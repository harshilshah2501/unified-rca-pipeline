#!/usr/bin/env python3
"""RCA Visual Compiler — CLI entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _ROOT.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from frame_generator import generate_frames
from manim_generator import generate_scene
from rca_spec_parser import parse_input, spec_from_dict
from renderer import render, write_scene
from simulation_engine import get_simulator


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="RCA Visual Compiler — Text-to-Simulation-to-Manim Engine"
    )
    parser.add_argument("--input", "-i", required=True, help="Scenario markdown or JSON file")
    parser.add_argument(
        "--system",
        "-s",
        choices=["murphy", "nezha", "panorama"],
        help="Override system from spec",
    )
    parser.add_argument("--output", "-o", default="generated/output.mp4", help="Output MP4 path")
    parser.add_argument("--seed", type=int, help="Random seed override")
    parser.add_argument("--dry-run", action="store_true", help="Stop after writing frame JSON")
    parser.add_argument("--no-render", action="store_true", help="Write scene file only")
    parser.add_argument("--quality", default="ql", choices=["ql", "qm", "qh"], help="Manim quality")
    parser.add_argument(
        "--scene-out",
        default="generated/generated_scene.py",
        help="Path for generated Manim scene",
    )
    parser.add_argument(
        "--frames-out",
        default="generated/frames.json",
        help="Path for normalized animation frames JSON",
    )
    args = parser.parse_args(argv)

    raw = parse_input(args.input)
    if args.system:
        raw["system"] = args.system
    if args.seed is not None:
        raw["seed"] = args.seed

    spec = spec_from_dict(raw)
    simulator = get_simulator(spec.system)
    sim_frames = simulator.run(spec)
    anim_frames = generate_frames(spec, sim_frames)

    frames_path = Path(args.frames_out)
    frames_path.parent.mkdir(parents=True, exist_ok=True)
    frames_data = [
        {
            "frame_id": f.frame_id,
            "graph_state": {
                "nodes": f.graph_state.nodes,
                "edges": f.graph_state.edges,
                "colors": f.graph_state.colors,
                "highlights": f.graph_state.highlights,
                "positions": f.graph_state.positions,
            },
            "overlays": {
                "text": f.overlays.text,
                "charts": f.overlays.charts,
                "counters": f.overlays.counters,
            },
            "metadata": f.metadata,
        }
        for f in anim_frames
    ]
    frames_path.write_text(json.dumps(frames_data, indent=2), encoding="utf-8")
    print(f"Wrote {len(anim_frames)} animation frames to {frames_path}")

    if args.dry_run:
        print("Dry run complete.")
        return 0

    scene_code = generate_scene(anim_frames, spec)
    scene_path = write_scene(scene_code, Path(args.scene_out))
    print(f"Wrote Manim scene to {scene_path}")

    if args.no_render:
        print("Scene generated; rendering skipped.")
        return 0

    output_path = render(scene_path, Path(args.output), quality=args.quality)
    print(f"Rendered video to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
