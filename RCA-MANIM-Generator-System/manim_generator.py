"""Generate Manim Python scene source from animation frames."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from frame_generator import AnimationFrame
from rca_spec_parser import RCASpec


def _frame_to_dict(frame: AnimationFrame) -> dict[str, Any]:
    return {
        "frame_id": frame.frame_id,
        "graph_state": asdict(frame.graph_state),
        "overlays": asdict(frame.overlays),
        "metadata": frame.metadata,
    }


def generate_scene(frames: list[AnimationFrame], spec: RCASpec) -> str:
    frames_json = json.dumps([_frame_to_dict(f) for f in frames], indent=2)
    style = spec.visualization.style
    system = spec.system

    lines = [
        '"""Auto-generated RCA Visual Compiler scene."""',
        "",
        "from __future__ import annotations",
        "",
        "import json",
        "",
        "from manim_helpers.rca_scene_base import RCAScene as BaseRCAScene",
        "",
        f"FRAMES = json.loads({json.dumps(frames_json)})",
        "",
        "",
        "class RCAScene(BaseRCAScene):",
        "    def construct(self):",
        f'        style = "{style}"',
        f'        system = "{system}"',
        "        legend_shown = False",
        "        for frame in FRAMES:",
        "            gs = frame['graph_state']",
        "            ov = frame['overlays']",
        "            meta = frame.get('metadata', {})",
        "",
        "            for chart in ov.get('charts', []):",
        "                if chart.get('type') == 'title':",
        "                    self.show_title_banner(chart.get('title', ''), chart.get('subtitle', ''))",
        "                elif chart.get('type') == 'panorama_dashboard':",
        "                    self.show_title_banner(chart.get('title', ''), chart.get('subtitle', ''))",
        "",
        "            if gs.get('nodes'):",
        "                large = style in ('graph', 'vote')",
        "                self.build_graph(gs['nodes'], gs['edges'], gs.get('positions', {}), large=large)",
        "                if gs.get('colors'):",
        "                    self.update_node_states(gs['colors'], gs.get('highlights', []))",
        "",
        "            if style == 'graph':",
        "                if not legend_shown:",
        "                    self.show_nezha_legend()",
        "                    legend_shown = True",
        "                for edge in gs.get('edges', []):",
        "                    if edge.get('active'):",
        "                        self.animate_wave_propagation((edge['from'], edge['to']))",
        "                if meta.get('drift_edge') and frame['frame_id'] > meta.get('drift_index', -1):",
        "                    drift = meta['drift_edge']",
        "                    if drift:",
        "                        self.animate_wave_propagation(tuple(drift))",
        "",
        "            if style == 'wave' and meta.get('phase') == 'propagation':",
        "                for edge in gs.get('edges', []):",
        "                    if edge.get('active'):",
        "                        self.animate_wave_propagation((edge['from'], edge['to']))",
        "",
        "            if style in ('wave', 'histogram') and ov.get('charts'):",
        "                for chart in ov['charts']:",
        "                    if chart.get('type') == 'histogram':",
        "                        series = chart.get('series', [])",
        "                        d1, d2 = [], []",
        "                        for s in series:",
        "                            bins = s.get('bins', [])",
        "                            expanded = []",
        "                            for b in bins:",
        "                                mid = (b['bin_start'] + b['bin_end']) / 2",
        "                                expanded.extend([mid] * b['count'])",
        "                            if s['name'] == 'D1':",
        "                                d1 = expanded",
        "                            elif s['name'] == 'D2':",
        "                                d2 = expanded",
        "                        self.show_distribution_plot(d1, d2, frame['frame_id'])",
        "",
        "            if style == 'vote':",
        "                for chart in ov.get('charts', []):",
        "                    if chart.get('type') == 'panorama_dashboard':",
        "                        self.show_panorama_dashboard(",
        "                            ov.get('counters', {}).get('tick', frame['frame_id'] + 1),",
        "                            chart.get('batch_reports', []),",
        "                            chart.get('view_summaries', {}),",
        "                            chart.get('pano', {}),",
        "                            chart.get('consensus_locked', False),",
        "                        )",
        "",
        "            if ov.get('text'):",
        "                self.show_overlay_text(ov['text'], hold=1.5)",
        "            else:",
        "                self.wait(1.2 if style in ('graph', 'vote') else 0.4)",
        "",
    ]
    return "\n".join(lines)
