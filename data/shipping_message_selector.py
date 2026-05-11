from data.gmail_store import get_connection


TARGET_SUBJECTS = [
    "SSY SINGAPORE",
    "SSY SINGAPOR",
]
TARGET_SUBJECTS_NORMALIZED = [value.replace(" ", "") for value in TARGET_SUBJECTS]


def get_latest_target_message(limit=100):
    del limit
    with get_connection() as conn:
        patterns = [f"%{value}%" for value in TARGET_SUBJECTS_NORMALIZED]
        placeholders = " OR ".join(
            "UPPER(REPLACE(COALESCE(subject, ''), ' ', '')) LIKE ?"
            for _ in patterns
        )
        row = conn.execute(
            f"""
            SELECT *
            FROM gmail_messages
            WHERE has_attachments = 1
              AND ({placeholders})
            ORDER BY internal_ts DESC, id DESC
            LIMIT 1
            """,
            patterns,
        ).fetchone()
    return dict(row) if row else None
