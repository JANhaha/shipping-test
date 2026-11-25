import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.mysteel_reports import BEIJING_TIME, MysteelReportError, get_mysteel_report_details, get_mysteel_reports
from data.mysteel_report_ocr import get_report_groups


SNAPSHOT = ROOT / "docs" / "data" / "mysteel_reports.json"
CHECK_INTERVAL = timedelta(minutes=30)
QUICK_CHECK_INTERVAL = timedelta(minutes=5)


def read_snapshot():
    try:
        return json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def recently_checked(previous, now):
    if not previous.get("source_status"):
        return False
    stamp = previous.get("attempted_at") or previous.get("checked_at")
    if not stamp:
        return False
    try:
        age = now - datetime.fromisoformat(stamp)
    except (ValueError, TypeError):
        return False
    latest = next(iter(previous.get("reports", [])), {})
    beijing_now = now.astimezone(BEIJING_TIME)
    minutes = beijing_now.hour * 60 + beijing_now.minute
    awaiting_today = (
        16 * 60 + 30 <= minutes < 22 * 60
        and not latest.get("published_at", "").startswith(beijing_now.date().isoformat())
    )
    needs_retry = previous.get("source_status") in {"unavailable", "lagging"} or (
        latest and not latest.get("grouped_complete")
    )
    interval = QUICK_CHECK_INTERVAL if awaiting_today or needs_retry else CHECK_INTERVAL
    return timedelta() <= age < interval


def write_snapshot(payload):
    staged = SNAPSHOT.with_suffix(".tmp")
    staged.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    staged.replace(SNAPSHOT)


def install_ocr():
    subprocess.run([
        sys.executable, "-m", "pip", "install", "--timeout", "20",
        "rapidocr-onnxruntime==1.4.4", "onnxruntime==1.31.0",
    ], check=True, timeout=150)


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


def sync_reports(force=False, provision_ocr=False):
    now = datetime.now(timezone.utc)
    previous = read_snapshot()
    if not force and recently_checked(previous, now):
        return

    attempted_at = now.isoformat(timespec="seconds")
    previous_reports = previous.get("reports", [])
    try:
        reports = get_mysteel_reports()
    except MysteelReportError as error:
        print(f"::warning title=Mysteel report check::{error} Kept the existing snapshot.")
        write_snapshot({
            **previous, "attempted_at": attempted_at, "source_status": "unavailable",
            "reports": previous_reports,
        })
        return

    source_latest = reports[0]["published_at"]
    if previous_reports and previous_reports[0]["published_at"] > source_latest:
        print("::warning title=Mysteel report check::The returned index is older than the last published edition.")
        write_snapshot({
            **previous, "attempted_at": attempted_at, "source_status": "lagging",
            "source_latest_published_at": source_latest, "reports": previous_reports,
        })
        return

    cached_reports = {
        (report["url"], report["published_at"]): report for report in previous_reports
    }
    to_process = {
        report["url"] for report in reports
        if force or not cached_reports.get((report["url"], report["published_at"]), {}).get("grouped_complete")
    }
    may_extract = True
    if to_process and provision_ocr:
        try:
            install_ocr()
        except (OSError, subprocess.SubprocessError) as error:
            print(f"::warning title=Mysteel report check::OCR setup failed ({type(error).__name__}); preserving known groups.")
            may_extract = False

    updated = []
    for metadata in reports:
        cached = cached_reports.get((metadata["url"], metadata["published_at"]), {})
        report = {**cached, **metadata}
        if metadata["url"] in to_process and may_extract:
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
    write_snapshot({
        "checked_at": attempted_at, "attempted_at": attempted_at, "source_status": "ok",
        "source_latest_published_at": source_latest, "reports": updated,
    })
    print(f"Mysteel reports: latest {updated[0]['published_at']}; {quote_count(updated[0])} route quotes in latest; "
          f"{sum(bool(report.get('groups')) for report in updated)}/{len(updated)} reports grouped.")


if __name__ == "__main__":
    sync_reports(force="--force" in sys.argv[1:], provision_ocr="--ci" in sys.argv[1:])
