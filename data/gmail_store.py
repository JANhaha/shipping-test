import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "shipping_data.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS gmail_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gmail_message_id TEXT NOT NULL UNIQUE,
                thread_id TEXT,
                label_ids TEXT,
                sender TEXT,
                subject TEXT,
                internal_ts INTEGER,
                received_at TEXT,
                snippet TEXT,
                body_text TEXT,
                body_summary TEXT,
                has_attachments INTEGER NOT NULL DEFAULT 0,
                raw_payload_json TEXT,
                synced_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS gmail_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gmail_message_id TEXT NOT NULL,
                attachment_id TEXT,
                filename TEXT NOT NULL,
                mime_type TEXT,
                size_bytes INTEGER,
                local_path TEXT,
                parsed_text TEXT,
                parsed_summary TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(gmail_message_id, attachment_id, filename)
            );

            CREATE INDEX IF NOT EXISTS idx_gmail_messages_received_at
            ON gmail_messages(received_at DESC);

            CREATE INDEX IF NOT EXISTS idx_gmail_attachments_message_id
            ON gmail_attachments(gmail_message_id);
            """
        )


def upsert_message(record):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO gmail_messages (
                gmail_message_id, thread_id, label_ids, sender, subject, internal_ts,
                received_at, snippet, body_text, body_summary, has_attachments,
                raw_payload_json, synced_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(gmail_message_id) DO UPDATE SET
                thread_id=excluded.thread_id,
                label_ids=excluded.label_ids,
                sender=excluded.sender,
                subject=excluded.subject,
                internal_ts=excluded.internal_ts,
                received_at=excluded.received_at,
                snippet=excluded.snippet,
                body_text=excluded.body_text,
                body_summary=excluded.body_summary,
                has_attachments=excluded.has_attachments,
                raw_payload_json=excluded.raw_payload_json,
                synced_at=excluded.synced_at
            """,
            (
                record["gmail_message_id"],
                record.get("thread_id"),
                json.dumps(record.get("label_ids", []), ensure_ascii=False),
                record.get("sender"),
                record.get("subject"),
                record.get("internal_ts"),
                record.get("received_at"),
                record.get("snippet"),
                record.get("body_text"),
                record.get("body_summary"),
                int(bool(record.get("has_attachments"))),
                json.dumps(record.get("raw_payload_json", {}), ensure_ascii=False),
                record.get("synced_at"),
            ),
        )


def replace_attachments(gmail_message_id, attachments):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM gmail_attachments WHERE gmail_message_id = ?",
            (gmail_message_id,),
        )
        conn.executemany(
            """
            INSERT INTO gmail_attachments (
                gmail_message_id, attachment_id, filename, mime_type, size_bytes,
                local_path, parsed_text, parsed_summary, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    gmail_message_id,
                    item.get("attachment_id"),
                    item.get("filename"),
                    item.get("mime_type"),
                    item.get("size_bytes"),
                    item.get("local_path"),
                    item.get("parsed_text"),
                    item.get("parsed_summary"),
                    item.get("created_at"),
                )
                for item in attachments
            ],
        )


def list_messages(limit=50):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM gmail_messages
            ORDER BY internal_ts DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def list_attachments_for_message_ids(message_ids):
    if not message_ids:
        return {}
    placeholders = ",".join("?" for _ in message_ids)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT *
            FROM gmail_attachments
            WHERE gmail_message_id IN ({placeholders})
            ORDER BY id ASC
            """,
            tuple(message_ids),
        ).fetchall()
    grouped = {}
    for row in rows:
        grouped.setdefault(row["gmail_message_id"], []).append(dict(row))
    return grouped


def list_all_attachments(limit=200):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT a.*, m.sender, m.subject, m.received_at, m.gmail_message_id
            FROM gmail_attachments a
            JOIN gmail_messages m
              ON m.gmail_message_id = a.gmail_message_id
            ORDER BY m.internal_ts DESC, a.id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_latest_sync_time():
    with get_connection() as conn:
        row = conn.execute("SELECT MAX(synced_at) AS latest FROM gmail_messages").fetchone()
        return row["latest"] if row and row["latest"] else None
