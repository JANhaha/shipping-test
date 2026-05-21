from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "outputs"
HISTORY_PATH = DATA_DIR / "article_history.json"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "120"))
OPENAI_API_MODE = os.getenv("OPENAI_API_MODE", "auto").strip().lower()

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

SOURCE_WHITELIST = {
    "Reuters": {"reuters.com"},
    "Bloomberg": {"bloomberg.com"},
    "Financial Times": {"ft.com"},
    "Wall Street Journal": {"wsj.com"},
    "Lloyd's List": {"lloydslist.com"},
    "TradeWinds": {"tradewindsnews.com"},
    "Splash247": {"splash247.com"},
    "S&P Global": {"spglobal.com", "spglobal.com/commodityinsights"},
    "Nikkei Asia": {"asia.nikkei.com"},
    "CNBC": {"cnbc.com"},
    "BBC": {"bbc.com", "bbc.co.uk"},
    "AP": {"apnews.com"},
    "Maritime Executive": {"maritime-executive.com"},
    "Journal of Commerce": {"joc.com"},
    "Seatrade Maritime": {"seatrade-maritime.com"},
}

DOMAIN_TO_SOURCE = {}
for source_name, domains in SOURCE_WHITELIST.items():
    for domain in domains:
        DOMAIN_TO_SOURCE[domain] = source_name

SHIPPING_KEYWORDS = [
    "shipping",
    "maritime",
    "container shipping",
    "port logistics",
    "tanker",
    "dry bulk",
    "bunker fuel",
    "freight rates",
    "shipping sanctions",
    "commodity shipping",
    "port security",
    "shipping insurance",
    "oil tanker",
    "container port",
    "bulk carrier",
    "strait of hormuz shipping",
    "red sea shipping",
    "shipping decarbonization",
]

GENERATION_SYSTEM_PROMPT = """
你是资深中文航运编辑，负责公众号栏目《漢洋海运·热点解码》。

写作规则：
1. 只允许使用提供的新闻事实，不要编造数字或新增未经验证的事实。
2. 成稿必须是中文，可直接复制到公众号后台发布。
3. 标题要有传播力，但保持专业克制，不能标题党。
4. 开头必须先回答“今天为什么值得看”。
5. 正文必须围绕航运市场展开，重点落到油轮、集运、港口、运力、燃油、地缘风险、绿色航运等影响。
6. 不要写成零散新闻列表，要写成一篇完整文章。
7. 正文不要出现括号式来源、脚注、链接或引用格式。
8. 文末必须单独列“来源：”，每行格式为“媒体名 — 文章标题”。
9. 如果新闻量不足，可以围绕一条主线做深度整合，但不能硬凑。
10. 不要输出思维链、解释过程或任何与最终成稿无关的内容。
""".strip()
