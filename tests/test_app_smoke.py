import unittest
from unittest.mock import patch

from app import app
from data import attachment_visualization
from data.gmail_service import GmailShippingDataService


class AppSmokeTest(unittest.TestCase):
    def test_health_endpoint(self):
        with app.test_client() as client:
            response = client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_page_routes_render(self):
        with app.test_client() as client:
            for path in ("/", "/shipping-data", "/map-data", "/route-rentals", "/route-rentals-v2"):
                response = client.get(path)
                self.assertEqual(response.status_code, 200, path)
                self.assertIn(b"html", response.data[:64].lower())

    def test_api_responses_disable_cache(self):
        with app.test_client() as client:
            response = client.get("/api/health")

        self.assertIn("no-store", response.headers.get("Cache-Control", ""))

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

    def test_route_market_snapshot_prefers_newer_static_shipping_data(self):
        old_categories = [
            {
                "items": [
                    {
                        "display_name": "Baltic Capesize Index.pdf",
                        "table": {"rows": [["C5", "Old route", "1.000", "0.100"]]},
                    }
                ]
            }
        ]
        static_payload = {
            "source_message": {
                "subject": "SSY SINGAPORE REPORT- 296 MAY 2026",
                "received_at": "2026-05-29T02:38:48",
            },
            "attachment_categories": [
                {
                    "items": [
                        {
                            "display_name": "Baltic Capesize Index.pdf",
                            "table": {"rows": [["C5", "West Australia to Qingdao", "16.870", "0.555"]]},
                        }
                    ]
                }
            ],
        }

        with patch.object(
            attachment_visualization,
            "build_attachment_dashboard",
            return_value={"categories": old_categories},
        ), patch.object(
            attachment_visualization,
            "_load_static_shipping_data",
            return_value=static_payload,
        ), patch.object(
            attachment_visualization,
            "get_latest_target_message",
            return_value={"received_at": "2026-05-25T10:19:07"},
        ):
            snapshot = attachment_visualization.build_route_market_snapshot()

        self.assertEqual(snapshot["C5"]["value"], "16.870")
        self.assertEqual(snapshot["C5"]["received_at"], "2026-05-29T02:38:48")


if __name__ == "__main__":
    unittest.main()
