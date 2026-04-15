from __future__ import annotations

import json
from datetime import datetime
from html import unescape
from pathlib import Path
import re
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from data.attachment_visualization import build_route_market_snapshot


class BalticMapDataService:
    DATA_URL = (
        "https://www.balticexchange.com/content/balticexchange/consumer/"
        "en/data-services/routes/jcr:content.data"
    )
    REQUEST_TIMEOUT = (10, 25)

    def __init__(self) -> None:
        self.session = requests.Session()
        retry = Retry(
            total=2,
            connect=2,
            read=2,
            backoff_factor=0.8,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods={"GET"},
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.root = Path(__file__).resolve().parents[1]

    def get_map_data(self) -> dict[str, Any]:
        try:
            response = self.session.get(self.DATA_URL, timeout=self.REQUEST_TIMEOUT)
            response.raise_for_status()
            payload = self._normalize_payload(response.json())
            payload["fallback"] = False
            payload["error"] = None
            return payload
        except Exception as exc:
            cached = self._load_cached_payload()
            if cached:
                cached["fallback"] = True
                cached["error"] = (
                    "Route map live fetch failed, using the last successful snapshot: "
                    f"{exc}"
                )
                return cached
            return {
                "title": "MAP DATA",
                "description": "",
                "segments": [],
                "route_count": 0,
                "index_count": 0,
                "fallback": False,
                "error": f"Route map fetch failed: {exc}",
                "updated_at": datetime.now().isoformat(),
            }

    def _normalize_payload(self, raw: dict[str, Any]) -> dict[str, Any]:
        segments: list[dict[str, Any]] = []
        route_count = 0
        index_count = 0
        route_snapshot = build_route_market_snapshot(limit=300)

        for segment in raw.get("segments", []):
            segment_title = segment.get("title") or "Unknown"
            normalized_indexes: list[dict[str, Any]] = []
            for index in segment.get("indexes", []):
                index_count += 1
                routes: list[dict[str, Any]] = []
                for route in index.get("routes", []):
                    route_count += 1
                    route_points = self._parse_route_points(route.get("routeJson"))
                    route_code = (route.get("title") or "").strip()
                    market_data = route_snapshot.get(route_code) or route_snapshot.get(
                        route_code.replace(" ", "")
                    )
                    routes.append(
                        {
                            "code": route_code,
                            "title": route_code,
                            "tooltip": route.get("tooltip") or route.get("title") or "",
                            "description": self._clean_html(route.get("description") or ""),
                            "reverse_route": bool(route.get("reverseRoute")),
                            "force_pacific_route": bool(route.get("forcePacificRoute")),
                            "path_points": route_points,
                            "points": self._parse_label_points(route.get("points")),
                            "market_data": market_data,
                            "stats": [
                                {
                                    "name": item.get("name", ""),
                                    "value": item.get("value", ""),
                                }
                                for item in (route.get("stats") or [])
                                if isinstance(item, dict)
                            ],
                        }
                    )
                normalized_indexes.append(
                    {
                        "title": index.get("title") or "",
                        "description": self._clean_html(index.get("description") or ""),
                        "routes": routes,
                    }
                )
            segments.append(
                {
                    "title": segment_title,
                    "description": self._clean_html(segment.get("description") or ""),
                    "indexes": normalized_indexes,
                }
            )

        return {
            "title": "MAP DATA",
            "source_title": raw.get("title") or "",
            "description": self._clean_html(raw.get("description") or ""),
            "segments": segments,
            "route_count": route_count,
            "index_count": index_count,
            "updated_at": datetime.now().isoformat(),
        }

    def _load_cached_payload(self) -> dict[str, Any] | None:
        target = self.root / "docs" / "data" / "map_data.json"
        if not target.exists():
            return None
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            return None

    @staticmethod
    def _clean_html(value: str) -> str:
        text = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
        text = re.sub(r"</p\s*>", "\n", text, flags=re.I)
        text = re.sub(r"<[^>]+>", "", text)
        text = unescape(text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _parse_route_points(value: Any) -> list[dict[str, Any]]:
        if not value:
            return []
        raw_points: list[dict[str, Any]]
        if isinstance(value, str):
            try:
                raw_points = json.loads(value)
            except json.JSONDecodeError:
                return []
        elif isinstance(value, list):
            raw_points = value
        else:
            return []

        points: list[dict[str, Any]] = []
        for point in raw_points:
            if not isinstance(point, dict):
                continue
            try:
                latitude = float(point["latitude"])
                longitude = float(point["longitude"])
            except (KeyError, TypeError, ValueError):
                continue
            points.append(
                {
                    "latitude": latitude,
                    "longitude": longitude,
                    "label": str(point.get("label", "")).strip(),
                    "additional_point": bool(point.get("additionalPoint")),
                }
            )
        return points

    @staticmethod
    def _parse_label_points(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        points: list[dict[str, Any]] = []
        for point in value:
            if not isinstance(point, dict):
                continue
            try:
                latitude = float(point["latitude"])
                longitude = float(point["longitude"])
            except (KeyError, TypeError, ValueError):
                continue
            points.append(
                {
                    "latitude": latitude,
                    "longitude": longitude,
                    "label": str(point.get("label", "")).strip(),
                    "additional_point": bool(point.get("additionalPoint")),
                }
            )
        return points
