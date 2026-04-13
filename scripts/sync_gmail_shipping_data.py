import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.gmail_service import GmailShippingDataService


def main():
    service = GmailShippingDataService()
    result = service.sync_recent_shipping_data()
    print(result)


if __name__ == "__main__":
    main()
