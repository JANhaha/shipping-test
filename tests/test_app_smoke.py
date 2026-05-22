import unittest

from app import app
from data.gmail_service import GmailShippingDataService


class AppSmokeTest(unittest.TestCase):
    def test_health_endpoint(self):
        with app.test_client() as client:
            response = client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_page_routes_render(self):
        with app.test_client() as client:
            for path in ("/", "/shipping-data", "/map-data"):
                response = client.get(path)
                self.assertEqual(response.status_code, 200, path)
                self.assertIn(b"html", response.data[:64].lower())

    def test_gmail_attachment_filename_is_path_safe(self):
        original = (
            "15-20 MAY 26-ANY 3 DAYS SPREAD TO BE SPECIFIED by Owners "
            "52,500 MT 5 PCT SULPHUR UAE MOROCCO ALS INTERNATIONAL "
            "SHIP CHARTERING LIMITED MAIN TERMS.pdf"
        )
        safe_name = GmailShippingDataService._safe_filename(original)

        self.assertLessEqual(len(safe_name), 120)
        self.assertTrue(safe_name.endswith(".pdf"))
        self.assertNotIn(" ", safe_name)


if __name__ == "__main__":
    unittest.main()
