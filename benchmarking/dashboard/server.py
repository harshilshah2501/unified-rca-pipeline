#!/usr/bin/env python3
"""PoC console control plane — static dashboard + job API (local / pro6000 SSH).

Bind: 127.0.0.1:8765 by default.

  .venv/bin/python benchmarking/dashboard/server.py
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from html import escape
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

DASH = Path(__file__).resolve().parent
REPO = DASH.parents[1]
sys.path.insert(0, str(DASH))

from poc_status import (  # noqa: E402
    REMOTE_REPO,
    SSH_HOST,
    build_status,
    lab_status,
    motadata_status,
    uc_status,
)

HOST = os.environ.get("POC_DASHBOARD_HOST", "127.0.0.1")
PORT = int(os.environ.get("POC_DASHBOARD_PORT", "8765"))
TOKEN = os.environ.get("POC_DASHBOARD_TOKEN", "").strip()
PY = REPO / ".venv" / "bin" / "python"
if not PY.is_file():
    PY = Path(sys.executable)

JOBS_LOCK = threading.Lock()
JOBS: dict[str, dict[str, Any]] = {}
ACTIVE_ID: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _append_log(job: dict[str, Any], line: str) -> None:
    job["log"].append(line)
    job["log_q"].put(line)


def _finish(job: dict[str, Any], code: int) -> None:
    global ACTIVE_ID
    job["status"] = "ok" if code == 0 else "failed"
    job["exit_code"] = code
    job["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _append_log(job, f"\n[exit {code}]\n")
    job["log_q"].put(None)
    with JOBS_LOCK:
        if ACTIVE_ID == job["id"]:
            ACTIVE_ID = None
    if code == 0:
        try:
            subprocess.run(
                [str(PY), str(DASH / "build_data.py")],
                cwd=str(REPO),
                check=False,
                capture_output=True,
            )
        except OSError:
            pass


def _run_local(job: dict[str, Any], cmd: list[str], *, cwd: Path | None = None) -> int:
    _append_log(job, f"$ {' '.join(cmd)}\n")
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd or REPO),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        _append_log(job, line)
    return proc.wait()


def _rsync_lab_to_remote(job: dict[str, Any]) -> None:
    paths = [
        "ingestion-poc/lab/",
        "ingestion-poc/compose/docker-compose.lab.yml",
        "ingestion-poc/pipeline/f1_run.py",
        "ingestion-poc/builders/federated_store_writer.py",
        "federated-pipeline/poc/benchmarks/phase0_dragonfly.py",
    ]
    for rel in paths:
        src = REPO / rel
        if not src.exists():
            continue
        dest = f"{SSH_HOST}:{REMOTE_REPO}/{rel}"
        cmd = ["rsync", "-az", str(src), dest]
        _append_log(job, f"$ {' '.join(cmd)}\n")
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            _append_log(job, (proc.stderr or proc.stdout or "") + "\n")
            raise RuntimeError(f"rsync failed for {rel}")


def _rsync_lab_results_back(job: dict[str, Any], run_id: str) -> None:
    remote = f"{SSH_HOST}:{REMOTE_REPO}/benchmarking/capacity/lab/{run_id}/"
    local = REPO / "benchmarking" / "capacity" / "lab" / run_id
    local.mkdir(parents=True, exist_ok=True)
    cmd = ["rsync", "-az", remote, str(local) + "/"]
    _append_log(job, f"$ {' '.join(cmd)}\n")
    subprocess.run(cmd, check=False)
    # latest pointer
    latest_remote = f"{SSH_HOST}:{REMOTE_REPO}/benchmarking/capacity/lab/LATEST.md"
    latest_local = REPO / "benchmarking" / "capacity" / "lab" / "LATEST.md"
    subprocess.run(
        ["rsync", "-az", latest_remote, str(latest_local)],
        check=False,
    )


def _run_remote(job: dict[str, Any], remote_cmd: str) -> int:
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=8",
        SSH_HOST,
        remote_cmd,
    ]
    _append_log(job, f"$ {' '.join(cmd)}\n")
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        _append_log(job, line)
    return proc.wait()


def job_motadata_broaden(job: dict[str, Any]) -> int:
    return _run_local(
        job,
        [str(PY), "ingestion-poc/adapters/build_motadata_incident.py"],
    )


def job_uc_bakeoff(job: dict[str, Any]) -> int:
    run_id = job.get("run_id") or f"ui-{_now()}"
    job["run_id"] = run_id
    steps = [
        [
            str(PY),
            "benchmarking/benchmark/run_lean.py",
            "--all",
            "--run-id",
            run_id,
        ],
        [
            str(PY),
            "benchmarking/benchmark/run_federated.py",
            "--all",
            "--run-id",
            run_id,
        ],
        [str(PY), "benchmarking/benchmark/compare.py", "--run-id", run_id],
        [str(PY), str(DASH / "build_data.py")],
    ]
    for cmd in steps:
        code = _run_local(job, cmd)
        if code != 0:
            return code
    return 0


def job_lab_eps(job: dict[str, Any]) -> int:
    target = job.get("target") or "local"
    run_id = job.get("run_id") or f"{'pro6000' if target == 'pro6000' else 'local'}-{_now()}"
    job["run_id"] = run_id
    if target == "pro6000":
        try:
            _rsync_lab_to_remote(job)
        except RuntimeError as exc:
            _append_log(job, f"ERROR: {exc}\n")
            return 2
        remote_cmd = (
            f"cd {REMOTE_REPO} && "
            "DF_PROACTOR_THREADS=8 DF_PORT=6380 "
            f".venv/bin/python ingestion-poc/lab/run_lab_eps.py "
            f"--seconds 30 --workers 16 --fanout-events 200000 "
            f"--run-id {run_id}"
        )
        code = _run_remote(job, remote_cmd)
        _rsync_lab_results_back(job, run_id)
        return code

    # local / WSL smoke defaults
    return _run_local(
        job,
        [
            str(PY),
            "ingestion-poc/lab/run_lab_eps.py",
            "--seconds",
            "8",
            "--workers",
            "4",
            "--fanout-events",
            "20000",
            "--run-id",
            run_id,
        ],
    )


def job_motadata_l1(job: dict[str, Any]) -> int:
    run_id = job.get("run_id") or f"motadata-l1-{_now()}"
    job["run_id"] = run_id
    return _run_local(
        job,
        [
            str(PY),
            "benchmarking/benchmark/run_motadata_bakeoff.py",
            "--run-id",
            run_id,
        ],
    )


RUNNERS = {
    "motadata_broaden": job_motadata_broaden,
    "uc_bakeoff": job_uc_bakeoff,
    "lab_eps": job_lab_eps,
    "motadata_l1": job_motadata_l1,
}


def start_job(kind: str, *, target: str = "local", run_id: str | None = None) -> dict[str, Any]:
    global ACTIVE_ID
    if kind not in RUNNERS:
        raise ValueError(f"unknown job: {kind}")
    if kind == "lab_eps" and target not in ("local", "pro6000"):
        raise ValueError("lab_eps target must be local|pro6000")
    with JOBS_LOCK:
        if ACTIVE_ID is not None:
            raise RuntimeError(f"job already running: {ACTIVE_ID}")
        job_id = uuid.uuid4().hex[:12]
        job: dict[str, Any] = {
            "id": job_id,
            "job": kind,
            "target": target if kind == "lab_eps" else "local",
            "run_id": run_id,
            "status": "running",
            "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "finished_at": None,
            "exit_code": None,
            "log": [],
            "log_q": queue.Queue(),
        }
        JOBS[job_id] = job
        ACTIVE_ID = job_id

    def worker() -> None:
        try:
            code = RUNNERS[kind](job)
        except Exception as exc:  # noqa: BLE001 — surface to UI log
            _append_log(job, f"ERROR: {exc}\n")
            code = 1
        _finish(job, code)

    threading.Thread(target=worker, daemon=True).start()
    return {k: v for k, v in job.items() if k != "log_q"}


def _md_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return fallback


def _markdown_page(url_path: str, text: str) -> bytes:
    title = _md_title(text, Path(url_path).name)
    payload = json.dumps(text, ensure_ascii=False)
    raw_href = escape(url_path + ("&" if "?" in url_path else "?") + "raw=1")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{escape(title)}</title>
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
<link rel="stylesheet" href="/urca-docs.css" />
<link rel="stylesheet" href="/urca-diagrams.css" />
<script src="/theme-init.js"></script>
<style>
.md-page .ud-viz {{ margin: 1.25rem 0 1.5rem; }}
.md-page .ud-chip small {{ font-weight: 400; font-size: .72rem; }}
.md-page pre.mermaid-src {{ display: none; }}
.md-page .mermaid {{
  margin: 1.1rem 0 1.35rem;
  padding: 1rem 1.1rem;
  background: var(--bg-elev);
  border: 1px solid var(--stroke);
  border-radius: 10px;
  overflow-x: auto;
}}
.md-page img {{
  max-width: 100%;
  height: auto;
  display: block;
  margin: .75rem 0 1rem;
}}
.md-page figure.doc-fig {{
  margin: .75rem 0 1.25rem;
  padding: .75rem .9rem;
  background: var(--bg-elev);
  border: 1px solid var(--stroke);
  border-radius: 10px;
  overflow-x: auto;
}}
.md-page figure.doc-fig img {{ margin: 0; }}
.md-page figure.doc-fig figcaption {{
  margin-top: .55rem;
  font-size: .82rem;
  color: var(--muted);
}}
</style>
</head>
<body class="urca-doc article">
<div class="wrap article md-page">
  <p class="md-src">Rendered from <code>{escape(url_path)}</code>
    · <a href="{raw_href}">raw markdown</a></p>
  <div id="md-content">Loading…</div>
</div>
<script src="https://cdn.jsdelivr.net/npm/marked@4.3.0/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>
(function () {{
  var src = {payload};
  var root = document.getElementById("md-content");
  if (typeof marked === "undefined") {{
    root.textContent = src;
    return;
  }}
  marked.setOptions({{ gfm: true, headerIds: true, mangle: false }});
  root.innerHTML = marked.parse(src);

  // Promote leftover ```mermaid fences (if any) into rendered diagrams
  root.querySelectorAll("pre code.language-mermaid").forEach(function (code) {{
    var pre = code.parentElement;
    var div = document.createElement("div");
    div.className = "mermaid";
    div.textContent = code.textContent;
    pre.replaceWith(div);
  }});
  if (typeof mermaid !== "undefined") {{
    var dark = !document.documentElement.getAttribute("data-theme") ||
      document.documentElement.getAttribute("data-theme") === "dark" ||
      (!document.documentElement.getAttribute("data-theme") &&
        window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
    var themeAttr = document.documentElement.getAttribute("data-theme");
    if (themeAttr === "light") dark = false;
    if (themeAttr === "dark") dark = true;
    mermaid.initialize({{
      startOnLoad: false,
      theme: dark ? "dark" : "default",
      securityLevel: "loose",
      flowchart: {{ curve: "basis", htmlLabels: true }}
    }});
    mermaid.run({{ querySelector: ".md-page .mermaid" }});
  }}

  var hash = decodeURIComponent((location.hash || "").replace(/^#/, ""));
  if (hash) {{
    var el = document.getElementById(hash);
    if (el) el.scrollIntoView();
  }}
}})();
</script>
<script src="/doc-nav.js" defer></script>
</body>
</html>
""".encode("utf-8")


