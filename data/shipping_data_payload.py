from datetime import datetime, timedelta, timezone

from data.attachment_visualization import build_attachment_dashboard
from data.gmail_store import get_latest_sync_time
from data.minimax_service import MiniMaxShippingAnalysisService
from data.shipping_message_selector import get_latest_target_message


PUBLIC_BODY_TEXT_LIMIT = 9000


def build_shipping_data_payload(limit=300):
    beijing_tz = timezone(timedelta(hours=8), name="Asia/Shanghai")
    now = datetime.now()
    now_beijing = datetime.now(beijing_tz)
    latest_message = get_latest_target_message(limit=100)
    rows = []
    if latest_message:
        rows.append(_public_message(latest_message))

    attachment_view = build_attachment_dashboard(limit=limit)
    payload = {
        "items": rows,
        "count": len(rows),
        "attachments_total": attachment_view["total"],
        "attachment_categories": attachment_view["categories"],
        "source_message": {
            "gmail_message_id": latest_message.get("gmail_message_id") if latest_message else None,
            "subject": latest_message.get("subject") if latest_message else None,
            "received_at": latest_message.get("received_at") if latest_message else None,
            "synced_at": latest_message.get("synced_at") if latest_message else None,
        },
        "latest_sync_at": get_latest_sync_time(),
        "served_at": now.isoformat(),
        "served_at_beijing": now_beijing.isoformat(),
    }
    payload["ai_analysis"] = MiniMaxShippingAnalysisService().analyze_shipping_payload(payload)
    return payload


def _public_message(message):
    return {
        "gmail_message_id": message.get("gmail_message_id"),
        "subject": message.get("subject"),
        "received_at": message.get("received_at"),
        "snippet": message.get("snippet"),
        "body_text": _trim_text(message.get("body_text"), PUBLIC_BODY_TEXT_LIMIT),
        "body_summary": message.get("body_summary"),
        "has_attachments": bool(message.get("has_attachments")),
        "synced_at": message.get("synced_at"),
    }


def _trim_text(value, limit):
    text = str(value or "")
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}\n\n[Content trimmed for public dashboard performance.]"
