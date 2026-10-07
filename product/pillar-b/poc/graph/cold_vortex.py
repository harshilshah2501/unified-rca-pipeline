"""Cold map packer bridge: GraphWriter ↔ ``map_vortex_cold`` (``vortex_s3.v1``).

Thin interface — inputs/outputs are ``graph_snapshot.v1`` dicts; Motadata cold
layout (parts + manifest + latest) is owned by the Rust binary.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

PROFILE_VORTEX = "vortex_s3.v1"
PROFILE_FILES = "files.v1"

_CRATE_DIR = Path(__file__).resolve().parents[2] / "map-vortex"


def resolve_map_vortex_cold() -> Path:
    """Locate ``map_vortex_cold`` binary (env override, then cargo target)."""
    env = os.environ.get("MAP_VORTEX_COLD")
    if env:
        p = Path(env)
        if p.is_file():
            return p
        raise FileNotFoundError(f"MAP_VORTEX_COLD not a file: {env}")
    cargo_target = os.environ.get("CARGO_TARGET_DIR")
    candidates = []
    if cargo_target:
        candidates.append(Path(cargo_target) / "debug" / "map_vortex_cold")
        candidates.append(Path(cargo_target) / "release" / "map_vortex_cold")
    candidates.append(_CRATE_DIR / "target" / "debug" / "map_vortex_cold")
    candidates.append(_CRATE_DIR / "target" / "release" / "map_vortex_cold")
    which = shutil.which("map_vortex_cold")
    if which:
        candidates.insert(0, Path(which))
    for c in candidates:
        if c.is_file() and os.access(c, os.X_OK):
            return c
    raise FileNotFoundError(
        "map_vortex_cold binary not found. Build with: "
        "cd pillar-ab-implementation/pillar-b/map-vortex && cargo build --bin map_vortex_cold"
    )


def map_room_root(file_dest_root: Path) -> Path:
    """``FileDest.root`` is ``…/<tenant>``; vortex tenant_map_root is ``…/<tenant>/map``."""
    return Path(file_dest_root) / "map"


def publish_vortex(
    snapshot: dict[str, Any],
    tenant_map_root: Path,
    *,
    binary: Path | None = None,
) -> dict[str, str]:
    """Write ``vortex_s3.v1`` cold tree from a validated graph_snapshot.v1 dict."""
    bin_path = binary or resolve_map_vortex_cold()
    tenant_map_root = Path(tenant_map_root)
    tenant_map_root.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tmp:
        json.dump(snapshot, tmp)
        tmp_path = Path(tmp.name)
    try:
        proc = subprocess.run(
            [
                str(bin_path),
                "publish",
                "--tenant-root",
                str(tenant_map_root),
                "--snapshot",
                str(tmp_path),
                "--tenant",
                str(snapshot["tenant"]),
                "--version",
                str(snapshot["version"]),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        tmp_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"map_vortex_cold publish failed ({proc.returncode}): {proc.stderr or proc.stdout}"
        )
    meta = {"profile": PROFILE_VORTEX, "stdout": proc.stdout}
    for line in proc.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            meta[k.strip()] = v.strip()
    return meta


def load_vortex(
    tenant_map_root: Path,
    *,
    binary: Path | None = None,
) -> dict[str, Any]:
    """Load latest cold generation into a graph_snapshot.v1 dict (walkable)."""
    bin_path = binary or resolve_map_vortex_cold()
    proc = subprocess.run(
        [str(bin_path), "load", "--tenant-root", str(tenant_map_root)],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"map_vortex_cold load failed ({proc.returncode}): {proc.stderr or proc.stdout}"
        )
    return json.loads(proc.stdout)


def looks_like_vortex_map(tenant_map_root: Path) -> bool:
    return (Path(tenant_map_root) / "latest.json").is_file()
