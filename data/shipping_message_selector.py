from data.gmail_store import list_messages


TARGET_SUBJECT = "SSY SINGAPORE REPORT"


def get_latest_target_message(limit=100):
    messages = list_messages(limit=limit)
    for message in messages:
        subject = (message.get("subject") or "").upper()
        if TARGET_SUBJECT in subject:
            return message
    return None
