import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.dashboard_service import ShippingDashboardService
from data.map_data_service import BalticMapDataService


def main():
    service = ShippingDashboardService()
    payload = service.get_dashboard()
    target = ROOT / "docs" / "data" / "dashboard.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {target}")

    map_service = BalticMapDataService()
    map_payload = map_service.get_map_data()
    map_target = ROOT / "docs" / "data" / "map_data.json"
    map_target.write_text(
        json.dumps(map_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {map_target}")


if __name__ == "__main__":
    main()
