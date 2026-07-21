import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import app
from data import attachment_visualization
from data.dashboard_service import ShippingDashboardService
from data.gmail_service import GmailShippingDataService


class AppSmokeTest(unittest.TestCase):
    def test_health_endpoint(self):
        with app.test_client() as client:
            response = client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_page_routes_render(self):
        with app.test_client() as client:
            for path in (
                "/",
                "/market-overview",
                "/map-data",
                "/route-rentals",
                "/route-rentals-v2",
                "/route-rentals-v3",
            ):
                response = client.get(path)
                self.assertEqual(response.status_code, 200, path)
                self.assertIn(b"html", response.data[:64].lower())

    def test_legacy_shipping_data_page_redirects_to_market_overview(self):
        with app.test_client() as client:
            response = client.get("/shipping-data")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/market-overview"))

    def test_shared_visual_system_is_served_on_primary_pages(self):
        with app.test_client() as client:
            stylesheet = client.get("/assets/ocean-ui.css")
            self.assertEqual(stylesheet.status_code, 200)
            self.assertIn(b".site-header", stylesheet.data)
            stylesheet.close()

            for path, page_class in (
                ("/", b"page-company"),
                ("/market-overview", b"page-market"),
                ("/map-data", b"page-map"),
                ("/route-rentals-v3", b"page-rentals"),
            ):
                response = client.get(path)
                self.assertEqual(response.status_code, 200, path)
                self.assertIn(page_class, response.data)
                self.assertIn(b"site-header", response.data)

            company_stylesheet = client.get("/assets/company.css")
            self.assertEqual(company_stylesheet.status_code, 200)
            self.assertIn(b".company-hero", company_stylesheet.data)
            company_stylesheet.close()

            company_logo = client.get("/assets/company/logo.webp")
            self.assertEqual(company_logo.status_code, 200)
            company_logo.close()

    def test_company_home_has_exactly_three_project_entries(self):
        with app.test_client() as client:
            response = client.get("/")

        html = response.get_data(as_text=True)
        self.assertEqual(html.count('class="project-card"'), 3)
        self.assertNotIn("航运数据", html)
        self.assertIn("Mandarine Ocean Ltd", html)

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

    def test_gmail_message_timestamp_is_beijing_aware(self):
        timestamp = GmailShippingDataService._format_ts("0")

        self.assertEqual(timestamp, "1970-01-01T08:00:00+08:00")

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

    def test_bunker_prices_keep_static_snapshot_when_source_fails(self):
        service = ShippingDashboardService()
        static_ports = [
            {"port": "Zhoushan", "country": "CN", "ifo380": 558, "vlsfo": 676, "mgo": 983, "date": "16 Jun"},
            {"port": "Singapore", "country": "SG", "ifo380": "451.00", "vlsfo": "664.00", "mgo": "905.00", "date": "02 Jul"},
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            service.root = Path(tmp_dir)
            dashboard_path = service.root / "docs" / "data" / "dashboard.json"
            dashboard_path.parent.mkdir(parents=True)
            dashboard_path.write_text(
                json.dumps({"bunker_index": {"ports": static_ports}}),
                encoding="utf-8",
            )

            with patch.object(
                service,
                "_load_bunker_index_ports",
                side_effect=RuntimeError("connection reset"),
            ), patch.object(
                service,
                "get_zhoushan_bunker",
                return_value={
                    "port": "Zhoushan",
                    "date": "02 Jul",
                    "prices": {"IFO380": 452, "VLSFO": 648, "LSMGO": 939},
                },
            ):
                payload = service.get_bunker_prices()

        self.assertTrue(payload["fallback_used"])
        self.assertEqual(payload["fallback_source"], "docs/data/dashboard.json")
        self.assertIn("BunkerIndex load failed", payload["error"])
        self.assertEqual(payload["ports"][0]["port"], "Zhoushan")
        self.assertEqual(payload["ports"][0]["vlsfo"], 648)
        self.assertEqual([row["port"] for row in payload["ports"]], ["Zhoushan", "Singapore"])


if __name__ == "__main__":
    unittest.main()
