import unittest

from scripts.check_refresh_health import assess_gmail_health


class RefreshHealthTest(unittest.TestCase):
    def test_healthy_sync_passes(self):
        code, message = assess_gmail_health({"gmail_sync_ok": True}, required=True)

        self.assertEqual(code, 0)
        self.assertIn("passed", message)

    def test_optional_gmail_failure_is_reported_as_warning(self):
        code, message = assess_gmail_health(
            {"gmail_sync_ok": False, "message": "Token expired."},
            required=False,
        )

        self.assertEqual(code, 0)
        self.assertTrue(message.startswith("::warning"))
        self.assertIn("Cached Gmail data remains published", message)

    def test_required_gmail_failure_still_fails(self):
        code, message = assess_gmail_health(
            {"gmail_sync_ok": False, "message": "Token expired."},
            required=True,
        )

        self.assertEqual(code, 1)
        self.assertIn("required but failed", message)

    def test_invalid_status_fails(self):
        code, message = assess_gmail_health({}, required=False)

        self.assertEqual(code, 1)
        self.assertIn("gmail_sync_ok", message)


if __name__ == "__main__":
    unittest.main()
