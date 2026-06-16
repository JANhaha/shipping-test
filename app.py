from datetime import datetime
import os

from flask import Flask, jsonify, render_template

from data.dashboard_service import ShippingDashboardService
from data.gmail_service import GmailShippingDataService
from data.gmail_store import init_db
from data.map_data_service import BalticMapDataService
from data.shipping_data_payload import build_shipping_data_payload


app = Flask(__name__, template_folder="templates")
service = ShippingDashboardService()
gmail_service = GmailShippingDataService()
map_data_service = BalticMapDataService()
init_db()


@app.after_request
def add_no_cache_headers(response):
    if response.content_type.startswith(
        "application/json"
    ) or response.content_type.startswith("text/html"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/shipping-data")
def shipping_data_page():
    return render_template("shipping_data.html")


@app.route("/map-data")
def map_data_page():
    return render_template("map_data.html")


@app.route("/route-rentals")
def route_rentals_page():
    return render_template("route_rentals.html")


@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    payload = service.get_dashboard()
    payload["served_at"] = datetime.now().isoformat()
    return jsonify(payload)


@app.route("/api/shipping-data", methods=["GET"])
def shipping_data():
    return jsonify(build_shipping_data_payload(limit=300))


@app.route("/api/map-data", methods=["GET"])
def map_data():
    return jsonify(map_data_service.get_map_data())


@app.route("/api/shipping-data/sync", methods=["POST"])
def sync_shipping_data():
    try:
        result = gmail_service.sync_recent_shipping_data()
        return jsonify({"status": "ok", "result": result})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "message": "shipping dashboard is running",
            "time": datetime.now().isoformat(),
        }
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False,
        use_reloader=False,
    )
