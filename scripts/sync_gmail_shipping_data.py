import sys
from pathlib import Path
import traceback

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.gmail_service import GmailShippingDataService


def main():
    service = GmailShippingDataService()
    try:
        result = service.sync_recent_shipping_data()
        print(result)
        return 0
    except Exception as exc:
        print(
            {
                "synced_count": 0,
                "message_ids": [],
                "warning": f"Gmail sync skipped: {exc}",
                "used_cached_data": True,
            }
        )
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