def job_public(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": job["id"],
        "job": job["job"],
        "target": job.get("target"),
        "run_id": job.get("run_id"),
        "status": job["status"],
        "started_at": job["started_at"],
        "finished_at": job.get("finished_at"),
        "exit_code": job.get("exit_code"),
        "log_lines": len(job.get("log") or []),
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASH), **kwargs)

    def guess_type(self, path: str) -> str:
        ctype = super().guess_type(path)
        if ctype.split(";", 1)[0] in (
            "text/html",
            "text/css",
            "text/javascript",
            "application/javascript",
            "text/markdown",
            "text/plain",
        ) and "charset=" not in ctype:
            ctype = f"{ctype}; charset=utf-8"
        return ctype

    def end_headers(self) -> None:
        # Teaching HTML changes often; avoid stale Detect clock in the browser.
        path = urlparse(self.path).path.lower()
        if path.endswith((".html", ".js", ".css", ".md")) or path in ("/", ""):
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
        super().end_headers()

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _markdown_file(self, url_path: str) -> Path | None:
        fs = Path(self.translate_path(url_path)).resolve()
        try:
            fs.relative_to(REPO.resolve())
        except ValueError:
            return None
        if not fs.is_file() or fs.suffix.lower() != ".md":
            return None
        return fs

    def _send_markdown_html(self, url_path: str, send_body: bool) -> bool:
        fs = self._markdown_file(url_path)
        if fs is None:
            return False
        body = _markdown_page(url_path, fs.read_text(encoding="utf-8"))
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if send_body:
            self.wfile.write(body)
        return True

    def _check_token(self) -> bool:
        if not TOKEN:
            return True
        auth = self.headers.get("X-PoC-Token") or ""
        qs = parse_qs(urlparse(self.path).query)
        qtok = (qs.get("token") or [""])[0]
        return auth == TOKEN or qtok == TOKEN

    def _json(self, code: int, payload: Any) -> None:
        raw = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        body = self.rfile.read(length)
        return json.loads(body.decode("utf-8") or "{}")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-PoC-Token")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/") and not self._check_token():
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return

        if path == "/api/status":
            self._json(HTTPStatus.OK, build_status())
            return

        if path == "/api/jobs":
            with JOBS_LOCK:
                items = [job_public(j) for j in JOBS.values()]
                active = ACTIVE_ID
            items.sort(key=lambda j: j["started_at"], reverse=True)
            self._json(HTTPStatus.OK, {"active_id": active, "jobs": items[:20]})
            return

        if path.startswith("/api/jobs/") and path.endswith("/log"):
            job_id = path.split("/")[3]
            job = JOBS.get(job_id)
            if not job:
                self._json(HTTPStatus.NOT_FOUND, {"error": "job not found"})
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            # replay existing
            for line in list(job["log"]):
                data = json.dumps({"line": line})
                self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                self.wfile.flush()
            if job["status"] != "running":
                self.wfile.write(
                    f"data: {json.dumps({'done': True, 'status': job['status'], 'exit_code': job.get('exit_code')})}\n\n".encode(
                        "utf-8"
                    )
                )
                self.wfile.flush()
                return
            q: queue.Queue = job["log_q"]
            while True:
                try:
                    item = q.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    if job["status"] != "running":
                        break
                    continue
                if item is None:
                    self.wfile.write(
                        f"data: {json.dumps({'done': True, 'status': job['status'], 'exit_code': job.get('exit_code')})}\n\n".encode(
                            "utf-8"
                        )
                    )
                    self.wfile.flush()
                    break
                self.wfile.write(
                    f"data: {json.dumps({'line': item})}\n\n".encode("utf-8")
                )
                self.wfile.flush()
            return

        if path.startswith("/api/results/"):
            kind = path.rsplit("/", 1)[-1]
            if kind == "motadata":
                self._json(HTTPStatus.OK, motadata_status())
                return
            if kind == "lab":
                self._json(HTTPStatus.OK, lab_status())
                return
            if kind == "uc":
                self._json(HTTPStatus.OK, uc_status())
                return
            self._json(HTTPStatus.NOT_FOUND, {"error": "unknown kind"})
            return

        # Markdown: browsers get a hub HTML page; ?raw=1 keeps the source file.
        if path.lower().endswith(".md"):
            qs = parse_qs(parsed.query)
            want_raw = (qs.get("raw") or [""])[0].lower() in ("1", "true", "yes")
            if not want_raw:
                if self._send_markdown_html(path, send_body=True):
                    return
                self.send_error(HTTPStatus.NOT_FOUND, "markdown not found")
                return
            self.path = path

        # static
        if path == "/":
            self.path = "/index.html"
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_HEAD(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path.lower().endswith(".md"):
            qs = parse_qs(parsed.query)
            want_raw = (qs.get("raw") or [""])[0].lower() in ("1", "true", "yes")
            if not want_raw:
                if self._send_markdown_html(path, send_body=False):
                    return
                self.send_error(HTTPStatus.NOT_FOUND, "markdown not found")
                return
            self.path = path
        return SimpleHTTPRequestHandler.do_HEAD(self)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/api/jobs":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        if not self._check_token():
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        try:
            body = self._read_json()
            kind = str(body.get("job") or "")
            target = str(body.get("target") or "local")
            run_id = body.get("run_id")
            if run_id is not None:
                run_id = str(run_id)
            # Default lab target: prefer pro6000 when reachable
            if kind == "lab_eps" and "target" not in body:
                st = build_status()
                target = "pro6000" if st.get("ssh", {}).get("ok") else "local"
            job = start_job(kind, target=target, run_id=run_id)
            self._json(HTTPStatus.ACCEPTED, job_public(job) | {"id": job["id"]})
        except RuntimeError as exc:
            self._json(HTTPStatus.CONFLICT, {"error": str(exc)})
        except ValueError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except json.JSONDecodeError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid json"})


def main() -> int:
    os.chdir(DASH)
    try:
        httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as exc:
        # Single-instance guard: second process exits cleanly if :PORT is taken.
        print(f"PoC console bind failed on {HOST}:{PORT}: {exc}", file=sys.stderr)
        print("Another dashboard instance is likely already running.", file=sys.stderr)
        return 1
    print(f"PoC console http://{HOST}:{PORT}/  (repo={REPO})")
    if TOKEN:
        print("POC_DASHBOARD_TOKEN is set — send X-PoC-Token header")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
