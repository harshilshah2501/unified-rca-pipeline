"""Product — calls Inventory. Same topology as dynatrace-rca-lab."""
from __future__ import annotations

import os
import time
from pathlib import Path

import requests
from ddtrace import patch_all, tracer
from flask import Flask, jsonify

patch_all()

app = Flask(__name__)
INVENTORY_URL = os.environ.get("INVENTORY_URL", "http://inventory:8082")
FAULT_DIR = Path(os.environ.get("FAULT_DIR", "/faults"))


def _fail() -> bool:
    return FAULT_DIR.joinpath("product.fail").read_text().strip().lower() == "true"


def _latency() -> float:
    try:
        return float(FAULT_DIR.joinpath("product.latency").read_text().strip() or "0")
    except Exception:
        return 0.0


@app.get("/health")
def health():
    return jsonify(service="product", status="ok")


@app.get("/api/product")
def product():
    with tracer.trace("product.get", service="product", resource="GET /api/product"):
        if _fail():
            return jsonify(error="product fault injected"), 503
        delay = _latency()
        if delay:
            time.sleep(delay)
        try:
            r = requests.get(f"{INVENTORY_URL}/api/stock", timeout=5)
            return jsonify(
                service="product",
                sku="WIDGET-1",
                inventory_status=r.status_code,
                inventory=r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text,
            ), (200 if r.ok else 502)
        except requests.RequestException as e:
            return jsonify(service="product", error=str(e)), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8081")))
