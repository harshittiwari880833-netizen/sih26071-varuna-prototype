"""
app.py — VARUNA backend API (optional, for demonstrating a "real" architecture)
---------------------------------------------------------------------------
This is NOT required to run the dashboard demo (the frontend reads the
pre-computed data/demo_bundle.json directly, which is the zero-risk path for
presenting in front of judges). Run this ONLY if you want to additionally
show a live API responding to requests -- useful for Q&A when a judge asks
"do you have a real backend?" or "can I hit an endpoint?".

Run:
    pip install flask flask-cors
    python app.py
Then visit: http://localhost:5000/api/frames

Swap-in point for production: replace load_bundle() with real-time calls to
your data pipeline (satellite/radar/AWS/NWP ingestion -> fusion -> ML model
-> inundation mapping), keeping the exact same JSON response shape so the
existing frontend needs zero changes.
"""

import json
import os
from flask import Flask, jsonify

try:
    from flask_cors import CORS
    HAS_CORS = True
except ImportError:
    HAS_CORS = False

app = Flask(__name__)
if HAS_CORS:
    CORS(app)  # allow the frontend (served on a different port) to call this API

BUNDLE_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "data", "demo_bundle.json")

_bundle_cache = None


def load_bundle():
    global _bundle_cache
    if _bundle_cache is None:
        with open(BUNDLE_PATH) as f:
            _bundle_cache = json.load(f)
    return _bundle_cache


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "service": "VARUNA rainfall & inundation API"})


@app.route("/api/meta")
def meta():
    return jsonify(load_bundle()["meta"])


@app.route("/api/metrics")
def metrics():
    return jsonify(load_bundle()["model_metrics"])


@app.route("/api/frames")
def frames():
    return jsonify(load_bundle()["frames"])


@app.route("/api/frames/<int:time_step>")
def frame_by_step(time_step):
    b = load_bundle()
    matches = [f for f in b["frames"] if f["time_step"] == time_step]
    if not matches:
        return jsonify({"error": "time_step not found"}), 404
    return jsonify(matches[0])


@app.route("/api/alerts")
def alerts():
    return jsonify(load_bundle()["alerts"])


if __name__ == "__main__":
    print("VARUNA backend running -> http://localhost:5000")
    print("Try: /api/health  /api/meta  /api/metrics  /api/frames  /api/alerts")
    app.run(host="0.0.0.0", port=5000, debug=False)
