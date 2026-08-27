from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Iterator, Protocol


class IngestSource(Protocol):
    def records(self) -> Iterator[dict]: ...


class ListIngestSource:
    def __init__(self, items: Iterable[dict]) -> None:
        self._items = list(items)

    def records(self) -> Iterator[dict]:
        yield from self._items


class JsonlIngestSource:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def records(self) -> Iterator[dict]:
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)
