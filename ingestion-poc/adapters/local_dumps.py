"""Helpers for Motadata local dumps (gitignored multi-GB JSONL).

Adapters default to ``datasets/ingest_samples/jsonl_resolved/``. That tree is
**not** required for ObserveOps UC replay, Pillar A/B fixtures, or the docs hub.
See ``ingestion-poc/README.md`` § Local bulk dumps.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_JSONL_RESOLVED = REPO / "datasets" / "ingest_samples" / "jsonl_resolved"

_DUMP_HELP = """\
Motadata local dump missing or empty.

  Expected: {src}
  Typical size: ~4.3G total (span.jsonl alone ~3.8G) — gitignored on purpose.

  Needed for: Motadata adapters under ingestion-poc/adapters/
  Not needed for: ObserveOps UC replay, Pillar A/B make test-all, docs hub :8765

  Place ClickHouse-resolved *.jsonl here (see datasets/ingest_samples/jsonl_resolved/README.md)
  or pass --src / --span-jsonl to an alternate directory.

  Overview: ingestion-poc/README.md
"""


def jsonl_resolved_ready(src: Path | None = None) -> bool:
    """True if the Motadata dump dir exists and contains at least one *.jsonl."""
    root = src or DEFAULT_JSONL_RESOLVED
    if not root.is_dir():
        return False
    return any(root.glob("*.jsonl"))


def require_jsonl_resolved(
    src: Path | None = None,
    *,
    required_files: list[str] | None = None,
) -> Path:
    """Exit with a clear message if Motadata dumps are absent.

    Parameters
    ----------
    src:
        Dump directory (default ``datasets/ingest_samples/jsonl_resolved``).
    required_files:
        Optional basenames that must exist (e.g. ``[\"span.jsonl\"]``).
    """
    root = (src or DEFAULT_JSONL_RESOLVED).resolve()
    if not jsonl_resolved_ready(root):
        print(_DUMP_HELP.format(src=root), file=sys.stderr)
        raise SystemExit(2)
    if required_files:
        missing = [name for name in required_files if not (root / name).is_file()]
        if missing:
            print(_DUMP_HELP.format(src=root), file=sys.stderr)
            print(f"Missing required file(s): {', '.join(missing)}", file=sys.stderr)
            raise SystemExit(2)
    return root


def require_file(path: Path, *, hint_dir: Path | None = None) -> Path:
    """Exit if a single dump file is missing."""
    p = path.resolve()
    if p.is_file():
        return p
    parent = hint_dir or p.parent
    print(_DUMP_HELP.format(src=parent), file=sys.stderr)
    print(f"Missing file: {p}", file=sys.stderr)
    raise SystemExit(2)
