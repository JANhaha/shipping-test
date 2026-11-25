import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.mysteel_reports import MysteelReportError, get_mysteel_report_details, get_mysteel_reports
from data.mysteel_report_ocr import get_report_groups


SNAPSHOT = ROOT / "docs" / "data" / "mysteel_reports.json"
CHECK_INTERVAL = timedelta(minutes=30)


def read_snapshot():
    try:
        return json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def recently_checked(previous, now):
    stamp = previous.get("checked_at")
    if not stamp:
        return False
    try:
        age = now - datetime.fromisoformat(stamp)
    except (ValueError, TypeError):
        return False
    return timedelta() <= age < CHECK_INTERVAL


def needs_ocr():
    previous = read_snapshot()
    if recently_checked(previous, datetime.now(timezone.utc)):
        return False
    cached = {report["url"]: report for report in previous.get("reports", [])}
    try:
        reports = get_mysteel_reports()
    except MysteelReportError:
        return False
    return any(not cached.get(report["url"], {}).get("grouped_complete") for report in reports)


def quote_count(report):
    return sum(len(rows) for rows in report.get("groups", {}).values())


def group_quality(groups):
    # Normal report layout: seven Capesize, four Panamax and three Supramax rows.
    # A changed layout can still publish validated rows, with a coverage notice.
    expected_counts = {"capesize": 7, "panamax": 4, "supramax": 3}
    for ship, expected in expected_counts.items():
        rows = groups.get(ship, [])
        if len(rows) < expected or any(row.get("change") is None for row in rows):
            return False
    return True


def sync_reports(force=False):
    now = datetime.now(timezone.utc)
    previous = read_snapshot()
    if not force and recently_checked(previous, now):
        return

    try:
        reports = get_mysteel_reports()
    except MysteelReportError as error:
        print(f"::warning title=Mysteel report check::{error} Kept the existing snapshot.")
        return

    previous_reports = previous.get("reports", [])
    if previous_reports and previous_reports[0]["published_at"] > reports[0]["published_at"]:
        reports = [{field: report[field] for field in ("title", "url", "published_at")} for report in previous_reports]
    cached_reports = {report["url"]: report for report in previous_reports}
    updated = []
    for metadata in reports:
        cached = cached_reports.get(metadata["url"], {})
        report = {**cached, **metadata}
        if force or not cached.get("grouped_complete"):
            try:
                details = get_mysteel_report_details(metadata, include_image=True)
                candidates = details.pop("image_candidates")
                report.update(details)
                grouped = get_report_groups(candidates, report["published_at"])
                complete = group_quality(grouped["groups"])
                if quote_count(grouped) >= quote_count(cached) and (not cached.get("grouped_complete") or complete):
                    report.update(grouped)
                    report["grouped_complete"] = complete
            except MysteelReportError as error:
                print(f"::warning title=Mysteel article check::{report['published_at']} {error}")
        updated.append(report)
    payload = {"checked_at": now.isoformat(timespec="seconds"), "reports": updated}
    SNAPSHOT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Mysteel reports: latest {updated[0]['published_at']}; {quote_count(updated[0])} route quotes in latest; "
          f"{sum(bool(report.get('groups')) for report in updated)}/{len(updated)} reports grouped.")


if __name__ == "__main__":
    if "--needs-ocr" in sys.argv[1:]:
        print("yes" if needs_ocr() else "no")
    else:
        sync_reports(force="--force" in sys.argv[1:])
