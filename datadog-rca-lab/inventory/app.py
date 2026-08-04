"""Inventory — leaf service. Fault here = Dynatrace-lab parity scenario."""
from __future__ import annotations

import os
import time
from pathlib import Path

from ddtrace import patch_all, tracer
from flask import Flask, jsonify

patch_all()

app = Flask(__name__)
FAULT_DIR = Path(os.environ.get("FAULT_DIR", "/faults"))


def _fail() -> bool:
    return FAULT_DIR.joinpath("inventory.fail").read_text().strip().lower() == "true"


def _latency() -> float:
    try:
        return float(FAULT_DIR.joinpath("inventory.latency").read_text().strip() or "0")
    except Exception:
        return 0.0


@app.get("/health")
def health():
    return jsonify(service="inventory", status="ok")


@app.get("/api/stock")
def stock():
    with tracer.trace("inventory.stock", service="inventory", resource="GET /api/stock"):
        if _fail():
            return jsonify(error="inventory fault injected", sku="WIDGET-1"), 503
        delay = _latency()
        if delay:
            time.sleep(delay)
        return jsonify(service="inventory", sku="WIDGET-1", qty=42)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8082")))
