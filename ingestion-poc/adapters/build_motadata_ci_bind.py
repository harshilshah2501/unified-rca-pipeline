#!/usr/bin/env python3
"""Build Motadata CI-bind table from metric_string object.name / system.name."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_SRC = REPO / "datasets" / "ingest_samples" / "jsonl_resolved"
DEFAULT_OUT = REPO / "datasets" / "ingest_samples" / "motadata-ingest" / "ci_bind.json"

# When Motadata string metrics lack object.name/system.name, synthesize a stable id.
_PLUGIN_FALLBACK_PREFIX = {
    426: "proxmox-ve",
    88: "linux-host",
    157: "network-device",
    181: "windows-host",
    199: "ping-target",
}


def _pick_name(fields: dict) -> str | None:
    for key in (
        "object.name",
        "system.name",
        "host.name",
        "hostname",
        "device.name",
        "target.name",
    ):
        val = fields.get(key)
        if val:
            return str(val).strip()
    # Last resort: any *.name string field that looks like a hostname
    for key, val in fields.items():
        if not key.endswith(".name") or not isinstance(val, str):
            continue
        name = val.strip()
        if name and " " not in name and len(name) < 128:
            return name
    return None


def _fallback_ci(mid: str, plugin_id: object) -> str:
    prefix = _PLUGIN_FALLBACK_PREFIX.get(int(plugin_id) if plugin_id is not None else -1)
    if prefix:
        return f"{prefix}-{mid}"
    return f"monitor-{mid}"


def build_ci_bind(src: Path) -> dict:
    bind: dict[str, dict] = {}
    path = src / "metric_string.jsonl"
    if not path.is_file():
        return {"schema_version": "motadata_ci_bind.v1", "monitors": {}, "miss_count": 0}

    seen_ids: dict[str, object] = {}
    for line in path.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        mid = str(row.get("id"))
        plugin_id = row.get("plugin_id")
        seen_ids[mid] = plugin_id
        fields = row.get("fields") or {}
        name = _pick_name(fields)
        if not name:
            continue
        entry = bind.setdefault(
            mid,
            {
                "monitor_id": mid,
                "ci_id": name,
                "ci_type": "Host",
                "plugin_id": plugin_id,
                "aliases": [],
                "bind_source": "string_name",
            },
        )
        if name and name not in entry["aliases"] and name != entry["ci_id"]:
            entry["aliases"].append(name)
        # Prefer object.name over softer keys when both appear
        if fields.get("object.name"):
            entry["ci_id"] = str(fields["object.name"]).strip()
            entry["bind_source"] = "object.name"

    # Fill monitors that only have inventory/string fields without a hostname key.
    fallback_count = 0
    for mid, plugin_id in seen_ids.items():
        if mid in bind:
            continue
        bind[mid] = {
            "monitor_id": mid,
            "ci_id": _fallback_ci(mid, plugin_id),
            "ci_type": "Host",
            "plugin_id": plugin_id,
            "aliases": [],
            "bind_source": "plugin_fallback",
        }
        fallback_count += 1

    return {
        "schema_version": "motadata_ci_bind.v1",
        "source": str(src / "metric_string.jsonl"),
        "monitor_count": len(bind),
        "fallback_count": fallback_count,
        "monitors": bind,
        "note": (
            "ci_id from object.name/system.name/host.name when present; "
            "else plugin_fallback-{id}"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Motadata CI bind table")
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    from local_dumps import require_jsonl_resolved

    require_jsonl_resolved(args.src)

    doc = build_ci_bind(args.src.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2) + "\n")
    print(
        f"wrote {args.out} monitors={doc.get('monitor_count', 0)} "
        f"fallback={doc.get('fallback_count', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
