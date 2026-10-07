"""Gather PoC console status from Motadata / lab / UC artifacts."""

from __future__ import annotations

import json
import os
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
MOTADATA_SUMMARY = (
    REPO / "datasets" / "ingest_samples" / "motadata-ingest" / "broaden_summary.json"
)
LAB_DIR = REPO / "benchmarking" / "capacity" / "lab"
UC_COMPARISON = REPO / "benchmarking" / "results" / "comparison" / "comparison.json"
SSH_HOST = os.environ.get("POC_SSH_HOST", "pro6000-server")
REMOTE_REPO = os.environ.get(
    "POC_REMOTE_REPO", "/home/harshil/Projects/Unified-RCA"
)


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def ssh_reachable(host: str = SSH_HOST, timeout: float = 4.0) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                f"ConnectTimeout={int(timeout)}",
                "-o",
                "StrictHostKeyChecking=accept-new",
                host,
                "hostname; nproc; free -g | awk '/Mem:/{print $2}'",
            ],
            capture_output=True,
            text=True,
            timeout=timeout + 2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "host": host, "error": str(exc)}
    if proc.returncode != 0:
        return {
            "ok": False,
            "host": host,
            "error": (proc.stderr or proc.stdout or "ssh failed").strip()[:240],
        }
    lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    return {
        "ok": True,
        "host": host,
        "remote_hostname": lines[0] if lines else None,
        "remote_nproc": lines[1] if len(lines) > 1 else None,
        "remote_mem_gib": lines[2] if len(lines) > 2 else None,
    }


def motadata_status() -> dict[str, Any]:
    summary = _load_json(MOTADATA_SUMMARY)
    if not summary:
        return {"ok": False, "pass_count": 0, "total": 0, "incidents": []}
    incidents = summary.get("incidents") or []
    return {
        "ok": int(summary.get("pass_count") or 0) == int(summary.get("total") or 0)
        and int(summary.get("total") or 0) > 0,
        "pass_count": summary.get("pass_count"),
        "total": summary.get("total"),
        "incidents": incidents,
        "path": str(MOTADATA_SUMMARY),
    }


