import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import full_refresh


class RefreshStatusTest(unittest.TestCase):
    def test_failure_preserves_last_success_and_records_current_run(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "refresh_status.json"
            target.write_text(json.dumps({"gmail_sync_ok": True, "last_attempt_at_beijing": "2026-10-01T10:00:00+08:00"}), encoding="utf-8")
            with patch.object(full_refresh, "DATA_DIR", Path(directory)), patch.dict("os.environ", {"GITHUB_RUN_ID": "42"}):
                full_refresh.write_refresh_status(False, "failed")
            result = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(result["last_success_at_beijing"], "2026-10-01T10:00:00+08:00")
            self.assertFalse(result["gmail_sync_ok"])
            self.assertEqual(result["run_id"], "42")
            self.assertTrue(result["last_attempt_at"].endswith("+00:00"))

    def test_success_advances_last_success(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(full_refresh, "DATA_DIR", Path(directory)):
            full_refresh.write_refresh_status(True, "ok")
            result = json.loads((Path(directory) / "refresh_status.json").read_text(encoding="utf-8"))
            self.assertEqual(result["last_success_at_beijing"], result["last_attempt_at_beijing"])
