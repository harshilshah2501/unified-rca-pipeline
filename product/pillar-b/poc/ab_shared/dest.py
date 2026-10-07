"""Destination protocol for logical rooms (``map/`` · ``history/``).

GraphWriter publishes via ``Dest.put("map", …)`` for ``files.v1`` lab keys, or
via the map-room filesystem path for ``vortex_s3.v1`` (see ``graph.cold_vortex``).
Scope/Diagnose read a loaded snapshot — not Vortex per hop.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class Dest(Protocol):
    """Minimal room/key byte store shared by Pillar A and Pillar B."""

    def put(self, room: str, key: str, payload: bytes) -> None: ...
    def get(self, room: str, key: str) -> bytes | None: ...
    def list_keys(self, room: str) -> list[str]: ...


class MemoryDest:
    """In-memory Dest for unit tests (no disk)."""

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], bytes] = {}

    def put(self, room: str, key: str, payload: bytes) -> None:
        self._store[(room, key)] = payload

    def get(self, room: str, key: str) -> bytes | None:
        return self._store.get((room, key))

    def list_keys(self, room: str) -> list[str]:
        return sorted(k for (r, k) in self._store if r == room)


class FileDest:
    """Gate B files.v1: ``poc/out/<tenant>/{map,history}/...``."""

    def __init__(self, root: Path, tenant: str = "default") -> None:
        self.root = Path(root) / tenant
        (self.root / "map").mkdir(parents=True, exist_ok=True)
        (self.root / "history").mkdir(parents=True, exist_ok=True)

    def _path(self, room: str, key: str) -> Path:
        if room not in {"map", "history"}:
            raise ValueError(f"unknown room {room!r}")
        return self.root / room / key

    def put(self, room: str, key: str, payload: bytes) -> None:
        path = self._path(room, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    def get(self, room: str, key: str) -> bytes | None:
        path = self._path(room, key)
        if not path.exists():
            return None
        return path.read_bytes()

    def list_keys(self, room: str) -> list[str]:
        base = self.root / room
        if not base.exists():
            return []
        return sorted(p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file())
