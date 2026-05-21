import unittest

from app import app


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


if __name__ == "__main__":
    unittest.main()
