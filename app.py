from datetime import datetime
import os

from flask import Flask, jsonify, render_template

from data.dashboard_service import ShippingDashboardService


app = Flask(__name__, template_folder="templates")
service = ShippingDashboardService()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    payload = service.get_dashboard()
    payload["served_at"] = datetime.now().isoformat()
    return jsonify(payload)


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
