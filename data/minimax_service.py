import json
import os
from pathlib import Path

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
            return {
                "enabled": False,
                "provider": "MiniMax",
                "model": MINIMAX_MODEL,
                "summary": None,
                "sections": [],
                "market_watch": [],
                "route_focus": [],
                "error": "MiniMax API key not configured.",
            }

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
            return {
                "enabled": True,
                "provider": "MiniMax",
                "model": MINIMAX_MODEL,
                "summary": data.get("summary"),
                "sections": data.get("sections", []),
                "market_watch": data.get("market_watch", []),
                "route_focus": data.get("route_focus", []),
                "error": None,
            }
        except Exception as exc:
            return {
                "enabled": False,
                "provider": "MiniMax",
                "model": MINIMAX_MODEL,
                "summary": None,
                "sections": [],
                "market_watch": [],
                "route_focus": [],
                "error": str(exc),
            }

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
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                return json.loads(content[start : end + 1])
            raise

    @staticmethod
    def _read_key_file():
        if DEFAULT_KEY_PATH.exists():
            return DEFAULT_KEY_PATH.read_text(encoding="utf-8").replace("\ufeff", "").strip()
        return None
