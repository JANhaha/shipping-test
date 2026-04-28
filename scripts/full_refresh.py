from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "docs" / "data"


def run_step(script_name: str) -> None:
    script_path = ROOT / "scripts" / script_name
    result = subprocess.run([sys.executable, str(script_path)], cwd=ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def try_step(script_name: str) -> bool:
    script_path = ROOT / "scripts" / script_name
    result = subprocess.run([sys.executable, str(script_path)], cwd=ROOT, check=False)
    return result.returncode == 0


def main() -> None:
    shipping_snapshot = DATA_DIR / "shipping_data.json"
    map_snapshot = DATA_DIR / "map_data.json"
    shipping_backup = shipping_snapshot.read_text(encoding="utf-8") if shipping_snapshot.exists() else None
    map_backup = map_snapshot.read_text(encoding="utf-8") if map_snapshot.exists() else None

    gmail_ready = try_step("sync_gmail_shipping_data.py")
    if gmail_ready:
        run_step("export_shipping_data_static.py")
    else:
        print("warning: Gmail sync failed, keeping existing shipping_data.json snapshot")
    run_step("generate_static_data.py")
    if not gmail_ready:
        if shipping_backup is not None:
            shipping_snapshot.write_text(shipping_backup, encoding="utf-8")
        if map_backup is not None:
            map_snapshot.write_text(map_backup, encoding="utf-8")
        print("warning: Gmail-derived snapshots restored from previous stable data")


if __name__ == "__main__":
    main()
