from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import HISTORY_PATH, OPENAI_BASE_URL, OPENAI_MODEL, OUTPUT_DIR
from .history import (
    HistoryEntry,
    filter_recent_history,
    keyword_overlap,
    load_history,
    save_history,
    similarity,
)
from .news import Article, ShippingNewsCollector
from .openai_client import OpenAIResponsesClient


UTC = timezone.utc


PLANNER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "candidate_topics": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "lead_angle": {"type": "string"},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                    "article_ids": {"type": "array", "items": {"type": "string"}},
                    "shipping_impact": {"type": "string"},
                    "duplicate_risk": {"type": "string"},
                },
                "required": [
                    "title",
                    "lead_angle",
                    "keywords",
                    "article_ids",
                    "shipping_impact",
                    "duplicate_risk",
                ],
            },
        },
        "selected_topic": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "title": {"type": "string"},
                "lead_angle": {"type": "string"},
                "keywords": {"type": "array", "items": {"type": "string"}},
                "main_article_ids": {"type": "array", "items": {"type": "string"}},
                "support_article_ids": {"type": "array", "items": {"type": "string"}},
                "why_today": {"type": "string"},
                "market_watchpoints": {"type": "array", "items": {"type": "string"}},
                "fallback_single_event": {"type": "boolean"},
            },
            "required": [
                "title",
                "lead_angle",
                "keywords",
                "main_article_ids",
                "support_article_ids",
                "why_today",
                "market_watchpoints",
                "fallback_single_event",
            ],
        },
    },
    "required": ["candidate_topics", "selected_topic"],
}


QUALITY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "pass": {"type": "boolean"},
        "issues": {"type": "array", "items": {"type": "string"}},
        "revised_article": {"type": "string"},
    },
    "required": ["pass", "issues", "revised_article"],
}


@dataclass
class PipelineResult:
    output_path: Path
    title: str
    candidate_count: int
    article_count: int
    used_hours_window: int
    sources: list[str]


