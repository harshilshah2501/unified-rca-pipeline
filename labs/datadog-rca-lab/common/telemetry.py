"""Shared Datadog telemetry helpers for rca-lab (Metrics ∥ APM ∥ Logs).

Emits production-shaped signals only:
  • Traces  — ddtrace spans + standard error.* tags
  • Logs    — JSON lines to stdout + /logs/<service>.log with dd.trace_id
  • Metrics — DogStatsD UDP counters (rca.*) + APM auto metrics from spans
"""
from __future__ import annotations

import json
import logging
import os
import socket
import sys
import time
from typing import Any, Optional

from ddtrace import tracer

SERVICE = os.environ.get("DD_SERVICE", "unknown")
ENV = os.environ.get("DD_ENV", "rca-lab")
VERSION = os.environ.get("DD_VERSION", "1.0.0")
AGENT_HOST = os.environ.get("DD_AGENT_HOST", "127.0.0.1")
DSD_PORT = int(os.environ.get("DD_DOGSTATSD_PORT", "8125"))
LOG_DIR = os.environ.get("LOG_DIR", "/logs")


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        span = tracer.current_span()
        payload: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "service": SERVICE,
            "env": ENV,
            "version": VERSION,
            "dd": {"service": SERVICE, "env": ENV, "version": VERSION},
        }
        if span is not None:
            payload["dd"]["trace_id"] = str(span.trace_id)
            payload["dd"]["span_id"] = str(span.span_id)
            payload["dd.trace_id"] = str(span.trace_id)
            payload["dd.span_id"] = str(span.span_id)
        for key in (
            "event",
            "http_status",
            "sku",
            "peer_service",
            "error_type",
            "resource",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["error.kind"] = getattr(record.exc_info[0], "__name__", "Exception")
            payload["error.message"] = str(record.exc_info[1])
        return json.dumps(payload, default=str)


def setup_logging() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger(SERVICE)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False
    fmt = _JsonFormatter()
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    fh = logging.FileHandler(os.path.join(LOG_DIR, f"{SERVICE}.log"))
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


class DogStatsdClient:
    """Minimal DogStatsD client (UDP) — no extra pip dependency."""

    def __init__(self, host: str, port: int, namespace: str = "rca.") -> None:
        self.host = host
        self.port = port
        self.namespace = namespace
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def _send(self, metric: str, value: float, mtype: str, tags: Optional[list[str]] = None) -> None:
        name = f"{self.namespace}{metric}"
        tag_str = ""
        if tags:
            tag_str = "|#" + ",".join(tags)
        payload = f"{name}:{value}|{mtype}{tag_str}".encode("utf-8")
        try:
            self._sock.sendto(payload, (self.host, self.port))
        except OSError:
            pass

    def increment(self, metric: str, value: int = 1, tags: Optional[list[str]] = None) -> None:
        self._send(metric, float(value), "c", tags)

    def timing(self, metric: str, value_ms: float, tags: Optional[list[str]] = None) -> None:
        self._send(metric, float(value_ms), "ms", tags)

    def gauge(self, metric: str, value: float, tags: Optional[list[str]] = None) -> None:
        self._send(metric, float(value), "g", tags)


def dogstatsd() -> DogStatsdClient:
    return DogStatsdClient(AGENT_HOST, DSD_PORT)


def base_tags() -> list[str]:
    return [f"service:{SERVICE}", f"env:{ENV}", f"version:{VERSION}"]


def mark_span_error(span, message: str, error_type: str = "Exception") -> None:  # noqa: ANN001
    """Mark the active span with standard APM error fields only (no custom hint tags)."""
    if span is None:
        return
    span.error = 1
    span.set_tag("error.message", message)
    span.set_tag("error.type", error_type)
