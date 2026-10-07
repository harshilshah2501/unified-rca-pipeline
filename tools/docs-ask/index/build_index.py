#!/usr/bin/env python3
"""Build a chunked documentation index for docs-ask (Worker retrieval + citations)."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from fnmatch import fnmatch
from html import unescape
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = Path(__file__).resolve().parent / "paths.yaml"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "worker" / "public" / "docs-index.json"


@dataclass
class Chunk:
    id: str
    path: str
    title: str
    heading: str
    start_line: int
    text: str
    cite_url: str


def load_config() -> dict:
    raw = CONFIG_PATH.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(raw)
    # Minimal fallback if PyYAML missing in CI
    raise SystemExit("PyYAML required: pip install pyyaml")


def should_include(rel: str, cfg: dict) -> bool:
    rel = rel.replace("\\", "/")
    for pat in cfg.get("exclude_globs", []):
        if fnmatch(rel, pat):
            return False
    allow = cfg.get("include_files") or []
    if allow:
        return rel in set(allow)
    for pat in cfg.get("include_globs", []):
        if fnmatch(rel, pat):
            return True
    return False


def strip_html(html: str) -> str:
    html = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    html = unescape(html)
    html = re.sub(r"\s+", " ", html).strip()
    return html


def extract_title(content: str, path: Path) -> str:
    if path.suffix == ".md":
        for line in content.splitlines():
            m = re.match(r"^#\s+(.+)$", line.strip())
            if m:
                return m.group(1).strip()
    m = re.search(r"(?is)<title[^>]*>([^<]+)</title>", content)
    if m:
        return unescape(m.group(1)).strip()
    return path.stem.replace("-", " ").replace("_", " ")


def plain_text(content: str, path: Path) -> str:
    if path.suffix == ".html":
        return strip_html(content)
    # markdown: drop fenced code blocks for cleaner retrieval (keep inline)
    out: list[str] = []
    in_fence = False
    for line in content.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        out.append(line)
    return "\n".join(out)


def chunk_text(text: str, max_chars: int, overlap: int) -> list[tuple[str, int]]:
    """Return (chunk_body, approximate_start_line) pieces."""
    lines = text.splitlines()
    if not lines:
        return []
    chunks: list[tuple[str, int]] = []
    buf: list[str] = []
    buf_start = 1
    size = 0
    line_no = 0
    for line in lines:
        line_no += 1
        if not buf:
            buf_start = line_no
        buf.append(line)
        size += len(line) + 1
        if size >= max_chars:
            body = "\n".join(buf).strip()
            if body:
                chunks.append((body, buf_start))
            # overlap tail
            tail: list[str] = []
            tail_size = 0
            for prev in reversed(buf):
                tail_size += len(prev) + 1
                tail.insert(0, prev)
                if tail_size >= overlap:
                    break
            buf = tail
            size = sum(len(x) + 1 for x in buf)
    if buf:
        body = "\n".join(buf).strip()
        if body:
            chunks.append((body, buf_start))
    return chunks


def github_cite_url(cfg: dict, rel: str, start_line: int) -> str:
    gh = cfg["github"]
    base = f"https://github.com/{gh['owner']}/{gh['repo']}/blob/{gh['branch']}/{rel}"
    if start_line > 1:
        return f"{base}#L{start_line}"
    return base


def build_index(out_path: Path) -> dict:
    cfg = load_config()
    max_chars = int(cfg.get("chunking", {}).get("max_chars", 2400))
    overlap = int(cfg.get("chunking", {}).get("overlap_chars", 200))
    max_text = int(cfg.get("chunking", {}).get("max_text_chars", 0) or 0)

    chunks: list[Chunk] = []
    seen_paths: set[str] = set()

    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".html"}:
            continue
        try:
            rel = path.relative_to(ROOT).as_posix()
        except ValueError:
            continue
        if rel.startswith("docs/") and (ROOT / "knowledge" / rel[5:]).exists():
            # Avoid indexing duplicate via docs -> knowledge shim
            continue
        if not should_include(rel, cfg):
            continue
        if rel in seen_paths:
            continue
        seen_paths.add(rel)

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        title = extract_title(content, path)
        text = plain_text(content, path)
        if len(text) < 40:
            continue

        for i, (body, start_line) in enumerate(chunk_text(text, max_chars, overlap)):
            heading = ""
            for line in body.splitlines()[:8]:
                if line.strip().startswith("#"):
                    heading = re.sub(r"^#+\s*", "", line.strip())
                    break
            chunk_id = hashlib.sha256(f"{rel}:{i}:{start_line}".encode()).hexdigest()[:16]
            text_out = body if not max_text else body[:max_text]
            chunks.append(
                Chunk(
                    id=chunk_id,
                    path=rel,
                    title=title,
                    heading=heading or title,
                    start_line=start_line,
                    text=text_out,
                    cite_url=github_cite_url(cfg, rel, start_line),
                )
            )

    meta = {
        "schema_version": "docs_index.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(ROOT.name),
        "chunk_count": len(chunks),
        "github": cfg["github"],
    }
    payload = {"meta": meta, "chunks": [asdict(c) for c in chunks]}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return meta


def main() -> None:
    out = DEFAULT_OUT
    if len(sys.argv) > 1:
        out = Path(sys.argv[1])
    meta = build_index(out)
    print(f"Wrote {meta['chunk_count']} chunks -> {out}")


if __name__ == "__main__":
    main()
