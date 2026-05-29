from pathlib import Path
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.gmail_store import init_db

DATA_DIR = ROOT / "docs" / "data"
BEIJING_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")


def run_step(script_name: str) -> None:
    script_path = ROOT / "scripts" / script_name
    result = subprocess.run([sys.executable, str(script_path)], cwd=ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def try_step(script_name: str) -> bool:
    script_path = ROOT / "scripts" / script_name
    result = subprocess.run([sys.executable, str(script_path)], cwd=ROOT, check=False)
    return result.returncode == 0


def write_refresh_status(gmail_ready: bool, message: str) -> None:
    now = datetime.now()
    now_beijing = datetime.now(BEIJING_TZ)
    payload = {
        "status": "ok" if gmail_ready else "warning",
        "gmail_sync_ok": gmail_ready,
        "message": message,
        "last_attempt_at": now.isoformat(),
        "last_attempt_at_beijing": now_beijing.isoformat(),
        "refresh_interval_minutes": int(os.getenv("DATA_REFRESH_INTERVAL_MINUTES", "5")),
    }
    target = DATA_DIR / "refresh_status.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {target}")


def main() -> None:
    init_db()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    shipping_snapshot = DATA_DIR / "shipping_data.json"
    shipping_backup = shipping_snapshot.read_text(encoding="utf-8") if shipping_snapshot.exists() else None

    gmail_ready = try_step("sync_gmail_shipping_data.py")
    if not gmail_ready and os.getenv("REQUIRE_GMAIL_SYNC", "").lower() in {"1", "true", "yes"}:
        raise SystemExit("Gmail sync failed; refusing to publish partial data.")
    if gmail_ready:
        run_step("export_shipping_data_static.py")
    else:
        print("warning: Gmail sync failed, keeping existing shipping_data.json snapshot")
    run_step("generate_static_data.py")
    if not gmail_ready:
        if shipping_backup is not None:
            shipping_snapshot.write_text(shipping_backup, encoding="utf-8")
        print("warning: shipping snapshot restored from previous stable data")
    write_refresh_status(
        gmail_ready,
        "Gmail sync completed and static snapshots were regenerated."
        if gmail_ready
        else "Gmail sync failed; showing the latest previously published shipping email snapshot with freshly regenerated market dashboards.",
    )


if __name__ == "__main__":
    main()