class DailyWechatHotspotPipeline:
    def __init__(self) -> None:
        self.news_collector = ShippingNewsCollector()
        self.llm = OpenAIResponsesClient()

    def run(self, run_date: datetime | None = None) -> PipelineResult:
        run_date = run_date or datetime.now(UTC)
        history_entries = load_history(HISTORY_PATH)
        recent_history = filter_recent_history(history_entries, days=14)

        hours_window = 24
        articles = self.news_collector.collect(hours=hours_window)
        if len(articles) < 6:
            hours_window = 48
            articles = self.news_collector.collect(hours=hours_window)
        if not articles:
            raise RuntimeError("没有检索到可用的海外航运新闻。")

        if self._use_single_pass_mode():
            selected_articles = self._select_articles_for_single_pass(articles, recent_history)
            article_body = self._generate_article_single_pass(
                run_date=run_date,
                articles=selected_articles,
                recent_history=recent_history,
                hours_window=hours_window,
            )
            output_path = self._write_output(run_date=run_date, article_body=article_body)
            history_entries.append(
                self._build_single_pass_history_entry(
                    run_date=run_date,
                    output_path=output_path,
                    articles=selected_articles,
                    article_body=article_body,
                )
            )
            save_history(HISTORY_PATH, history_entries)
            sources = [f"{article.source} — {article.title}" for article in selected_articles]
            return PipelineResult(
                output_path=output_path,
                title=self._extract_title(article_body),
                candidate_count=max(5, len(selected_articles)),
                article_count=len(articles),
                used_hours_window=hours_window,
                sources=sources,
            )

        planner_payload = self._plan_topics(run_date=run_date, articles=articles, recent_history=recent_history)
        selected_topic = planner_payload["selected_topic"]
        article_body = self._generate_article(run_date=run_date, articles=articles, planner_payload=planner_payload)
        article_body = self._quality_check(article_body=article_body, selected_topic=selected_topic, articles=articles)

        output_path = self._write_output(run_date=run_date, article_body=article_body)
        history_entries.append(
            self._build_history_entry(
                run_date=run_date,
                output_path=output_path,
                selected_topic=selected_topic,
                articles=articles,
                article_body=article_body,
            )
        )
        save_history(HISTORY_PATH, history_entries)

        sources = [f"{article.source} — {article.title}" for article in self._selected_articles(selected_topic, articles)]
        return PipelineResult(
            output_path=output_path,
            title=self._extract_title(article_body),
            candidate_count=len(planner_payload["candidate_topics"]),
            article_count=len(articles),
            used_hours_window=hours_window,
            sources=sources,
        )

    def _use_single_pass_mode(self) -> bool:
        if self.llm.api_mode == "chat_completions":
            return True
        base_url = OPENAI_BASE_URL.lower()
        model_name = OPENAI_MODEL.lower()
        return "scnet.cn" in base_url or "deepseek-r1" in model_name

    def _select_articles_for_single_pass(
        self,
        articles: list[Article],
        recent_history: list[HistoryEntry],
    ) -> list[Article]:
        scored: list[tuple[int, Article]] = []
        impact_terms = {
            "tanker": 4,
            "oil": 3,
            "port": 3,
            "shipping": 2,
            "container": 3,
            "bulk": 3,
            "red sea": 4,
            "hormuz": 4,
            "security": 3,
            "fund": 2,
            "electrification": 2,
            "orderbook": 2,
            "kamsarmax": 3,
            "suezmax": 3,
        }
        for article in articles:
            text = f"{article.title} {article.summary}".lower()
            if any(term in text for term in ("cockpit", "raf", "drone mission")):
                continue
            score = sum(weight for term, weight in impact_terms.items() if term in text)
            if not any(
                term in text
                for term in (
                    "shipping",
                    "maritime",
                    "tanker",
                    "port",
                    "container",
                    "bulk",
                    "orderbook",
                    "vlcc",
                    "suezmax",
                    "kamsarmax",
                    "blockade",
                    "hormuz",
                )
            ):
                score -= 3
            penalty = 0
            for history_entry in recent_history:
                if similarity(article.title, history_entry.title) >= 0.72:
                    penalty += 3
            scored.append((score - penalty, article))
        scored.sort(key=lambda item: item[0], reverse=True)
        selected = [article for _, article in scored[:10]]
        return selected or articles[:10]

    def _generate_article_single_pass(
        self,
        *,
        run_date: datetime,
        articles: list[Article],
        recent_history: list[HistoryEntry],
        hours_window: int,
    ) -> str:
        fact_lines = []
        for index, article in enumerate(articles, start=1):
            summary = article.summary or "无公开摘要，仅可依据标题判断。"
            fact_lines.append(
                f"{index}. 媒体：{article.source}；标题：{article.title}；时间：{article.published_at or '未知'}；可用事实：{summary}"
            )

        prompt = "\n".join(
            [
                f"当前日期（UTC）: {run_date.isoformat()}",
                f"新闻时间窗口：优先最近24小时，本次实际使用最近{hours_window}小时材料。",
                "你现在要直接产出一篇可发布的公众号成稿，不要先列提纲，不要先做摘要。",
                "栏目名固定：《漢洋海运·热点解码》",
                "你必须严格按照下面骨架输出：",
                "标题",
                "导语",
                "一、......",
                "二、......",
                "三、......",
                "四、......（如果材料不足可以省略这一节）",
                "结尾",
                "写作目标：",
                "1. 总字数控制在1100到1300字。",
                "2. 风格要像高打开率的专业公众号，不要像学术评论，也不要像新闻列表。",
                "3. 标题要有冲突感和传播力，但不能夸张失真。",
                "4. 开头第一段必须回答：今天为什么值得看。",
                "5. 正文必须用3到5个小标题，每个小标题下都要说明发生了什么、为什么对航运重要、接下来要看什么。",
                "6. 允许把24小时内新闻作为主线，再补入48小时内仍在发酵、且与航运直接相关的消息来撑起完整内容。",
                "7. 重点关注：油轮、能源运输、港口安全、运力订单、船东投资、绿色航运、地缘政治对海运的影响。",
                "8. 绝对不要写成“第1条、第2条”的资讯列表，不要输出摘要清单。",
                "9. 正文不要出现括号式来源、脚注、链接、引号式引用。",
                "10. 不要输出来源部分，来源由系统在文末追加。",
                "11. 不要编造数字；不确定的地方用趋势性表达。",
                "12. 不要输出<think>、不要解释你的写作过程，直接输出最终文章。",
                "13. 文中必须至少具体整合4条不同新闻事实，不能只泛泛而谈全球航运。",
                "14. 每个小标题都必须围绕同一主线推进，形成一篇完整文章，而不是平铺罗列。",
                "15. 结尾必须给出接下来市场最值得看的2到3个观察点。",
                "16. 避免空话，例如“全球运价持续波动”“市场充满不确定性”这类泛泛表述，必须尽量写出材料中真实发生的事情。",
                "17. 不要写“新闻1”“新闻2”“某媒体称”等字样，要把材料自然写进文章里。",
                "18. 不要使用 Markdown 粗体，不要使用分隔线，不要写编号清单。",
                "最近14天历史，供你避开重复角度：",
                json.dumps([entry.to_dict() for entry in recent_history], ensure_ascii=False, indent=2),
                "可用新闻事实清单：",
                "\n".join(fact_lines),
            ]
        )
        article = self.llm.create_text(prompt)
        return self._finalize_single_pass_article(article, articles)

    def _plan_topics(self, *, run_date: datetime, articles: list[Article], recent_history: list[HistoryEntry]) -> dict[str, Any]:
        prompt = "\n".join(
            [
                f"当前日期（UTC）: {run_date.isoformat()}",
                "任务：为《漢洋海运·热点解码》生成选题方案。",
                "你必须产出至少5个候选主题，只使用给定新闻。",
                "你必须避开最近14天重复主线、重复角度和重复叙事框架。",
                "如果新闻分散，请优先选择最能影响航运市场的一条主线。",
                "最近14天历史：",
                json.dumps([entry.to_dict() for entry in recent_history], ensure_ascii=False, indent=2),
                "新闻池：",
                json.dumps([article.to_prompt_dict() for article in articles], ensure_ascii=False, indent=2),
                "输出 JSON，字段必须符合 schema。",
            ]
        )
        payload = self.llm.create_json(prompt, schema_name="wechat_topic_planner", schema=PLANNER_SCHEMA)
        payload["candidate_topics"] = self._dedupe_candidates(payload["candidate_topics"], recent_history)
        payload["selected_topic"] = self._ensure_selected_topic_not_duplicate(
            payload["selected_topic"],
            payload["candidate_topics"],
            recent_history,
        )
        return payload

    def _generate_article(self, *, run_date: datetime, articles: list[Article], planner_payload: dict[str, Any]) -> str:
        selected_topic = planner_payload["selected_topic"]
        selected_articles = [article.to_prompt_dict() for article in self._selected_articles(selected_topic, articles)]
        prompt = "\n".join(
            [
                f"当前日期（UTC）: {run_date.isoformat()}",
                "请生成一篇可直接发布到微信公众号的中文文章。",
                "固定栏目名：《漢洋海运·热点解码》",
                "要求：",
                "1. 总字数 1100-1300 字。",
                "2. 必须包含标题、导语、3-5个小标题分段、结尾总结、来源。",
                "3. 第一段快速说明今天为什么值得看。",
                "4. 每个分段都要回答：发生了什么、为什么对航运重要、接下来市场看什么。",
                "5. 不要写成新闻摘要拼盘，要写成航运市场评论。",
                "6. 正文不要出现括号式来源、脚注、引号式引用。",
                "7. 文末来源格式必须是 plain text，每行一个“媒体名 — 文章标题”。",
                "8. 如果事实不够确认，不要写具体数字，改用趋势性表述。",
                "9. 标题要有打开率，但保持专业，不要标题党。",
                "选题方案：",
                json.dumps(selected_topic, ensure_ascii=False, indent=2),
                "候选主题摘要：",
                json.dumps(planner_payload["candidate_topics"], ensure_ascii=False, indent=2),
                "可用新闻事实：",
                json.dumps(selected_articles, ensure_ascii=False, indent=2),
            ]
        )
        return self.llm.create_text(prompt)

    def _quality_check(self, *, article_body: str, selected_topic: dict[str, Any], articles: list[Article]) -> str:
        selected_articles = [article.to_prompt_dict() for article in self._selected_articles(selected_topic, articles)]
        prompt = "\n".join(
            [
                "请对下面的公众号文章做质量自检，如果不合格则直接输出修订版。",
                "检查点：",
                "1. 是否只是新闻摘要。",
                "2. 是否明确落到航运市场影响。",
                "3. 是否给出明确后续观察点。",
                "4. 是否存在括号式来源、脚注或引用痕迹。",
                "5. 是否保持 1100-1300 字左右。",
                "如果通过，revised_article 返回原文。",
                "选题：",
                json.dumps(selected_topic, ensure_ascii=False, indent=2),
                "事实池：",
                json.dumps(selected_articles, ensure_ascii=False, indent=2),
                "文章：",
                article_body,
            ]
        )
        result = self.llm.create_json(prompt, schema_name="wechat_quality_check", schema=QUALITY_SCHEMA)
        return (result.get("revised_article") or article_body).strip()

    def _write_output(self, *, run_date: datetime, article_body: str) -> Path:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / f"{run_date.date().isoformat()}-热点解码.md"
        path.write_text(article_body.strip() + "\n", encoding="utf-8")
        return path

    def _build_history_entry(
        self,
        *,
        run_date: datetime,
        output_path: Path,
        selected_topic: dict[str, Any],
        articles: list[Article],
        article_body: str,
    ) -> HistoryEntry:
        selected_articles = self._selected_articles(selected_topic, articles)
        return HistoryEntry(
            date=run_date.isoformat(),
            title=self._extract_title(article_body),
            lead_angle=str(selected_topic.get("lead_angle", "")).strip(),
            keywords=[str(item).strip() for item in selected_topic.get("keywords", []) if str(item).strip()],
            sources=[f"{article.source} — {article.title}" for article in selected_articles],
            core_event=str(selected_topic.get("why_today", "")).strip(),
            output_file=str(output_path),
        )

    def _build_single_pass_history_entry(
        self,
        *,
        run_date: datetime,
        output_path: Path,
        articles: list[Article],
        article_body: str,
    ) -> HistoryEntry:
        keywords = self._infer_keywords_from_articles(articles)
        lead_angle = "、".join(keywords[:3]) if keywords else "航运热点整合"
        return HistoryEntry(
            date=run_date.isoformat(),
            title=self._extract_title(article_body),
            lead_angle=lead_angle,
            keywords=keywords,
            sources=[f"{article.source} — {article.title}" for article in articles],
            core_event=lead_angle,
            output_file=str(output_path),
        )

    @staticmethod
    def _extract_title(article_body: str) -> str:
        for line in article_body.splitlines():
            clean = line.strip().lstrip("#").strip()
            if clean:
                return clean
        return "《漢洋海运·热点解码》"

    @staticmethod
    def _selected_articles(selected_topic: dict[str, Any], articles: list[Article]) -> list[Article]:
        wanted_ids = {
            *selected_topic.get("main_article_ids", []),
            *selected_topic.get("support_article_ids", []),
        }
        matches = [article for article in articles if article.id in wanted_ids]
        return matches or articles[:3]

    @staticmethod
    def _infer_keywords_from_articles(articles: list[Article]) -> list[str]:
        buckets = {
            "油轮": ("tanker", "oil", "vlcc", "suezmax", "mr2"),
            "集运": ("container", "logistics", "port"),
            "干散货": ("bulk", "kamsarmax", "capesize", "panamax"),
            "绿色航运": ("electrification", "green", "decarbon", "fuel"),
            "航线安全": ("security", "red sea", "hormuz", "blockade"),
            "船东投资": ("fund", "orderbook", "order", "investment"),
        }
        found: list[str] = []
        corpus = " ".join(f"{article.title} {article.summary}".lower() for article in articles)
        for label, terms in buckets.items():
            if any(term in corpus for term in terms):
                found.append(label)
        return found or ["航运", "海外媒体", "市场观察"]

    @staticmethod
    def _finalize_single_pass_article(article_body: str, articles: list[Article]) -> str:
        cleaned = article_body.replace("<think>", "").replace("</think>", "").strip()
        cleaned = cleaned.replace("**", "")
        cleaned = cleaned.replace("---", "")
        lines = [line.rstrip() for line in cleaned.splitlines()]
        filtered_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if filtered_lines and filtered_lines[-1] != "":
                    filtered_lines.append("")
                continue
            if stripped.startswith("来源"):
                break
            filtered_lines.append(stripped)
        while filtered_lines and filtered_lines[-1] == "":
            filtered_lines.pop()
        source_lines = ["来源："]
        for article in articles:
            source_lines.append(f"{article.source} — {article.title}")
        return "\n".join([*filtered_lines, "", *source_lines]).strip() + "\n"

    @staticmethod
    def _dedupe_candidates(candidates: list[dict[str, Any]], recent_history: list[HistoryEntry]) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        for candidate in candidates:
            title = str(candidate.get("title", ""))
            lead_angle = str(candidate.get("lead_angle", ""))
            keywords = [str(item) for item in candidate.get("keywords", [])]
            duplicate = False
            for history_entry in recent_history:
                if similarity(title, history_entry.title) >= 0.72:
                    duplicate = True
                    break
                if similarity(lead_angle, history_entry.lead_angle) >= 0.72:
                    duplicate = True
                    break
                if keyword_overlap(keywords, history_entry.keywords) >= 0.65:
                    duplicate = True
                    break
            if not duplicate:
                filtered.append(candidate)
        return filtered or candidates

    @classmethod
    def _ensure_selected_topic_not_duplicate(
        cls,
        selected_topic: dict[str, Any],
        candidates: list[dict[str, Any]],
        recent_history: list[HistoryEntry],
    ) -> dict[str, Any]:
        if not cls._is_duplicate(selected_topic, recent_history):
            return selected_topic
        for candidate in candidates:
            if not cls._is_duplicate(candidate, recent_history):
                merged = dict(selected_topic)
                merged["title"] = candidate.get("title", merged.get("title", ""))
                merged["lead_angle"] = candidate.get("lead_angle", merged.get("lead_angle", ""))
                merged["keywords"] = candidate.get("keywords", merged.get("keywords", []))
                merged["main_article_ids"] = candidate.get("article_ids", merged.get("main_article_ids", []))
                merged["support_article_ids"] = []
                return merged
        return selected_topic

    @staticmethod
    def _is_duplicate(topic: dict[str, Any], recent_history: list[HistoryEntry]) -> bool:
        title = str(topic.get("title", ""))
        lead_angle = str(topic.get("lead_angle", ""))
        keywords = [str(item) for item in topic.get("keywords", [])]
        for history_entry in recent_history:
            if similarity(title, history_entry.title) >= 0.72:
                return True
            if similarity(lead_angle, history_entry.lead_angle) >= 0.72:
                return True
            if keyword_overlap(keywords, history_entry.keywords) >= 0.65:
                return True
        return False
