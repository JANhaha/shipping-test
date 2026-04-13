import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.gmail_service import GmailShippingDataService


def main():
    service = GmailShippingDataService()
    token_path = service.ensure_oauth_token()
    print(f"Gmail OAuth 完成，token 已保存到: {token_path}")


if __name__ == "__main__":
    main()
