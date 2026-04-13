from datetime import datetime
import os

from flask import Flask, jsonify, render_template

from data.attachment_visualization import build_attachment_dashboard
from data.dashboard_service import ShippingDashboardService
from data.gmail_service import GmailShippingDataService
from data.gmail_store import get_latest_sync_time, init_db, list_attachments_for_message_ids, list_messages


app = Flask(__name__, template_folder="templates")
service = ShippingDashboardService()
gmail_service = GmailShippingDataService()
init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/shipping-data")
def shipping_data_page():
    return render_template("shipping_data.html")


@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    payload = service.get_dashboard()
    payload["served_at"] = datetime.now().isoformat()
    return jsonify(payload)


@app.route("/api/shipping-data", methods=["GET"])
def shipping_data():
    messages = list_messages(limit=100)
    attachments = list_attachments_for_message_ids([item["gmail_message_id"] for item in messages])
    rows = []
    for message in messages:
        row = dict(message)
        row["attachments"] = attachments.get(message["gmail_message_id"], [])
        rows.append(row)

    attachment_view = build_attachment_dashboard(limit=300)
    return jsonify(
        {
            "items": rows,
            "count": len(rows),
            "attachments_total": attachment_view["total"],
            "attachment_categories": attachment_view["categories"],
            "latest_sync_at": get_latest_sync_time(),
            "served_at": datetime.now().isoformat(),
        }
    )


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
