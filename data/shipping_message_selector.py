from data.gmail_store import get_connection


TARGET_SUBJECT = "SSY SINGAPORE REPORT"


def get_latest_target_message(limit=100):
    del limit
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM gmail_messages
            WHERE UPPER(COALESCE(subject, '')) LIKE ?
            ORDER BY has_attachments DESC, internal_ts DESC, id DESC
            LIMIT 1
            """,
            (f"%{TARGET_SUBJECT}%",),
        ).fetchone()
    return dict(row) if row else None
