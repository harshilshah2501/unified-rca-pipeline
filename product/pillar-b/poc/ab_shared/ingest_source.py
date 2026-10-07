"""Ingest stream adapters: JSONL files or in-memory lists of ``ingest.v1`` dicts.

Lab CLI and tests feed GraphWriter through these; product would stream from
the post-Identity bus into the same ``IngestSource.records()`` shape.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Iterator, Protocol


class IngestSource(Protocol):
    def records(self) -> Iterator[dict]: ...


class ListIngestSource:
    """Unit-test helper: inject one-off NOOP/DROP lines without new estate files."""

    def __init__(self, items: Iterable[dict]) -> None:
        self._items = list(items)

    def records(self) -> Iterator[dict]:
        yield from self._items


class JsonlIngestSource:
    """One JSON object per line (sample estate streams, reject tapes)."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def records(self) -> Iterator[dict]:
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)
