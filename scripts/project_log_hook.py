#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append structured project log entries from hooks or manual commands."""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_PATH = PROJECT_ROOT / "logs" / "PROJECT_LOG.md"


def env_or_default(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def split_items(value: str) -> list[str]:
    if not value:
        return []
    normalized = value.replace(";", ",").replace("\n", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def bullet_block(items: list[str], fallback: str) -> str:
    if not items:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in items)


def build_entry(args: argparse.Namespace) -> str:
    now = args.time or datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %z")
    title = args.title or args.summary[:36] or "项目日志"
    files = split_items(args.files)
    verification = split_items(args.verification)
    deployment = split_items(args.deployment)
    risks = split_items(args.risks)
    next_notes = split_items(args.next)

    return f"""## {now} - {title}

触发来源：{args.event}

用户需求：
- {args.summary or "hook 未提供摘要。"}

完成内容：
- {args.details or args.summary or "hook 未提供完成内容。"}

关键文件：
{bullet_block(files, "hook 未提供文件列表。")}

验证：
{bullet_block(verification, "hook 未提供验证结果。")}

发布状态：
{bullet_block(deployment, "hook 未提供发布状态。")}

风险与待办：
{bullet_block(risks, "暂无记录。")}

下次接手提示：
{bullet_block(next_notes, "继续查看本日志和最近 Git 变更。")}
"""


def insert_entry(existing: str, entry: str) -> str:
    if not existing.strip():
        return (
            "# Project Log\n\n"
            "> 记录 `shipping_project` 的关键变更、验证、发布状态和下次接手提示。\n\n"
            f"{entry}\n"
        )

    lines = existing.splitlines()
    if not lines or not lines[0].startswith("# "):
        return f"# Project Log\n\n{entry}\n{existing.rstrip()}\n"

    insert_at = 1
    while insert_at < len(lines):
        text = lines[insert_at].strip()
        if text == "" or text.startswith(">"):
            insert_at += 1
            continue
        break

    output = lines[:insert_at] + ["", entry.rstrip(), ""] + lines[insert_at:]
    return "\n".join(output).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Append a structured shipping_project log entry.")
    parser.add_argument("--event", default=env_or_default("PROJECT_LOG_EVENT", "manual"))
    parser.add_argument("--summary", default=env_or_default("PROJECT_LOG_SUMMARY"))
    parser.add_argument("--details", default=env_or_default("PROJECT_LOG_DETAILS"))
    parser.add_argument("--files", default=env_or_default("PROJECT_LOG_FILES"))
    parser.add_argument("--verification", default=env_or_default("PROJECT_LOG_VERIFICATION"))
    parser.add_argument("--deployment", default=env_or_default("PROJECT_LOG_DEPLOYMENT"))
    parser.add_argument("--risks", default=env_or_default("PROJECT_LOG_RISKS"))
    parser.add_argument("--next", default=env_or_default("PROJECT_LOG_NEXT"))
    parser.add_argument("--title", default=env_or_default("PROJECT_LOG_TITLE"))
    parser.add_argument("--time", default=env_or_default("PROJECT_LOG_TIME"))
    parser.add_argument("--log-path", default=str(DEFAULT_LOG_PATH))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    entry = build_entry(args)
    log_path = Path(args.log_path)
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    updated = insert_entry(existing, entry)

    if args.dry_run:
        print(entry)
        return 0

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(updated, encoding="utf-8", newline="\n")
    print(f"updated {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
