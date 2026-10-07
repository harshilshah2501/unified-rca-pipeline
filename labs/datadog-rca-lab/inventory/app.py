"""Inventory — stock lookup service (FE → product → inventory leaf).

Code-level scenarios (scripts swap markers; not fault-flag / env-only simulation):
  • ERROR — WAREHOUSE_SKU_INDEX missing WIDGET-1 → KeyError
  • SLOWDOWN — LOOKUP_ block heavy ledger scan
  • AVAILABILITY — SCENARIO_MODE AVAILABILITY_DOWN → process exit after boot
  • MONITORING_UNAVAILABLE — SCENARIO_MODE MONITORING_DARK → no APM patch / no DogStatsD
  • RESOURCE_CONTENTION — RESOURCE_BURN background CPU thread (HTTP stays O(1))
"""
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

# --- SCENARIO_MODE markers (break/heal scripts swap HEALTHY / MONITORING_DARK / AVAILABILITY_DOWN) ---
SCENARIO_MODE = "HEALTHY"
# --- end SCENARIO_MODE ---

if SCENARIO_MODE == "MONITORING_DARK":
    # Code-only visibility dark: disable tracer before import/patch.
    os.environ["DD_TRACE_ENABLED"] = "false"
    os.environ["DD_RUNTIME_METRICS_ENABLED"] = "false"
    os.environ["DD_LOGS_INJECTION"] = "false"

from ddtrace import patch_all, tracer  # noqa: E402
from flask import Flask, jsonify  # noqa: E402

sys.path.insert(0, "/app")
from common.telemetry import (  # noqa: E402
    base_tags,
    dogstatsd,
    mark_span_error,
    setup_logging,
)

# Conditional instrumentation — MONITORING_DARK skips patch_all (HTTP still serves).
if SCENARIO_MODE != "MONITORING_DARK":
    patch_all()

app = Flask(__name__)
log = setup_logging()
CTRL_DIR = Path(os.environ.get("CTRL_DIR", os.environ.get("FAULT_DIR", "/faults")))


class _NullStats:
    def increment(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return None

    def timing(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return None

    def gauge(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return None


stats = _NullStats() if SCENARIO_MODE == "MONITORING_DARK" else dogstatsd()

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

# --- RESOURCE_BURN markers (break/heal scripts swap IDLE / BURN) ---
# IDLE: no background CPU burn (RESOURCE_CONTENTION lab off).
# --- end RESOURCE_BURN ---


if SCENARIO_MODE == "AVAILABILITY_DOWN":
    # Code-induced hard outage: process exits shortly after boot.
    def _exit_soon() -> None:
        time.sleep(2)
        os._exit(1)

    threading.Thread(target=_exit_soon, name="lab-avail-down", daemon=True).start()


def _latency() -> float:
    try:
        return float(CTRL_DIR.joinpath("inventory.latency").read_text().strip() or "0")
    except Exception:
        return 0.0


@app.get("/health")
def health():
    return jsonify(service="inventory", status="ok", scenario=SCENARIO_MODE)


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
                "scenario": SCENARIO_MODE,
            },
        )
        stats.timing("inventory.stock.duration", (time.perf_counter() - t0) * 1000, tags=tags)
        return jsonify(service="inventory", sku=body["sku"], qty=body["stock"])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8082")))
