"""Stdlib WSGI HTTP interface for Lean RCA."""

from __future__ import annotations

import json
from http import HTTPStatus
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs

from core_engine.observeops.engine import diagnose

StartResponse = Callable[[str, list[tuple[str, str]]], None]


def _json_response(start_response: StartResponse, status: HTTPStatus, body: dict) -> list[bytes]:
    encoded = json.dumps(body).encode("utf-8")
    start_response(
        f"{status.value} {status.phrase}",
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(encoded))),
        ],
    )
    return [encoded]


class LeanRcaApp:
    """Small WSGI application with a corpus directory set by the CLI."""

    corpus_dir: Path | None = None

    def __call__(self, environ: dict, start_response: StartResponse) -> list[bytes]:
        method = environ["REQUEST_METHOD"]
        path = environ.get("PATH_INFO", "")

        if method == "GET" and path == "/health":
            return _json_response(start_response, HTTPStatus.OK, {"status": "ok", "engine": "lean"})

        uc_id: str | None = None
        if method == "GET" and path.startswith("/v1/diagnose/"):
            uc_id = path.removeprefix("/v1/diagnose/").strip("/")
            parse_qs(environ.get("QUERY_STRING", ""))  # Reserved for format=json compatibility.
        elif method == "POST" and path == "/v1/diagnose":
            try:
                length = int(environ.get("CONTENT_LENGTH") or 0)
                payload = json.loads(environ["wsgi.input"].read(length) or b"{}")
            except (ValueError, json.JSONDecodeError):
                return _json_response(
                    start_response, HTTPStatus.BAD_REQUEST, {"error": "invalid JSON request body"}
                )
            if "bundle" in payload and "uc_id" not in payload:
                return _json_response(
                    start_response,
                    HTTPStatus.NOT_IMPLEMENTED,
                    {"error": "inline bundle diagnosis is not implemented"},
                )
            uc_id = payload.get("uc_id")
            if not isinstance(uc_id, str) or not uc_id:
                return _json_response(
                    start_response, HTTPStatus.BAD_REQUEST, {"error": "uc_id is required"}
                )
        else:
            return _json_response(start_response, HTTPStatus.NOT_FOUND, {"error": "not found"})

        if self.corpus_dir is None:
            return _json_response(
                start_response, HTTPStatus.SERVICE_UNAVAILABLE, {"error": "corpus is not configured"}
            )
        try:
            return _json_response(start_response, HTTPStatus.OK, diagnose(uc_id, self.corpus_dir))
        except FileNotFoundError:
            return _json_response(
                start_response, HTTPStatus.NOT_FOUND, {"error": f"unknown use case: {uc_id}"}
            )


app = LeanRcaApp()
