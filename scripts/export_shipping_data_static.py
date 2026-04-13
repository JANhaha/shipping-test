import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.gmail_store import init_db
from data.shipping_data_payload import build_shipping_data_payload


def main():
    init_db()
    payload = build_shipping_data_payload(limit=300)
    target = ROOT / "docs" / "data" / "shipping_data.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
