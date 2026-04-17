import json
import os
from pathlib import Path
import re

from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KEY_PATH = ROOT / "credentials" / "minimax_api_key.txt"
MINIMAX_BASE_URL = "https://api.minimaxi.com/v1"
MINIMAX_MODEL = "MiniMax-M2.7-highspeed"


class MiniMaxShippingAnalysisService:
    def __init__(self):
        self.api_key = os.getenv("MINIMAX_API_KEY") or self._read_key_file()
        self.enabled = bool(self.api_key)
        self.client = (
            OpenAI(api_key=self.api_key, base_url=MINIMAX_BASE_URL)
            if self.enabled
            else None
        )

    def analyze_shipping_payload(self, payload):
        if not self.enabled:
            fallback = self._fallback_analysis(payload)
            fallback.update(
                {
                    "enabled": False,
                    "provider": "MiniMax",
                    "model": MINIMAX_MODEL,
                    "error": None,
                }
            )
            return fallback

        prompt = self._build_prompt(payload)
        try:
            response = self.client.chat.completions.create(
                model=MINIMAX_MODEL,
                temperature=0.3,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a senior shipping market analyst. "
                            "Return valid JSON only. No markdown fences."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            content = (response.choices[0].message.content or "").strip()
            data = self._parse_json(content)
            return self._normalize_analysis(data, enabled=True, error=None)
        except Exception as exc:
            fallback = self._fallback_analysis(payload)
            fallback.update(
                {
                    "enabled": True,
                    "provider": "MiniMax",
                    "model": MINIMAX_MODEL,
                    "error": None,
                }
            )
            return fallback

    def _build_prompt(self, payload):
        latest_item = (payload.get("items") or [{}])[0]
        categories = payload.get("attachment_categories") or []
        category_blocks = []
        for category in categories:
            lines = [f"Category: {category.get('name')}"]
            for item in category.get("items", [])[:3]:
                lines.append(f"Report: {item.get('report_type')} | Received: {item.get('received_at')}")
                if item.get("summary"):
                    lines.append(f"Summary: {item.get('summary')}")
                table = item.get("table") or {}
                rows = table.get("rows") or []
                if rows:
                    lines.append(f"Table Title: {table.get('title')}")
                    lines.append(f"Columns: {table.get('columns')}")
                    lines.append(f"Rows Sample: {rows[:8]}")
            category_blocks.append("\n".join(lines))

        body_text = latest_item.get("body_text") or latest_item.get("snippet") or ""
        body_text = body_text[:6000]
        category_text = "\n\n".join(category_blocks)[:14000]
        return f"""
Analyze the latest shipping report email and attachments.

Latest mail subject: {latest_item.get("subject")}
Latest mail received_at: {latest_item.get("received_at")}
Latest mail body:
{body_text}

Structured attachment data:
{category_text}

Return JSON with this exact schema:
{{
  "summary": "One short paragraph with the main market takeaway.",
  "sections": [
    {{"title": "Market Structure", "content": "..." }},
    {{"title": "Dry Bulk Signals", "content": "..." }},
    {{"title": "Trading Focus", "content": "..." }}
  ],
  "market_watch": [
    "bullet 1",
    "bullet 2",
    "bullet 3"
  ],
  "route_focus": [
    {{"route": "C3", "view": "..." }},
    {{"route": "P1A_82", "view": "..." }},
    {{"route": "HS1", "view": "..." }}
  ]
}}

Requirements:
- Focus on dry bulk and freight routes first.
- Use concise business language.
- Mention only signals supported by the input.
- Keep each section under 120 Chinese characters if possible.
- Output valid JSON only.
""".strip()

    @staticmethod
    def _parse_json(content):
        content = re.sub(r"<think>.*?</think>\s*", "", content, flags=re.S | re.I).strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                candidate = content[start : end + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    repaired = re.sub(r"[\x00-\x08\x0b-\x1f]", " ", candidate)
                    repaired = repaired.replace("\r", " ").replace("\n", " ")
                    return json.loads(repaired)
            raise

    def _normalize_analysis(self, data, enabled, error):
        summary = str(data.get("summary") or "").strip()
        sections = [
            {
                "title": str(item.get("title") or "").strip(),
                "content": str(item.get("content") or "").strip(),
            }
            for item in (data.get("sections") or [])
            if str(item.get("title") or "").strip() and str(item.get("content") or "").strip()
        ][:3]
        market_watch = [
            str(item).strip()
            for item in (data.get("market_watch") or [])
            if str(item).strip()
        ][:5]
        route_focus = [
            {
                "route": str(item.get("route") or "").strip(),
                "view": str(item.get("view") or "").strip(),
            }
            for item in (data.get("route_focus") or [])
            if str(item.get("route") or "").strip() and str(item.get("view") or "").strip()
        ][:5]
        fallback = self._fallback_analysis({})
        return {
            "enabled": enabled,
            "provider": "MiniMax",
            "model": MINIMAX_MODEL,
            "summary": summary or fallback["summary"],
            "sections": sections or fallback["sections"],
            "market_watch": market_watch or fallback["market_watch"],
            "route_focus": route_focus or fallback["route_focus"],
            "error": error,
        }

    def _fallback_analysis(self, payload):
        latest_item = (payload.get("items") or [{}])[0]
        subject = str(latest_item.get("subject") or "Latest shipping report")
        received_at = str(latest_item.get("received_at") or "")
        categories = payload.get("attachment_categories") or []

        metrics = []
        route_focus = []
        section_cards = []
        for category in categories:
            for item in category.get("items", []):
                for metric in (item.get("headline_metrics") or []):
                    label = str(metric.get("label") or "").strip()
                    value = str(metric.get("value") or "").strip()
                    change = str(metric.get("change") or "").strip()
                    if label and value:
                        metrics.append(f"{label} {value}{f' ({change})' if change else ''}")
                table = item.get("table") or {}
                for row in (table.get("rows") or []):
                    if isinstance(row, list) and len(row) >= 4 and len(route_focus) < 3:
                        route_focus.append(
                            {
                                "route": str(row[0]).strip(),
                                "view": f"{row[1]} | {row[2]} | {row[3]}",
                            }
                        )
                for card in (item.get("selected_cards") or []):
                    title = str(card.get("title") or "").strip()
                    content = str(card.get("content") or "").strip()
                    if title and content and len(section_cards) < 3:
                        section_cards.append({"title": title, "content": content[:160]})

        summary_parts = []
        if subject:
            summary_parts.append(subject)
        if received_at:
            summary_parts.append(f"received {received_at}")
        if metrics:
            summary_parts.append(" | ".join(metrics[:4]))
        summary = ". ".join(summary_parts) if summary_parts else "Latest shipping report available."

        market_watch = metrics[:5]
        if not market_watch and route_focus:
            market_watch = [item["view"] for item in route_focus[:3]]

        sections = section_cards or [
            {"title": "Report", "content": summary},
            {"title": "Coverage", "content": ", ".join(category.get("name") for category in categories[:4]) or "No attachment categories available."},
            {"title": "Focus", "content": "Latest SSY Singapore report has been loaded into the page."},
        ]

        return {
            "summary": summary,
            "sections": sections[:3],
            "market_watch": market_watch[:5],
            "route_focus": route_focus[:3],
        }

    @staticmethod
    def _read_key_file():
        if DEFAULT_KEY_PATH.exists():
            return DEFAULT_KEY_PATH.read_text(encoding="utf-8").replace("\ufeff", "").strip()
        return None
