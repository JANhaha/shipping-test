import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.mysteel_reports import MysteelReportError, get_mysteel_reports


SNAPSHOT = ROOT / "docs" / "data" / "mysteel_reports.json"
CHECK_INTERVAL = timedelta(minutes=30)


def sync_reports(force=False):
    now = datetime.now(timezone.utc)
    try:
        previous = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}

    if not force and previous.get("checked_at"):
        checked_at = datetime.fromisoformat(previous["checked_at"])
        if timedelta() <= now - checked_at < CHECK_INTERVAL:
            return

    try:
        reports = get_mysteel_reports()
    except MysteelReportError as error:
        print(f"::warning title=Mysteel report check::{error} Kept the existing snapshot.")
        return

    previous_reports = previous.get("reports")
    if previous_reports and previous_reports[0]["published_at"] > reports[0]["published_at"]:
        reports = previous_reports
    payload = {"checked_at": now.isoformat(timespec="seconds"), "reports": reports}
    SNAPSHOT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Mysteel reports: latest publication {reports[0]['published_at']}")


if __name__ == "__main__":
    sync_reports(force="--force" in sys.argv[1:])
