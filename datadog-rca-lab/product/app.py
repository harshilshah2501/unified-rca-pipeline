"""Product — assembles catalog from inventory."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
from ddtrace import patch_all, tracer
from flask import Flask, jsonify

sys.path.insert(0, "/app")
from common.telemetry import base_tags, dogstatsd, mark_span_error, setup_logging  # noqa: E402

patch_all()

app = Flask(__name__)
log = setup_logging()
stats = dogstatsd()
INVENTORY_URL = os.environ.get("INVENTORY_URL", "http://inventory:8082")
CTRL_DIR = Path(os.environ.get("CTRL_DIR", os.environ.get("FAULT_DIR", "/faults")))


def _latency() -> float:
    try:
        return float(CTRL_DIR.joinpath("product.latency").read_text().strip() or "0")
    except Exception:
        return 0.0


@app.get("/health")
def health():
    return jsonify(service="product", status="ok")


@app.get("/api/product")
def product():
    t0 = time.perf_counter()
    tags = base_tags() + ["resource:GET_/api/product"]
    with tracer.trace("product.get", service="product", resource="GET /api/product") as span:
        delay = _latency()
        if delay:
            time.sleep(delay)
        try:
            r = requests.get(f"{INVENTORY_URL}/api/stock", timeout=40)
            ok = r.ok
            status = 200 if ok else 502
            if not ok:
                mark_span_error(
                    span,
                    f"inventory upstream failed status={r.status_code}",
                    "UpstreamInventoryError",
                )
                span.set_tag("peer.service", "inventory")
                span.set_tag("http.status_code", status)
                stats.increment(
                    "product.upstream.errors",
                    tags=tags + [f"peer_status:{r.status_code}", "peer_service:inventory", f"http_status:{status}"],
                )
                log.error(
                    "upstream inventory call failed — cascading error",
                    extra={
                        "event": "product.upstream.error",
                        "http_status": status,
                        "peer_service": "inventory",
                        "error_type": "UpstreamInventoryError",
                        "resource": "GET /api/product",
                    },
                )
            else:
                stats.increment("product.ok", tags=tags + ["http_status:200"])
                log.info(
                    "product assembled from inventory",
                    extra={
                        "event": "product.ok",
                        "http_status": 200,
                        "peer_service": "inventory",
                        "resource": "GET /api/product",
                    },
                )
            stats.timing("product.duration", (time.perf_counter() - t0) * 1000, tags=tags)
            return jsonify(
                service="product",
                sku="WIDGET-1",
                inventory_status=r.status_code,
                inventory=r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text,
            ), status
        except requests.RequestException as e:
            mark_span_error(span, str(e), "UpstreamRequestException")
            stats.increment("product.upstream.errors", tags=tags + ["peer_service:inventory", "http_status:502"])
            log.exception(
                "inventory request exception",
                extra={"event": "product.upstream.exception", "http_status": 502, "peer_service": "inventory"},
            )
            return jsonify(service="product", error=str(e)), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8081")))
