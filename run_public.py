import os

from waitress import serve

from app import app


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")), threads=8)
