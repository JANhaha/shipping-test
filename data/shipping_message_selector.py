from data.gmail_store import get_connection


TARGET_SUBJECT = "SSY SINGAPORE REPORT"
TARGET_SUBJECT_NORMALIZED = TARGET_SUBJECT.replace(" ", "")


def get_latest_target_message(limit=100):
    del limit
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM gmail_messages
            WHERE has_attachments = 1
              AND UPPER(REPLACE(COALESCE(subject, ''), ' ', '')) LIKE ?
            ORDER BY internal_ts DESC, id DESC
            LIMIT 1
            """,
            (f"%{TARGET_SUBJECT_NORMALIZED}%",),
        ).fetchone()
    return dict(row) if row else None
