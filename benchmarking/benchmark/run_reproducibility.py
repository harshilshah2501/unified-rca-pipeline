#!/usr/bin/env python3
"""
N-run reproducibility harness for Lean / Federated.

For each scenario pack: run the engine N times with distinct --run-id,
hash verdict.json, score bit-stability.

  reproducibility_pct = 100 if all N hashes identical else 0

Works on ObserveOps (UC-1..UC-5) or OO engine_packs (--corpus).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
N_DEFAULT = 20
DEFAULT_CORPUS = REPO / "datasets" / "observeops"
OO_PACKS = REPO / "datasets" / "openobserve_incidents" / "v1" / "engine_packs"
RESULTS = REPO / "benchmarking" / "results"

# Allow importing corpus helpers
sys.path.insert(0, str(REPO / "benchmarking"))
from benchmark.corpus_util import (  # noqa: E402
    is_frozen_pack_corpus,
    is_observeops_uc_corpus,
    pack_ids as corpus_pack_ids,
    results_subdir,
)


def _hash_verdict(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_oo_packs(corpus: Path) -> bool:
    return corpus.resolve() == OO_PACKS.resolve() or corpus.name == "engine_packs"


def _pack_ids(corpus: Path) -> list[str]:
    return corpus_pack_ids(corpus)


def _results_root(engine: str, corpus: Path) -> Path:
    base = RESULTS / engine
    sub = results_subdir(corpus)
    if sub:
        return base / sub
    return base


def _corpus_tag(corpus: Path) -> str:
    if _is_oo_packs(corpus):
        return "oo"
    if is_observeops_uc_corpus(corpus):
        return "observeops"
    if corpus.name == "incidents" and corpus.parent.name == "ecom_checkout":
        return "ecom"
    return corpus.parent.name if corpus.name == "incidents" else corpus.name


def _python() -> Path:
    py = REPO / ".venv" / "bin" / "python"
    return py if py.exists() else Path(sys.executable)


def run_reproducibility(
    engine: str,
    n: int,
    run_prefix: str,
    corpus: Path,
    pack_ids: list[str] | None = None,
) -> dict:
    corpus = corpus.resolve()
    ids = pack_ids or _pack_ids(corpus)
    script = REPO / "benchmarking" / "benchmark" / f"run_{engine}.py"
    py = _python()
    results_root = _results_root(engine, corpus)
    frozen = is_frozen_pack_corpus(corpus)

    for i in range(n):
        run_id = f"{run_prefix}-{i:02d}"
        for pid in ids:
            cmd = [
                str(py),
                str(script),
                "--corpus",
                str(corpus),
                "--uc",
                pid,
                "--run-id",
                run_id,
            ]
            if frozen:
                cmd.append("--no-shared-detect")
            subprocess.run(cmd, cwd=REPO, check=True)

    per_pack: dict[str, dict] = {}
    bit_ok = 0
    for pid in ids:
        pack_hashes: list[str] = []
        for run_dir in sorted(
            (results_root / pid).glob(f"run-{run_prefix}-*/verdict.json")
        ):
            pack_hashes.append(_hash_verdict(run_dir))
        unique = len(set(pack_hashes))
        total = len(pack_hashes)
        identical = unique == 1 and total > 0
        if identical:
            bit_ok += 1
        per_pack[pid] = {
            "runs": total,
            "unique_hashes": unique,
            "reproducibility_pct": 100.0 if identical else (0.0 if total else 0.0),
            "bit_identical": identical,
            "hashes": pack_hashes,
        }

    overall_pct = (100.0 * bit_ok / len(ids)) if ids else 0.0
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine": engine,
        "n": n,
        "run_prefix": run_prefix,
        "corpus": str(corpus),
        "pack_count": len(ids),
        "overall_reproducibility_pct": overall_pct,
        "bit_identical_packs": bit_ok,
        "definition": (
            "Per pack: run engine N times; SHA-256(verdict.json). "
            "pack reproducibility_pct = 100 iff all N hashes identical, else 0. "
            "overall = fraction of packs that are bit-identical."
        ),
        "packs": per_pack,
    }

    tag = _corpus_tag(corpus)
    out = RESULTS / f"reproducibility_{engine}_{tag}_{run_prefix}.json"
    # Keep legacy ObserveOps filename when using default UC prefix layout
    if is_observeops_uc_corpus(corpus) and set(ids) == {f"UC-{i}" for i in range(1, 6)}:
        legacy = RESULTS / f"reproducibility_{engine}_{run_prefix}.json"
        # Flat UC summary for older consumers
        flat = {pid: {k: v for k, v in d.items() if k != "hashes"} for pid, d in per_pack.items()}
        legacy.write_text(json.dumps(flat, indent=2) + "\n")
    out.write_text(json.dumps(report, indent=2) + "\n")
    report["output"] = str(out)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reproducibility: N identical runs → bit-stable verdict hash. "
            "Default N=20."
        )
    )
    parser.add_argument("--engine", choices=["federated", "lean"], required=True)
    parser.add_argument("--n", type=int, default=N_DEFAULT)
    parser.add_argument("--prefix", default="repro")
    parser.add_argument(
        "--corpus",
        type=Path,
        default=DEFAULT_CORPUS,
        help="ObserveOps corpus or OO engine_packs directory",
    )
    parser.add_argument(
        "--ids",
        nargs="*",
        help="Optional pack/UC ids (default: all under corpus)",
    )
    parser.add_argument(
        "--eligible-only",
        action="store_true",
        help="OO packs: only include_in_accuracy=true (Option B)",
    )
    parser.add_argument("--limit", type=int, help="Cap number of packs (smoke)")
    args = parser.parse_args(argv)

    corpus = args.corpus.resolve()
    ids = list(args.ids) if args.ids else _pack_ids(corpus)

    if args.eligible_only and _is_oo_packs(corpus):
        filtered = []
        for pid in ids:
            gt = json.loads((corpus / pid / "ground_truth.json").read_text())
            if gt.get("include_in_accuracy"):
                filtered.append(pid)
        ids = filtered

    if args.limit is not None:
        ids = ids[: args.limit]

    report = run_reproducibility(args.engine, args.n, args.prefix, corpus, ids)
    print(
        f"{args.engine} overall {report['overall_reproducibility_pct']:.0f}% "
        f"({report['bit_identical_packs']}/{report['pack_count']} packs bit-identical) "
        f"N={args.n}"
    )
    for pid, s in report["packs"].items():
        print(
            f"  {pid}: {s['reproducibility_pct']:.0f}% "
            f"({s['unique_hashes']} unique / {s['runs']} runs)"
        )
    print(f"Wrote {report['output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
