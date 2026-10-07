#!/usr/bin/env python3
"""Unified RCA PoC — run the federated pipeline."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Unified RCA PoC pipeline runner")
    parser.add_argument(
        "--scenario",
        choices=["crawler", "hipster", "ingest"],
        default="crawler",
        help="Demo scenario to run",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write RCAVerdict JSON to this path",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable hop-level logging",
    )
    parser.add_argument(
        "--live-nezha",
        action="store_true",
        help="Try Nezha rca_data path (hipster only; falls back if deps/data fail)",
    )
    parser.add_argument(
        "--with-speed-tier",
        action="store_true",
        help="For hipster: ingest into Redis speed tier and score Nezha from pc: keys",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.scenario == "crawler":
        from poc.scenarios.crawler import run_crawler_scenario

        verdict = run_crawler_scenario()
        payload = verdict.to_json(indent=2)
    elif args.scenario == "ingest":
        from poc.ingest import demo_hipster_ingest
        from poc.stores.speed import SpeedStore
        import json

        speed = SpeedStore()
        result = demo_hipster_ingest(speed=speed)
        payload = json.dumps(result, indent=2, default=str)
    elif args.scenario == "hipster":
        from poc.scenarios.hipster import (
            build_hipster_detection_flag,
            build_hipster_orchestrator,
            INCIDENT_TIME,
        )

        orchestrator = build_hipster_orchestrator()
        if not args.live_nezha:
            orchestrator.nezha.prefer_dataset = False
        if args.with_speed_tier:
            from poc.adapters.nezha_speed import SpeedBackedNezhaAdapter
            from poc.ingest import demo_hipster_ingest
            from poc.stores.speed import SpeedStore

            speed = SpeedStore()
            demo_hipster_ingest(speed=speed)
            orchestrator.nezha = SpeedBackedNezhaAdapter(speed)
        flag = build_hipster_detection_flag()
        verdict = orchestrator.run_pipeline(flag, incident_time=INCIDENT_TIME)
        payload = verdict.to_json(indent=2)
    else:
        parser.error(f"Unknown scenario: {args.scenario}")
        return 1

    print(payload)

    if args.output:
        args.output.write_text(payload + "\n")
        print(f"\nWrote output to {args.output}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
