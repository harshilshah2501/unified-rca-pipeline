"""Command-line entry point for the ObserveOps Lean RCA API."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from wsgiref.simple_server import make_server

from core_engine.observeops.engine import diagnose
from lean_rca.http import app
from lean_rca.report import format_human_report


def default_corpus_dir() -> Path:
    """Resolve the ObserveOps corpus, allowing a deployment override."""
    configured = os.environ.get("OBSERVEOPS_CORPUS")
    if configured:
        return Path(configured)
    try:
        from repo_paths import OBSERVEOPS_CORPUS

        return OBSERVEOPS_CORPUS
    except ImportError:
        return Path(__file__).resolve().parents[2] / "datasets" / "observeops"


def _diagnose(args: argparse.Namespace) -> int:
    report = diagnose(args.uc_id, default_corpus_dir())
    if args.format == "report":
        print(format_human_report(report))
    else:
        print(json.dumps(report, indent=2))
    return 0


def _serve(args: argparse.Namespace) -> int:
    app.corpus_dir = default_corpus_dir()
    with make_server(args.host, args.port, app) as server:
        print(f"Lean RCA API listening on http://{args.host}:{args.port}", flush=True)
        server.serve_forever()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ObserveOps Lean RCA")
    subcommands = parser.add_subparsers(dest="command", required=True)

    diagnose_parser = subcommands.add_parser("diagnose", help="Diagnose an ObserveOps UC")
    diagnose_parser.add_argument("uc_id", help="Use case id, for example UC-1")
    diagnose_parser.add_argument("--format", choices=("json", "report"), default="json")
    diagnose_parser.set_defaults(handler=_diagnose)

    serve_parser = subcommands.add_parser("serve", help="Serve the HTTP API")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8780)
    serve_parser.set_defaults(handler=_serve)

    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except FileNotFoundError as exc:
        parser.error(f"ObserveOps bundle not found: {exc.filename or exc}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
