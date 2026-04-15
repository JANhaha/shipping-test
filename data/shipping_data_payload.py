from datetime import datetime

from data.attachment_visualization import build_attachment_dashboard
from data.gmail_store import get_latest_sync_time, list_attachments_for_message_ids
from data.shipping_message_selector import get_latest_target_message


def build_shipping_data_payload(limit=300):
    latest_message = get_latest_target_message(limit=100)
    rows = []
    if latest_message:
        attachments = list_attachments_for_message_ids([latest_message["gmail_message_id"]])
        row = dict(latest_message)
        row["attachments"] = attachments.get(latest_message["gmail_message_id"], [])
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
