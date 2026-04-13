import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.attachment_visualization import build_attachment_dashboard
from data.gmail_store import get_latest_sync_time, init_db


def main():
    init_db()
    payload = {
        "attachment_categories": build_attachment_dashboard(limit=300)["categories"],
        "latest_sync_at": get_latest_sync_time(),
    }
    target = ROOT / "docs" / "data" / "shipping_data.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
