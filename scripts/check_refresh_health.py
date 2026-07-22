import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATUS_PATH = ROOT / "docs" / "data" / "refresh_status.json"
TRUE_VALUES = {"1", "true", "yes", "on"}


def gmail_sync_required() -> bool:
    return os.getenv("REQUIRE_GMAIL_SYNC", "").strip().lower() in TRUE_VALUES


def assess_gmail_health(status: dict, required: bool) -> tuple[int, str]:
    sync_ok = status.get("gmail_sync_ok")
    if sync_ok is True:
        return 0, "Gmail sync health check passed."
    if sync_ok is not False:
        return 1, "Refresh status is missing a valid gmail_sync_ok value."

    detail = str(status.get("message") or "Gmail sync did not complete.")
    detail = " ".join(detail.split())
    if required:
        return 1, f"Gmail sync is required but failed. {detail}"
    return 0, f"::warning title=Gmail sync degraded::{detail} Cached Gmail data remains published."


def main() -> int:
    status_path = Path(os.getenv("REFRESH_STATUS_PATH", DEFAULT_STATUS_PATH))
    try:
        status = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Unable to read refresh status: {exc}")
        return 1

    exit_code, message = assess_gmail_health(status, gmail_sync_required())
    print(message)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
