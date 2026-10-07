"""Frontend — checkout edge service."""
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
PRODUCT_URL = os.environ.get("PRODUCT_URL", "http://product:8081")
CTRL_DIR = Path(os.environ.get("CTRL_DIR", os.environ.get("FAULT_DIR", "/faults")))


def _latency() -> float:
    try:
        return float(CTRL_DIR.joinpath("frontend.latency").read_text().strip() or "0")
    except Exception:
        return 0.0


@app.get("/health")
def health():
    return jsonify(service="frontend", status="ok")


@app.get("/api/checkout")
def checkout():
    t0 = time.perf_counter()
    tags = base_tags() + ["resource:GET_/api/checkout"]
    with tracer.trace("frontend.checkout", service="frontend", resource="GET /api/checkout") as span:
        delay = _latency()
        if delay:
            time.sleep(delay)
        try:
            r = requests.get(f"{PRODUCT_URL}/api/product", timeout=40)
            ok = r.ok
            status = 200 if ok else 502
            if not ok:
                mark_span_error(
                    span,
                    f"product upstream failed status={r.status_code}",
                    "UpstreamProductError",
                )
                span.set_tag("peer.service", "product")
                span.set_tag("http.status_code", status)
                stats.increment(
                    "checkout.errors",
                    tags=tags + [f"peer_status:{r.status_code}", "peer_service:product", f"http_status:{status}"],
                )
                log.error(
                    "checkout failed — upstream product error",
                    extra={
                        "event": "checkout.upstream.error",
                        "http_status": status,
                        "peer_service": "product",
                        "error_type": "UpstreamProductError",
                        "resource": "GET /api/checkout",
                    },
                )
            else:
                stats.increment("checkout.ok", tags=tags + ["http_status:200"])
                log.info(
                    "checkout ok",
                    extra={
                        "event": "checkout.ok",
                        "http_status": 200,
                        "peer_service": "product",
                        "resource": "GET /api/checkout",
                    },
                )
            stats.timing("checkout.duration", (time.perf_counter() - t0) * 1000, tags=tags)
            return jsonify(
                service="frontend",
                product_status=r.status_code,
                product=r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text,
            ), status
        except requests.RequestException as e:
            mark_span_error(span, str(e), "UpstreamRequestException")
            stats.increment("checkout.errors", tags=tags + ["peer_service:product", "http_status:502"])
            log.exception(
                "product request exception",
                extra={"event": "checkout.upstream.exception", "http_status": 502, "peer_service": "product"},
            )
            return jsonify(service="frontend", error=str(e)), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