def lab_status() -> dict[str, Any]:
    latest_md = LAB_DIR / "LATEST.md"
    runs = sorted(
        [p for p in LAB_DIR.glob("pro6000-*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    wsl_runs = sorted(
        [p for p in LAB_DIR.glob("wsl-*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    run_dir = runs[0] if runs else (wsl_runs[0] if wsl_runs else None)
    phase0 = _load_json(run_dir / "phase0_dragonfly.json") if run_dir else None
    report = _load_json(run_dir / "lab_report.json") if run_dir else None
    eps = (phase0 or {}).get("eps")
    host = ((report or {}).get("host") or {}).get("hostname")
    tier = ((report or {}).get("host") or {}).get("tier")
    eligible = ((report or {}).get("host") or {}).get("recommended", {}).get(
        "headline_eligible"
    )
    ok = isinstance(eps, (int, float)) and float(eps) >= 50_000 and bool(eligible)
    return {
        "ok": bool(ok),
        "eps": eps,
        "p99_ms": (phase0 or {}).get("p99_latency_ms"),
        "hostname": host,
        "tier": tier,
        "run_id": run_dir.name if run_dir else None,
        "latest_md": latest_md.read_text(encoding="utf-8")[:4000]
        if latest_md.is_file()
        else None,
        "path": str(run_dir) if run_dir else None,
    }


def uc_status() -> dict[str, Any]:
    cmp_ = _load_json(UC_COMPARISON)
    if not cmp_:
        return {"ok": False, "rows": [], "summary": None}
    summary = cmp_.get("summary") or {}
    rows_out = []
    for row in cmp_.get("rows") or []:
        lean = row.get("lean") or {}
        fed = row.get("federated") or {}
        rows_out.append(
            {
                "uc_id": row.get("uc_id"),
                "winner": row.get("winner"),
                "lean_root": lean.get("root_ci"),
                "fed_root": fed.get("root_ci"),
                "lean_status": lean.get("status"),
                "fed_status": fed.get("status"),
                "by_anomaly_class": lean.get("by_anomaly_class")
                or fed.get("by_anomaly_class"),
                "C_detect_ms": lean.get("C_detect_ms")
                or lean.get("detect_latency_ms")
                or fed.get("detect_latency_ms"),
                "change_near_onset": lean.get("change_near_onset")
                if lean.get("change_near_onset") is not None
                else fed.get("change_near_onset"),
            }
        )
    lean_pass = summary.get("lean_pass") or "0/5"
    fed_pass = summary.get("federated_pass") or "0/5"
    ok = str(lean_pass).startswith("5") and str(fed_pass).startswith("5")
    return {
        "ok": ok,
        "summary": summary,
        "generated_at": cmp_.get("generated_at"),
        "run_id": cmp_.get("run_id_filter"),
        "rows": rows_out,
        "path": str(UC_COMPARISON),
    }


def stage_chips(
    motadata: dict[str, Any],
    lab: dict[str, Any],
    uc: dict[str, Any],
) -> list[dict[str, Any]]:
    """Workflow stage chips for the status rail."""
    return [
        {
            "id": "ingest",
            "label": "Ingest",
            "ok": True,
            "detail": "N1–N5 closed",
        },
        {
            "id": "detect",
            "label": "Detect",
            "ok": bool(uc.get("ok")) or any(
                r.get("by_anomaly_class") for r in (uc.get("rows") or [])
            ),
            "detail": "D1–D3 + C_detect on scoreboard",
        },
        {
            "id": "localize",
            "label": "Localize",
            "ok": bool(motadata.get("ok")) or bool(uc.get("ok")),
            "detail": f"Motadata {motadata.get('pass_count', 0)}/{motadata.get('total', 0)}",
        },
        {
            "id": "identify",
            "label": "Identify",
            "ok": bool(motadata.get("ok")),
            "detail": "I1 Motadata signatures",
        },
        {
            "id": "lab",
            "label": "Lab EPS",
            "ok": bool(lab.get("ok")),
            "detail": (
                f"{lab.get('eps'):.0f} EPS" if isinstance(lab.get("eps"), (int, float)) else "pending"
            ),
        },
        {
            "id": "l1",
            "label": "L1 Motadata",
            "ok": bool(motadata_l1_ok()),
            "detail": motadata_l1_detail(),
            "disabled": False,
        },
    ]


def motadata_l1_ok() -> bool:
    path = (
        Path(__file__).resolve().parents[2]
        / "benchmarking"
        / "results"
        / "motadata"
        / "comparison.json"
    )
    if not path.is_file():
        return False
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    s = doc.get("summary") or {}
    return str(s.get("lean_pass", "")).startswith("3/") and str(
        s.get("federated_pass", "")
    ).startswith("3/")


def motadata_l1_detail() -> str:
    path = (
        Path(__file__).resolve().parents[2]
        / "benchmarking"
        / "results"
        / "motadata"
        / "comparison.json"
    )
    if not path.is_file():
        return "Lean vs Fed compare pending"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        s = doc.get("summary") or {}
        return f"L {s.get('lean_pass')} · F {s.get('federated_pass')}"
    except (OSError, json.JSONDecodeError):
        return "compare unreadable"


def build_status(*, check_ssh: bool = True) -> dict[str, Any]:
    motadata = motadata_status()
    lab = lab_status()
    uc = uc_status()
    ssh = ssh_reachable() if check_ssh else {"ok": False, "host": SSH_HOST, "skipped": True}
    return {
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "local_hostname": socket.gethostname(),
        "local_cpu": os.cpu_count() or 1,
        "ssh": ssh,
        "remote_repo": REMOTE_REPO,
        "motadata": motadata,
        "lab": lab,
        "uc": uc,
        "stages": stage_chips(motadata, lab, uc),
    }
