import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.shipping_data_payload import build_shipping_data_payload
from data.dashboard_service import ShippingDashboardService
from data.gmail_store import init_db
from data.map_data_service import BalticMapDataService


BEIJING_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")


def main() -> None:
    init_db()
    now = datetime.now(BEIJING_TZ)
    payload = {
        "archived_at": now.isoformat(),
        "timezone": "Asia/Shanghai",
        "dashboard": ShippingDashboardService().get_dashboard(),
        "shipping_data": build_shipping_data_payload(limit=300),
        "map_data": BalticMapDataService().get_map_data(),
    }

    target_dir = ROOT / "data" / "daily_snapshots"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{now:%Y-%m-%d}.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
