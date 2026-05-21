from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI
import requests

from .config import (
    GENERATION_SYSTEM_PROMPT,
    OPENAI_API_KEY,
    OPENAI_API_MODE,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    OPENAI_TIMEOUT,
)


class OpenAIResponsesClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = (api_key or OPENAI_API_KEY).strip()
        if not self.api_key:
            raise RuntimeError("缺少 OPENAI_API_KEY，无法生成选题和文章。")
        self.api_mode = self._resolve_api_mode(OPENAI_API_MODE, OPENAI_BASE_URL)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )
        self.sdk_client = OpenAI(
            api_key=self.api_key,
            base_url=OPENAI_BASE_URL,
            timeout=OPENAI_TIMEOUT,
        )

    @staticmethod
    def _resolve_api_mode(configured_mode: str, base_url: str) -> str:
        mode = (configured_mode or "auto").strip().lower()
        if mode and mode != "auto":
            return mode
        lowered = (base_url or "").lower()
        if "minimaxi.com" in lowered or "scnet.cn" in lowered:
            return "chat_completions"
        return "responses"

    def create_text(self, user_prompt: str, *, model: str | None = None) -> str:
        if self.api_mode == "chat_completions":
            return self._create_text_via_chat(user_prompt, model=model)
        payload = {
            "model": model or OPENAI_MODEL,
            "instructions": GENERATION_SYSTEM_PROMPT,
            "input": user_prompt,
        }
        response = self.session.post(
            f"{OPENAI_BASE_URL}/responses",
            data=json.dumps(payload),
            timeout=OPENAI_TIMEOUT,
        )
        response.raise_for_status()
        body = response.json()
        text = body.get("output_text")
        if isinstance(text, str) and text.strip():
            return text.strip()
        return self._flatten_output_text(body)

    def create_json(
        self,
        user_prompt: str,
        schema_name: str,
        schema: dict,
        *,
        model: str | None = None,
    ) -> dict[str, Any]:
        if self.api_mode == "chat_completions":
            return self._create_json_via_chat(user_prompt, schema=schema, model=model)
        payload = {
            "model": model or OPENAI_MODEL,
            "instructions": GENERATION_SYSTEM_PROMPT,
            "input": user_prompt,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                }
            },
        }
        response = self.session.post(
            f"{OPENAI_BASE_URL}/responses",
            data=json.dumps(payload),
            timeout=OPENAI_TIMEOUT,
        )
        response.raise_for_status()
        body = response.json()
        text = body.get("output_text") or self._flatten_output_text(body)
        return json.loads(text)

    def _create_text_via_chat(self, user_prompt: str, *, model: str | None = None) -> str:
        response = self.sdk_client.chat.completions.create(
            model=model or OPENAI_MODEL,
            messages=[
                {"role": "system", "content": GENERATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=4096,
            stream=False,
        )
        content = response.choices[0].message.content
        if isinstance(content, str) and content.strip():
            return self._strip_reasoning(content)
        raise RuntimeError("模型未返回可用文本。")

    def _create_json_via_chat(self, user_prompt: str, *, schema: dict, model: str | None = None) -> dict[str, Any]:
        schema_prompt = "\n".join(
            [
                user_prompt,
                "请严格输出 JSON，不要输出 Markdown 代码块，不要输出解释文字。",
                "JSON Schema 如下：",
                json.dumps(schema, ensure_ascii=False),
            ]
        )
        raw = self._create_text_via_chat(schema_prompt, model=model)
        cleaned = self._extract_json_text(raw)
        return json.loads(cleaned)

    @staticmethod
    def _flatten_output_text(body: dict) -> str:
        fragments: list[str] = []
        for item in body.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if isinstance(text, str):
                    fragments.append(text)
        joined = "\n".join(fragment for fragment in fragments if fragment.strip()).strip()
        if not joined:
            raise RuntimeError("OpenAI 响应中没有可用文本输出。")
        return joined

    @staticmethod
    def _strip_reasoning(text: str) -> str:
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
        return cleaned or text.strip()

    @classmethod
    def _extract_json_text(cls, text: str) -> str:
        cleaned = cls._strip_reasoning(text)
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned).strip()
        for start_char, end_char in (("{", "}"), ("[", "]")):
            start = cleaned.find(start_char)
            end = cleaned.rfind(end_char)
            if start != -1 and end != -1 and end > start:
                return cleaned[start : end + 1]
        return cleaned.strip()
