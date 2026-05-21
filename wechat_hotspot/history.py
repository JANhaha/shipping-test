from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable


UTC = timezone.utc


@dataclass
class HistoryEntry:
    date: str
    title: str
    lead_angle: str
    keywords: list[str]
    sources: list[str]
    core_event: str
    output_file: str

    @classmethod
    def from_dict(cls, payload: dict) -> "HistoryEntry":
        return cls(
            date=str(payload.get("date", "")),
            title=str(payload.get("title", "")),
            lead_angle=str(payload.get("lead_angle", "")),
            keywords=[str(item) for item in payload.get("keywords", [])],
            sources=[str(item) for item in payload.get("sources", [])],
            core_event=str(payload.get("core_event", "")),
            output_file=str(payload.get("output_file", "")),
        )

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "title": self.title,
            "lead_angle": self.lead_angle,
            "keywords": self.keywords,
            "sources": self.sources,
            "core_event": self.core_event,
            "output_file": self.output_file,
        }


def ensure_history_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]", encoding="utf-8")


def load_history(path: Path) -> list[HistoryEntry]:
    ensure_history_file(path)
    raw = json.loads(path.read_text(encoding="utf-8") or "[]")
    if not isinstance(raw, list):
        return []
    return [HistoryEntry.from_dict(item) for item in raw if isinstance(item, dict)]


def save_history(path: Path, entries: Iterable[HistoryEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([entry.to_dict() for entry in entries], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def filter_recent_history(entries: Iterable[HistoryEntry], days: int = 14) -> list[HistoryEntry]:
    threshold = datetime.now(UTC) - timedelta(days=days)
    recent: list[HistoryEntry] = []
    for entry in entries:
        try:
            entry_dt = datetime.fromisoformat(entry.date.replace("Z", "+00:00"))
        except ValueError:
            continue
        if entry_dt >= threshold:
            recent.append(entry)
    return recent


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left.lower().strip(), right.lower().strip()).ratio()


def keyword_overlap(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = {item.strip().lower() for item in left if item.strip()}
    right_set = {item.strip().lower() for item in right if item.strip()}
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)
