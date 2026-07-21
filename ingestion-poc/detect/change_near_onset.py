"""D2 — change-near-onset: correlate incident start with deploy/config change feed.

Separate data source from ops metrics (Bucket 4 / External). Does not invent roots;
annotates detect output so Localize/Identify can prefer or surface change context.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def parse_ts(ts: str) -> datetime:
    if not ts:
        raise ValueError("empty timestamp")
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts).astimezone(timezone.utc)


def load_changes(path: Path) -> list[dict[str, Any]]:
    """Load JSONL or JSON list of change events.

    Each event: ``{ "ts", "change_type", "ref"?, "ci_id"?, "summary"? }``
    """
    if not path.is_file():
        return []
    text = path.read_text().strip()
    if not text:
        return []
    if path.suffix == ".json" and not path.name.endswith(".jsonl"):
        data = json.loads(text)
        if isinstance(data, dict) and "changes" in data:
            return list(data["changes"])
        if isinstance(data, list):
            return data
        raise ValueError(f"Unexpected JSON shape in {path}")
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def change_near_onset(
    *,
    incident_start: str | None,
    changes: list[dict[str, Any]],
    window_minutes: int = 30,
) -> dict[str, Any]:
    """Return change-in-window annotation for an incident onset."""
    if not incident_start:
        return {
            "change_near_onset": False,
            "window_minutes": window_minutes,
            "incident_start": None,
            "changes_in_window": [],
            "change_count_in_window": 0,
            "note": "no_incident_start",
        }
    onset = parse_ts(incident_start)
    window = timedelta(minutes=window_minutes)
    in_window: list[dict[str, Any]] = []
    for ch in changes:
        ts = ch.get("ts") or ch.get("timestamp")
        if not ts:
            continue
        try:
            ct = parse_ts(str(ts))
        except ValueError:
            continue
        # Change at or before onset, within window (typical deploy-then-break).
        if ct <= onset and (onset - ct) <= window:
            in_window.append(
                {
                    "ts": ct.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "change_type": ch.get("change_type") or ch.get("type") or "change",
                    "ref": ch.get("ref") or ch.get("id"),
                    "ci_id": ch.get("ci_id"),
                    "summary": ch.get("summary") or ch.get("message"),
                    "minutes_before_onset": round((onset - ct).total_seconds() / 60.0, 2),
                }
            )
    in_window.sort(key=lambda r: r["ts"])
    return {
        "change_near_onset": len(in_window) > 0,
        "window_minutes": window_minutes,
        "incident_start": onset.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "changes_in_window": in_window,
        "change_count_in_window": len(in_window),
        "detect_feature": "change_near_onset",
    }


def write_change_context(ctx: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "change_context.json"
    path.write_text(json.dumps(ctx, indent=2) + "\n")
    return path
