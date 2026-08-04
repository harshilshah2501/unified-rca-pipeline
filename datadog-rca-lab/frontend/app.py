"""Frontend — calls Product. Same topology as dynatrace-rca-lab."""
from __future__ import annotations

import os
import time
from pathlib import Path

import requests
from ddtrace import patch_all, tracer
from flask import Flask, jsonify

patch_all()

app = Flask(__name__)
PRODUCT_URL = os.environ.get("PRODUCT_URL", "http://product:8081")
FAULT_DIR = Path(os.environ.get("FAULT_DIR", "/faults"))


def _fail() -> bool:
    return FAULT_DIR.joinpath("frontend.fail").read_text().strip().lower() == "true"


def _latency() -> float:
    try:
        return float(FAULT_DIR.joinpath("frontend.latency").read_text().strip() or "0")
    except Exception:
        return 0.0


@app.get("/health")
def health():
    return jsonify(service="frontend", status="ok")


@app.get("/api/checkout")
def checkout():
    with tracer.trace("frontend.checkout", service="frontend", resource="GET /api/checkout"):
        if _fail():
            return jsonify(error="frontend fault injected"), 503
        delay = _latency()
        if delay:
            time.sleep(delay)
        try:
            r = requests.get(f"{PRODUCT_URL}/api/product", timeout=5)
            return jsonify(
                service="frontend",
                product_status=r.status_code,
                product=r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text,
            ), (200 if r.ok else 502)
        except requests.RequestException as e:
            return jsonify(service="frontend", error=str(e)), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
