#!/usr/bin/env python3
"""Regenerate docs/REPO_INVENTORY.yaml stats and optional HUB_CATALOG crawl.

Usage (from repo root):
  python3 scripts/repo_inventory.py              # print inventory summary
  python3 scripts/repo_inventory.py --write       # write docs/REPO_INVENTORY.yaml stats section
  python3 scripts/repo_inventory.py --hub-crawl   # print hub link crawl from seed pages
  python3 scripts/repo_inventory.py --hub-write   # write docs/HUB_CATALOG.generated.yaml
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, unquote

REPO = Path(__file__).resolve().parents[1]
SKIP_DIR_NAMES = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "target",
    ".pytest_cache",
    ".claude",
}


def fmt_bytes(n: int) -> str:
    x = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if x < 1024 or unit == "TiB":
            return f"{x:.0f}{unit}" if unit == "B" else f"{x:.1f}{unit}"
        x /= 1024
    return f"{n}B"


def dir_size(path: Path) -> int:
    total = 0
    if not path.is_dir() or path.is_symlink():
        return total
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES]
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                pass
    return total


def count_rg(token: str, *globs: str) -> list[str]:
    cmd = ["rg", "-l", "--glob", "*.{md,html}", token, "docs", "pillar-ab-implementation"]
    try:
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return []
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def inventory_rows() -> list[dict]:
    """Static decisions for top-level paths (actions from Phase A audit)."""
    decisions = {
        "docs": {
            "status": "active",
            "canonical_edit": True,
            "action": "keep",
            "notes": "Docs hub source; Phase E portal slim. Future zone: knowledge/",
        },
        "pillar-ab-implementation": {
            "status": "active",
            "canonical_edit": True,
            "action": "keep",
            "notes": "Motadata Pillar A/B SoT. Future zone: product/",
        },
        "benchmarking": {
            "status": "active",
            "canonical_edit": True,
            "action": "keep",
            "notes": "Bakeoff + :8765 host. Future zone: eval/benchmarking/",
        },
        "datasets": {
            "status": "active",
            "canonical_edit": False,
            "action": "keep",
            "notes": "ObserveOps UC active; large JSONL gitignored. Future: eval/datasets/",
        },
        "lean-pipeline": {
            "status": "reference",
            "canonical_edit": False,
            "action": "move",
            "notes": "ADR-001 eval history — demote to reference/lean-pipeline/",
        },
        "federated-pipeline": {
            "status": "reference",
            "canonical_edit": False,
            "action": "move",
            "notes": "Eval history; Nezha bulk gitignored. Future: reference/federated-pipeline/",
        },
        "ingestion-poc": {
            "status": "active",
            "canonical_edit": True,
            "action": "keep",
            "notes": "ingest.v1 bridge for ObserveOps replay — not Motadata writer SoT",
        },
        "labs": {
            "status": "active",
            "canonical_edit": True,
            "action": "keep",
            "notes": "Vendor fault labs; decide labs/ed-lab track vs gitignore",
        },
        "_archive": {
            "status": "archive",
            "canonical_edit": False,
            "action": "keep",
            "notes": "Parked snapshots — never day-edit. Future rename: archive/",
        },
        "KR Plan": {
            "status": "active",
            "canonical_edit": True,
            "action": "keep",
            "notes": "Management PDFs/OKRs. Optional future: management/",
        },
        "scripts": {
            "status": "active",
            "canonical_edit": True,
            "action": "keep",
            "notes": "Repo hygiene tooling (this script)",
        },
        "README.md": {
            "status": "active",
            "canonical_edit": True,
            "action": "keep",
            "notes": "Root orientation",
        },
        "repo_paths.py": {
            "status": "active",
            "canonical_edit": True,
            "action": "keep",
            "notes": "Shared path constants",
        },
        "start-poc-dash.sh": {
            "status": "active",
            "canonical_edit": True,
            "action": "keep",
            "notes": "Dashboard singleton helper",
        },
        "NAVIGATION.md": {
            "status": "host-only",
            "canonical_edit": False,
            "action": "keep",
            "notes": "Symlink → docs/NAVIGATION.md",
            "redundancy_of": "docs/NAVIGATION.md",
        },
        "ROADMAP.md": {
            "status": "host-only",
            "canonical_edit": False,
            "action": "keep",
            "notes": "Symlink → docs/ROADMAP.md",
            "redundancy_of": "docs/ROADMAP.md",
        },
        "rca-use-cases-only.md": {
            "status": "host-only",
            "canonical_edit": False,
            "action": "keep",
            "notes": "Symlink → docs/rca-use-cases-only.md",
            "redundancy_of": "docs/rca-use-cases-only.md",
        },
        "E6-E11-mapping.md": {
            "status": "archive",
            "canonical_edit": False,
            "action": "move",
            "notes": "Root ad-hoc mapping note — park under archive/ or docs/reference/",
        },
        "Vortex-unit-check.md": {
            "status": "archive",
            "canonical_edit": False,
            "action": "move",
            "notes": "Root scratch note — park under archive/ or pillar-b/docs/",
        },
        "1789302458842.gif": {
            "status": "archive",
            "canonical_edit": False,
            "action": "move",
            "notes": "Loose GIF at root — move to docs/assets/ or archive",
        },
    }

    rows = []
    for p in sorted(REPO.iterdir(), key=lambda x: x.name.lower()):
        if p.name.startswith(".git") or p.name in {".venv", "__pycache__", ".pytest_cache", ".claude", ".cursor", ".vscode"}:
            continue
        kind = "symlink" if p.is_symlink() else ("dir" if p.is_dir() else "file")
        size = 0
        if kind == "dir":
            size = dir_size(p)
        elif kind == "file":
            try:
                size = p.stat().st_size
            except OSError:
                size = 0
        base = decisions.get(
            p.name,
            {
                "status": "archive" if p.name.startswith("_") else "active",
                "canonical_edit": False,
                "action": "keep",
                "notes": "Unclassified — review in REPO_AUDIT",
            },
        )
        row = {
            "path": p.name,
            "kind": kind,
            "size_bytes": size,
            "size_human": fmt_bytes(size),
            **base,
        }
        rows.append(row)
    return rows


def write_inventory_yaml(rows: list[dict]) -> Path:
    out = REPO / "docs" / "REPO_INVENTORY.yaml"
    fact_kind = count_rg("fact_kind")
    ingest = count_rg("ingest\\.v1")
    docs = REPO / "docs"
    dash = REPO / "benchmarking" / "dashboard"
    lines = [
        f"# Generated / maintained — Unified-RCA repo inventory",
        f"generated_at: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"generator: scripts/repo_inventory.py",
        f"repo_root: {REPO}",
        "",
        "stats:",
        f"  docs_html_count: {len(list(docs.rglob('*.html')))}",
        f"  docs_md_count: {len(list(docs.rglob('*.md')))}",
        f"  docs_flat_symlinks: {sum(1 for p in docs.iterdir() if p.is_symlink())}",
        f"  dashboard_root_symlinks: {sum(1 for p in dash.iterdir() if p.is_symlink())}",
        f"  dashboard_root_real_files: {sum(1 for p in dash.iterdir() if p.is_file() and not p.is_symlink())}",
        f"  drift_fact_kind_files: {len(fact_kind)}",
        f"  drift_ingest_v1_files: {len(ingest)}",
        "",
        "top_level:",
    ]
    for r in rows:
        lines.append(f"  - path: {r['path']!r}")
        lines.append(f"    kind: {r['kind']}")
        lines.append(f"    size_human: {r['size_human']!r}")
        lines.append(f"    status: {r['status']}")
        lines.append(f"    canonical_edit: {str(r.get('canonical_edit', False)).lower()}")
        lines.append(f"    action: {r['action']}")
        if r.get("redundancy_of"):
            lines.append(f"    redundancy_of: {r['redundancy_of']!r}")
        notes = r.get("notes", "").replace("'", "''")
        lines.append(f"    notes: '{notes}'")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


# --- Hub crawl -----------------------------------------------------------------

HREF_RE = re.compile(r"""(?:href|src)=["']([^"'#]+)""", re.I)
SEED_RELATIVE = [
    "docs/index.html",
    "docs/observeops/observeops-pipeline-hld.html",
    "docs/observeops/hld-archive.html",
    "docs/NAVIGATION.md",
    "docs/fabric/README.md",
]


def resolve_hub_url(base_file: Path, href: str) -> Path | None:
    href = href.strip()
    if not href or href.startswith(("http://", "https://", "mailto:", "javascript:", "data:")):
        return None
    # Absolute site path like /docs/foo.md or /observeops-pipeline-hld.html
    if href.startswith("/"):
        path = unquote(href.split("?", 1)[0])
        # Prefer docs/ + topic; many URLs are flat and live via dashboard symlink → docs/
        candidates = [
            REPO / "docs" / path.lstrip("/"),
            REPO / "benchmarking" / "dashboard" / path.lstrip("/"),
            REPO / path.lstrip("/"),
        ]
        # Flat /foo.html often means docs/foo.html (symlink to topic folder)
        if path.count("/") == 1 or (path.startswith("/") and path.count("/") == 1):
            candidates.insert(0, REPO / "docs" / path.lstrip("/"))
        for c in candidates:
            if c.exists():
                return c.resolve()
            # try without leading docs/
            if path.startswith("/docs/"):
                alt = REPO / path[len("/docs/") :]
                # noop
            if path.endswith(".html"):
                flat = REPO / "docs" / Path(path).name
                if flat.exists():
                    return flat.resolve()
        return None
    # Relative from base_file
    target = (base_file.parent / unquote(href.split("?", 1)[0])).resolve()
    if target.exists():
        return target
    return None


def classify_path(path: Path) -> dict:
    rel = str(path.relative_to(REPO)).replace("\\", "/")
    tier = 3
    audience = "everyone"
    topic = "observeops"
    status = "current"
    action = "keep-archive"

    if "agent-tasks" in rel:
        audience, topic, status, action = "past-task", "agent-task", "stale", "move-to-archive"
        tier = 3
    elif "/print/" in rel or rel.startswith("docs/print/"):
        audience, topic, action = "everyone", "print", "keep-archive"
        tier = 3
    elif "/learning/" in rel:
        audience, topic, action = "eval-reference", "eval", "keep-archive"
        tier = 3
    elif "fabric/" in rel or "MAP_" in path.name or "map-" in path.name or "vortex" in path.name.lower():
        audience, topic = "implementer", "fabric"
        tier, action = 2, "keep-archive"
    elif any(x in path.name.lower() for x in ("dd-", "datadog")):
        audience, topic = "vendor-lab", "vendor-dd"
        tier, action = 3, "keep-archive"
    elif any(x in path.name.lower() for x in ("dt-", "dynatrace", "davis")):
        audience, topic = "vendor-lab", "vendor-dt"
        tier, action = 3, "keep-archive"
    elif any(x in path.name.lower() for x in ("ed-", "edgedelta", "edge-delta")):
        audience, topic = "vendor-lab", "vendor-ed"
        tier, action = 3, "keep-archive"
    elif "lean" in path.name.lower() or "federated" in path.name.lower() or "rca-workflow" in path.name.lower():
        audience, topic, action = "eval-reference", "eval", "keep-archive"
        tier = 3
    elif "contracts/" in rel or path.name in {
        "GRAPH_QNA.md",
        "WRITER_REGULATOR.md",
        "MAP_WRITE_READ_RECORD.md",
        "MAP_HOT_COLD_LIFECYCLE.md",
        "MAP_SCOPE_WALK_POLICY.md",
    }:
        audience, topic = "implementer", "fabric"
        tier, action = 2, "keep-prominent"
    elif path.name in {
        "observeops-pipeline-hld.html",
        "observeops-fusion-guide.html",
        "OBSERVEOPS_PIPELINE_HLD.md",
        "data-shape-journey.html",
        "GRAPH_QNA.md",
        "urca-glossary.html",
        "index.html",
    }:
        tier, audience, action = 1, "everyone", "keep-prominent"
        topic = "observeops"

    if "_consolidated_sources" in rel:
        status, action = "duplicate", "redirect"
        tier = 3
    if "_archive" in rel:
        status, action = "stale", "keep-archive"

    return {
        "canonical_file": rel,
        "hub_tier": tier,
        "audience": audience,
        "topic": topic,
        "status": status,
        "action": action,
    }


def hub_crawl() -> list[dict]:
    seen: set[Path] = set()
    queue: list[Path] = []
    for rel in SEED_RELATIVE:
        p = (REPO / rel).resolve()
        if p.exists():
            queue.append(p)

    while queue:
        cur = queue.pop(0)
        if cur in seen:
            continue
        seen.add(cur)
        if cur.suffix.lower() not in {".html", ".md"}:
            continue
        try:
            text = cur.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in HREF_RE.finditer(text):
            tgt = resolve_hub_url(cur, m.group(1))
            if tgt is None:
                continue
            try:
                tgt.relative_to(REPO)
            except ValueError:
                continue
            if tgt.suffix.lower() in {".html", ".md"} and tgt not in seen:
                queue.append(tgt)

    rows = []
    for p in sorted(seen, key=lambda x: str(x)):
        try:
            rel = p.relative_to(REPO)
        except ValueError:
            continue
        # Prefer docs/ path for URL
        url = "/" + str(rel).replace("\\", "/")
        if str(rel).startswith("docs/"):
            # flat-friendly: if file is under topic folder, also note flat name
            url = "/" + str(rel)[len("docs/") :]
            if "/" in url.strip("/"):
                # keep topic path for accuracy
                url = "/docs/" + str(rel)[len("docs/") :]
            else:
                url = "/" + str(rel)[len("docs/") :]
        meta = classify_path(p)
        rows.append({"url_path": url, **meta})
    return rows


def write_hub_catalog(rows: list[dict]) -> Path:
    out = REPO / "docs" / "HUB_CATALOG.generated.yaml"
    lines = [
        f"# Auto-generated hub crawl — merge curated overrides into HUB_CATALOG.yaml",
        f"generated_at: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"seed_count: {len(SEED_RELATIVE)}",
        f"page_count: {len(rows)}",
        "pages:",
    ]
    for r in rows:
        lines.append(f"  - url_path: {r['url_path']!r}")
        lines.append(f"    canonical_file: {r['canonical_file']!r}")
        lines.append(f"    hub_tier: {r['hub_tier']}")
        lines.append(f"    audience: {r['audience']}")
        lines.append(f"    topic: {r['topic']}")
        lines.append(f"    status: {r['status']}")
        lines.append(f"    action: {r['action']}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="Write docs/REPO_INVENTORY.yaml")
    ap.add_argument("--hub-crawl", action="store_true", help="Print hub crawl summary")
    ap.add_argument("--hub-write", action="store_true", help="Write HUB_CATALOG.generated.yaml")
    args = ap.parse_args()

    rows = inventory_rows()
    if args.write:
        path = write_inventory_yaml(rows)
        print(f"wrote {path}")
    else:
        print(f"{'path':40} {'status':12} {'action':10} size")
        for r in rows:
            print(f"{r['path']:40} {r['status']:12} {r['action']:10} {r['size_human']}")

    if args.hub_crawl or args.hub_write:
        hub = hub_crawl()
        by_tier = defaultdict(int)
        by_action = defaultdict(int)
        for r in hub:
            by_tier[r["hub_tier"]] += 1
            by_action[r["action"]] += 1
        print(f"hub pages crawled: {len(hub)}")
        print(f"  by_tier: {dict(by_tier)}")
        print(f"  by_action: {dict(by_action)}")
        if args.hub_write:
            path = write_hub_catalog(hub)
            print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
