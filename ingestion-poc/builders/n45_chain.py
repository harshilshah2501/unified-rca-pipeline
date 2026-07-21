#!/usr/bin/env python3
"""N3→N5 chain: F1 smoke → Federated stores (N4) → Lean bundle + diagnose (N5)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ingestion-poc" / "pipeline"))
sys.path.insert(0, str(REPO_ROOT / "ingestion-poc" / "builders"))

from f1_run import resolve_inputs, run_f1  # noqa: E402
from federated_store_writer import write_federated_stores  # noqa: E402
from lean_bundle_writer import write_lean_bundle  # noqa: E402


def _diagnose_root(corpus_parent: Path, uc_id: str) -> tuple[dict, str | None]:
    env = os.environ.copy()
    env["OBSERVEOPS_CORPUS"] = str(corpus_parent)
    env["PYTHONPATH"] = f"{REPO_ROOT / 'lean-pipeline'}:{REPO_ROOT}"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "lean_rca",
            "diagnose",
            uc_id,
            "--format",
            "json",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"diagnose failed:\n{proc.stderr}\n{proc.stdout}")
    verdict = json.loads(proc.stdout)
    root = verdict.get("root_ci")
    if root is None and isinstance(verdict.get("verdict"), dict):
        root = verdict["verdict"].get("root_ci")
    return verdict, root


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="N3–N5 ingest chain smoke")
    parser.add_argument("--suite", default="UC-1")
    parser.add_argument("--vector", action="store_true")
    parser.add_argument(
        "--changes",
        type=Path,
        default=None,
        help="Optional D2 change feed for change-near-onset",
    )
    parser.add_argument(
        "--skip-diagnose",
        action="store_true",
        help="Write Lean bundle but do not run lean_rca",
    )
    args = parser.parse_args(argv)

    stream, _, suite_id = resolve_inputs(args.suite)
    if not suite_id.upper().startswith("UC-"):
        print(
            "N5 diagnose smoke requires a UC suite (UC-1..UC-5).",
            file=sys.stderr,
        )
        return 2

    t0 = time.perf_counter()
    f1_dir = REPO_ROOT / "ingestion-poc" / "out" / "f1-smoke" / suite_id
    f1_meta = run_f1(
        args.suite,
        f1_dir,
        use_vector=args.vector,
        changes_path=args.changes.resolve() if args.changes else None,
    )

    fed_dir = f1_dir / "federated_stores"
    topo = None
    topo_path = f1_dir / "topology.json"
    if topo_path.is_file():
        topo = json.loads(topo_path.read_text())
    fed_meta = write_federated_stores(
        structural_jsonl=f1_dir / "structural" / "stream.jsonl",
        out_dir=fed_dir,
        topology=topo,
        speed_jsonl=f1_dir / "speed_tier" / "feed.jsonl",
    )

    lean_parent = REPO_ROOT / "ingestion-poc" / "out" / "lean-bundles"
    lean_meta = write_lean_bundle(
        f1_dir=f1_dir,
        out_bundle=lean_parent / suite_id,
        uc_id=suite_id,
    )

    chain: dict = {
        "schema_version": "n45_chain.v1",
        "suite_id": suite_id,
        "stream": str(stream),
        "f1": {
            "out_dir": f1_meta["out_dir"],
            "anomaly_count": f1_meta["anomaly_count"],
            "sink_engine": f1_meta["sink_engine"],
        },
        "n4_federated": fed_meta,
        "n5_lean_bundle": lean_meta,
        "total_wall_ms": None,
        "diagnose": None,
    }

    if not args.skip_diagnose:
        verdict, root = _diagnose_root(lean_parent, suite_id)
        expected = lean_meta["ground_truth_root_ci"]
        chain["diagnose"] = {
            "root_ci": root,
            "expected_root_ci": expected,
            "match": root == expected,
            "signature": verdict.get("signature")
            or (verdict.get("verdict") or {}).get("signature"),
        }
        if root != expected:
            chain["total_wall_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
            print(json.dumps(chain, indent=2))
            print(
                f"\nFAIL diagnose root_ci={root} expected={expected}",
                file=sys.stderr,
            )
            return 2

    chain["total_wall_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
    (f1_dir / "n45_chain_meta.json").write_text(json.dumps(chain, indent=2) + "\n")
    print(json.dumps(chain, indent=2))
    print(f"\nN3–N5 OK → F1={f1_dir} lean={lean_parent / suite_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
