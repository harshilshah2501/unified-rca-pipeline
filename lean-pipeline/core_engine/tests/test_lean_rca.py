"""Contract tests for the public Lean RCA CLI report and HTTP API."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from core_engine.observeops.engine import diagnose
from lean_rca.http import LeanRcaApp

REPO = Path(__file__).resolve().parents[3]
CORPUS = REPO / "datasets" / "observeops"
UC_IDS = [f"UC-{index}" for index in range(1, 6)]


@pytest.mark.parametrize("uc_id", UC_IDS)
def test_sre_report_preserves_engine_verdict(uc_id: str) -> None:
    report = diagnose(uc_id, CORPUS)
    ground_truth = json.loads((CORPUS / uc_id / "ground_truth.json").read_text())
    assert report["root_ci"] == ground_truth["root_ci"]
    assert report["signature"] == ground_truth["signature"]
    assert report["remediation"]
    assert report["causal_chain"][0] == report["root_ci"]
    assert report["causal_chain"][-1] == "orders-api"


@pytest.mark.parametrize("uc_id", UC_IDS[:4])
def test_infrastructure_reports_have_topology_blast_radius(uc_id: str) -> None:
    assert diagnose(uc_id, CORPUS)["blast_radius"]


def test_application_blast_radius_includes_orders_api() -> None:
    assert "orders-api" in diagnose("UC-5", CORPUS)["blast_radius"]


def _request(app: LeanRcaApp, method: str, path: str, body: bytes = b"") -> tuple[str, dict]:
    captured: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        captured["status"] = status
        captured["headers"] = headers

    response = app(
        {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": "",
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
        },
        start_response,
    )
    return str(captured["status"]), json.loads(b"".join(response))


def test_http_health_and_diagnose_smoke() -> None:
    app = LeanRcaApp()
    app.corpus_dir = CORPUS
    status, body = _request(app, "GET", "/health")
    assert status == "200 OK"
    assert body == {"status": "ok", "engine": "lean"}

    status, body = _request(app, "GET", "/v1/diagnose/UC-1")
    assert status == "200 OK"
    assert body["root_ci"] == "esxi-host-01"
    assert body["blast_radius"]
