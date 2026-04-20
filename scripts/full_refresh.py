from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def run_step(script_name: str) -> None:
    script_path = ROOT / "scripts" / script_name
    result = subprocess.run([sys.executable, str(script_path)], cwd=ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    run_step("sync_gmail_shipping_data.py")
    run_step("export_shipping_data_static.py")
    run_step("generate_static_data.py")


if __name__ == "__main__":
    main()
