# RCA Visual Compiler (RVC)

Text-to-Simulation-to-Manim engine for distributed systems RCA education.

RVC is a **causal simulation compiler**, not a generic video generator. It parses RCA scenario descriptions, runs system-specific simulators (Murphy, Nezha, Panorama), converts simulation output into normalized animation frames, generates Manim Python scenes, and renders MP4 videos.

## Architecture

```
scenario.md → rca_spec_parser → RCA-SPEC
    → simulation_engine (murphy | nezha | panorama)
    → frame_generator → AnimationFrame[]
    → manim_generator → generated_scene.py
    → renderer (manim CLI) → output.mp4
```

## Requirements

- Python 3.10+
- [Manim Community Edition](https://docs.manim.community/) (`pip install manim`)
- `ffmpeg` (for video encoding)
- System libraries for Manim: `libcairo`, `pango` (see Manim install docs)

Murphy simulation wraps the existing [`../murphy/`](../murphy/) package from this repo.

## Install

```bash
cd RCA-MANIM-Generator-System
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# Full pipeline — Murphy crawler incident (use fast variant for quicker render)
python run.py --input scenarios/murphy_crawler_fast.md --system murphy --output generated/crawler.mp4

# Nezha event-graph drift
python run.py --input scenarios/nezha_checkout_drift.md --system nezha --output generated/nezha.mp4

# Panorama observer voting
python run.py --input scenarios/panorama_zk_partition.md --system panorama --output generated/panorama.mp4

# Dry run — frames JSON only
python run.py --input scenarios/murphy_crawler.md --dry-run

# Generate scene without rendering
python run.py --input scenarios/murphy_crawler.md --no-render
```

### CLI flags

| Flag | Description |
|------|-------------|
| `--input` | Scenario markdown or JSON |
| `--system` | Override system (`murphy`, `nezha`, `panorama`) |
| `--output` | Output MP4 path |
| `--seed` | Random seed (deterministic simulation) |
| `--dry-run` | Write `frames.json` only |
| `--no-render` | Skip Manim CLI |
| `--quality` | `ql`, `qm`, or `qh` |

## RCA-SPEC format

Markdown scenarios use YAML frontmatter plus `## Nodes`, `## Edges`, `## Fault` sections. See [`scenarios/`](scenarios/) for examples.

## Modules

| Module | Role |
|--------|------|
| `rca_spec_parser.py` | Parse and validate RCA-SPEC |
| `simulation_engine/murphy_sim.py` | Ridge + Gibbs counterfactual (wraps `murphy/`) |
| `simulation_engine/nezha_sim.py` | Event-graph drift simulation |
| `simulation_engine/panorama_sim.py` | InferView / InferPano voting |
| `frame_generator.py` | Normalize to animation frames |
| `manim_generator.py` | Codegen Manim scene |
| `manim_helpers/rca_scene_base.py` | `RCAScene` + visualization helpers |
| `renderer.py` | Manim CLI invocation |

## Tests

```bash
pytest tests/ -v
```

## Visual metaphors

- **Murphy**: D1 vs D2 counterfactual worlds, wave propagation, Gibbs histogram convergence
- **Nezha**: Expected (green) vs actual (red) event paths, drift highlight (orange)
- **Panorama**: Observer vote bars, weighted majority consensus lock-in
