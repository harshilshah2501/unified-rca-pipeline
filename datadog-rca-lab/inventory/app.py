"""Inventory — stock lookup service (FE → product → inventory leaf)."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from ddtrace import patch_all, tracer
from flask import Flask, jsonify

sys.path.insert(0, "/app")
from common.telemetry import (  # noqa: E402
    base_tags,
    dogstatsd,
    mark_span_error,
    setup_logging,
)

patch_all()

app = Flask(__name__)
log = setup_logging()
stats = dogstatsd()
CTRL_DIR = Path(os.environ.get("CTRL_DIR", os.environ.get("FAULT_DIR", "/faults")))

WAREHOUSE_SKU_INDEX = {
    "WIDGET-1": 42,
    "IPAD-AIR": 40,
    "WATCH-ULTRA": 15,
    "MACBOOK-PRO-14": 100,
}


# --- LOOKUP_ impl markers (break/heal scripts swap between FAST and SLOW) ---
def lookup_stock_in_warehouse(sku: str = "WIDGET-1") -> dict:
    """FAST: O(1) index lookup."""
    qty = WAREHOUSE_SKU_INDEX[sku]
    return {"stock": qty, "sku": sku}


# --- end LOOKUP_ ---


def _latency() -> float:
    try:
        return float(CTRL_DIR.joinpath("inventory.latency").read_text().strip() or "0")
    except Exception:
        return 0.0


@app.get("/health")
def health():
    return jsonify(service="inventory", status="ok")


@app.get("/api/stock")
def stock():
    t0 = time.perf_counter()
    tags = base_tags() + ["resource:GET_/api/stock", "sku:WIDGET-1"]
    with tracer.trace("inventory.stock", service="inventory", resource="GET /api/stock") as span:
        span.set_tag("sku", "WIDGET-1")
        delay = _latency()
        if delay:
            time.sleep(delay)
        try:
            body = lookup_stock_in_warehouse("WIDGET-1")
        except KeyError as exc:
            msg = f"KeyError: {exc!s} — SKU missing from WAREHOUSE_SKU_INDEX"
            mark_span_error(span, msg, "KeyError")
            span.set_tag("http.status_code", 500)
            span.set_tag("error.sku", "WIDGET-1")
            stats.increment("inventory.stock.errors", tags=tags + ["http_status:500", "error_type:KeyError"])
            stats.increment("http.server.errors", tags=tags + ["http_status:500"])
            log.error(
                "stock lookup KeyError — catalog key missing",
                extra={
                    "event": "inventory.stock.error",
                    "http_status": 500,
                    "sku": "WIDGET-1",
                    "error_type": "KeyError",
                    "resource": "GET /api/stock",
                },
            )
            stats.timing("inventory.stock.duration", (time.perf_counter() - t0) * 1000, tags=tags)
            return jsonify(error="stock lookup failed", sku="WIDGET-1", detail=str(exc)), 500

        stats.increment("inventory.stock.ok", tags=tags + ["http_status:200"])
        stats.increment("http.server.hits", tags=tags + ["http_status:200"])
        log.info(
            "stock request ok",
            extra={
                "event": "inventory.stock.ok",
                "http_status": 200,
                "sku": body["sku"],
                "resource": "GET /api/stock",
            },
        )
        stats.timing("inventory.stock.duration", (time.perf_counter() - t0) * 1000, tags=tags)
        return jsonify(service="inventory", sku=body["sku"], qty=body["stock"])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8082")))
