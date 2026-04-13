from datetime import datetime

from data.attachment_visualization import build_attachment_dashboard
from data.gmail_store import get_latest_sync_time, list_attachments_for_message_ids, list_messages


def build_shipping_data_payload(limit=300):
    messages = list_messages(limit=1)
    rows = []
    if messages:
        attachments = list_attachments_for_message_ids([messages[0]["gmail_message_id"]])
        for message in messages:
            row = dict(message)
            row["attachments"] = attachments.get(message["gmail_message_id"], [])
            rows.append(row)

    attachment_view = build_attachment_dashboard(limit=limit)
    return {
        "items": rows,
        "count": len(rows),
        "attachments_total": attachment_view["total"],
        "attachment_categories": attachment_view["categories"],
        "latest_sync_at": get_latest_sync_time(),
        "served_at": datetime.now().isoformat(),
    }
