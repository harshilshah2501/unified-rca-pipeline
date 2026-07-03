"""Manim base scene and helper methods for RCA visualizations."""

from __future__ import annotations

from manim import (
    BLUE,
    BOLD,
    DOWN,
    GRAY_A,
    GREEN,
    LEFT,
    ORANGE,
    RED,
    RIGHT,
    UP,
    WHITE,
    YELLOW,
    Circle,
    Create,
    FadeIn,
    FadeOut,
    Line,
    Rectangle,
    RoundedRectangle,
    Scene,
    Text,
    VGroup,
    Write,
)


class RCAScene(Scene):
    """Base scene with graph, propagation, histogram, and voting helpers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph_group: VGroup | None = None
        self.node_mobjects: dict[str, VGroup] = {}
        self.edge_mobjects: dict[tuple[str, str], Line] = {}
        self.overlay_group: VGroup | None = None
        self.title_group: VGroup | None = None
        self.legend_group: VGroup | None = None
        self._positions: dict[str, list[float]] = {}

    def show_title_banner(self, title: str, subtitle: str = "") -> None:
        if self.title_group is not None:
            self.remove(self.title_group)
        self.title_group = VGroup()
        heading = Text(str(title), font_size=36, weight=BOLD).to_edge(UP, buff=0.35)
        self.title_group.add(heading)
        if subtitle:
            sub = Text(str(subtitle), font_size=24, color=GRAY_A).next_to(
                heading, DOWN, buff=0.15
            )
            self.title_group.add(sub)
        self.add(self.title_group)

    def _fit_group(self, group: VGroup, max_width: float = 12.0, max_height: float = 5.5) -> None:
        if len(group) == 0:
            return
        if group.width > max_width:
            group.scale(max_width / group.width)
        if group.height > max_height:
            group.scale(max_height / group.height)
        group.move_to([0, -0.3, 0])

    def clear_graph(self) -> None:
        if self.graph_group is not None:
            self.remove(self.graph_group)
        self.graph_group = None
        self.node_mobjects.clear()
        self.edge_mobjects.clear()

    def build_graph(
        self,
        nodes: list[dict],
        edges: list[dict],
        positions: dict[str, list[float]] | None = None,
        *,
        large: bool = False,
    ) -> VGroup:
        self.clear_graph()
        self._positions = positions or {}

        scale = 1.8 if large else 3.5
        node_radius = 0.42 if large else 0.18
        font_size = 22 if large else 18
        group = VGroup()

        for node in nodes:
            nid = node["id"]
            pos = self._positions.get(nid, [0.0, 0.0])
            center = [pos[0] * scale, pos[1] * scale, 0]
            label_text = str(node.get("label", nid))
            if len(label_text) > 28:
                label_text = label_text[:25] + "..."
            circle = Circle(radius=node_radius, color=BLUE, fill_opacity=0.25, stroke_width=3)
            circle.move_to(center)
            label = Text(label_text, font_size=font_size, line_spacing=0.9)
            if label.width > node_radius * 3.2:
                label.scale(node_radius * 3.2 / label.width)
            label.move_to(center)
            node_group = VGroup(circle, label)
            self.node_mobjects[nid] = node_group
            group.add(node_group)

        for edge in edges:
            src, dst = edge["from"], edge["to"]
            if src not in self.node_mobjects or dst not in self.node_mobjects:
                continue
            color = ORANGE if edge.get("drift") else WHITE
            width = 6 if edge.get("active") or edge.get("drift") else 2
            line = Line(
                self.node_mobjects[src].get_center(),
                self.node_mobjects[dst].get_center(),
                color=color,
                stroke_width=width,
            )
            self.edge_mobjects[(src, dst)] = line
            group.add(line)

        self._fit_group(group)
        self.graph_group = group
        self.add(group)
        return group

    def update_node_states(
        self,
        colors: dict[str, str],
        highlights: list[str] | None = None,
    ) -> None:
        color_map = {
            "#22c55e": GREEN,
            "#ef4444": RED,
            "#f59e0b": ORANGE,
            "#60a5fa": BLUE,
            "#f97316": ORANGE,
            "#a855f7": ORANGE,
            "#38bdf8": BLUE,
            "#f472b6": RED,
        }
        highlights = highlights or []
        for nid, node_group in self.node_mobjects.items():
            hex_color = colors.get(nid, "#60a5fa")
            color = color_map.get(hex_color, BLUE)
            circle = node_group[0]
            circle.set_color(color)
            circle.set_fill(color, opacity=0.35)
            if nid in highlights:
                circle.set_stroke(YELLOW, width=6)

    def show_nezha_legend(self) -> None:
        if self.legend_group is not None:
            return
        self.legend_group = VGroup(
            Text("Expected (fault-free)", font_size=20, color=GREEN),
            Text("Actual (fault)", font_size=20, color=RED),
            Text("Drift point", font_size=20, color=ORANGE),
        ).arrange(RIGHT, buff=0.5).to_corner(DOWN + LEFT, buff=0.4)
        self.add(self.legend_group)

    def animate_wave_propagation(self, edge: tuple[str, str] | list) -> None:
        if isinstance(edge, list):
            edge = tuple(edge)
        src, dst = edge
        line = self.edge_mobjects.get((src, dst))
        if line is None:
            return
        self.play(Create(line), run_time=0.7)
        if dst in self.node_mobjects:
            circle = self.node_mobjects[dst][0]
            self.play(circle.animate.set_color(ORANGE).set_stroke(YELLOW, width=5), run_time=0.5)

    def show_distribution_plot(
        self,
        d1: list[float],
        d2: list[float],
        step: int = 0,
    ) -> None:
        if self.overlay_group is not None:
            self.remove(self.overlay_group)

        overlay = VGroup()
        title = Text(f"Gibbs convergence (step {step})", font_size=28).to_edge(UP)
        overlay.add(title)

        if d1 and d2:
            import numpy as np

            all_vals = d1 + d2
            lo, hi = min(all_vals), max(all_vals)
            if lo == hi:
                hi = lo + 1.0
            bins = np.linspace(lo, hi, 9)
            d1_counts, _ = np.histogram(d1, bins=bins)
            d2_counts, _ = np.histogram(d2, bins=bins)
            max_count = max(max(d1_counts), max(d2_counts), 1)

            bars = VGroup()
            for i, (c1, c2) in enumerate(zip(d1_counts, d2_counts)):
                x = i * 0.55 - 2.2
                h1 = float(c1) / max_count * 2.2
                h2 = float(c2) / max_count * 2.2
                r1 = Rectangle(width=0.22, height=max(h1, 0.08), color=GREEN, fill_opacity=0.85)
                r2 = Rectangle(width=0.22, height=max(h2, 0.08), color=RED, fill_opacity=0.85)
                r1.move_to([x - 0.12, h1 / 2 - 1.2, 0])
                r2.move_to([x + 0.12, h2 / 2 - 1.2, 0])
                bars.add(r1, r2)
            bars.scale(1.3).to_edge(RIGHT).shift(LEFT * 0.3)
            legend = VGroup(
                Text("D1 counterfactual", font_size=22, color=GREEN),
                Text("D2 observed", font_size=22, color=RED),
            ).arrange(DOWN, aligned_edge=LEFT).to_corner(DOWN + RIGHT, buff=0.4)
            overlay.add(bars, legend)

        self.overlay_group = overlay
        self.play(FadeIn(overlay), run_time=0.8)

    def show_panorama_dashboard(
        self,
        tick: int,
        batch_reports: list[dict],
        view_summaries: dict,
        pano: dict,
        consensus_locked: bool = False,
    ) -> None:
        if self.overlay_group is not None:
            self.remove(self.overlay_group)

        overlay = VGroup()
        panel = RoundedRectangle(
            width=11.5, height=3.2, corner_radius=0.15, color=BLUE, fill_opacity=0.08, stroke_width=2
        ).shift(DOWN * 2.0)
        overlay.add(panel)

        header = Text(
            f"Tick {tick} — new observer reports",
            font_size=26,
            color=YELLOW,
        ).next_to(panel.get_top(), DOWN, buff=0.2)
        overlay.add(header)

        rows = VGroup()
        if batch_reports:
            for report in batch_reports[:6]:
                row = Text(
                    f"{report.get('observer', '?')}  →  {report.get('subject', '?')}:"
                    f"{report.get('metric', '?')}  =  {report.get('status', '?')}"
                    f"  (score {report.get('score', 0):.0f})",
                    font_size=22,
                    color=RED if report.get("status") == "UNHEALTHY" else ORANGE,
                )
                rows.add(row)
        else:
            rows.add(Text("Waiting for observer reports…", font_size=22))
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.12).move_to(panel.get_center()).shift(UP * 0.15)
        overlay.add(rows)

        if pano:
            metric = next(iter(pano), "metric")
            verdict = pano[metric]
            verdict_text = Text(
                f"InferPano majority: {metric} → {verdict.get('status', '?')}"
                f"  (avg score {verdict.get('score', 0):.0f})",
                font_size=24,
                color=ORANGE if not consensus_locked else GREEN,
            ).next_to(panel, DOWN, buff=0.25)
            overlay.add(verdict_text)

        if consensus_locked:
            lock = Text("CONSENSUS LOCKED — all observers agree", font_size=28, color=GREEN)
            lock.next_to(panel, DOWN, buff=0.65)
            overlay.add(lock)

        self.overlay_group = overlay
        self.play(FadeIn(overlay), run_time=0.9)

    def show_voting_convergence(
        self,
        votes: dict,
        consensus: dict | None = None,
    ) -> None:
        """Legacy helper — prefer show_panorama_dashboard."""
        batch = [
            {
                "observer": str(k).split(":")[0],
                "subject": "?",
                "metric": str(k).split(":")[-1] if ":" in str(k) else "metric",
                "status": v.get("status", "") if isinstance(v, dict) else "",
                "score": v.get("score", 0) if isinstance(v, dict) else 0,
            }
            for k, v in (votes or {}).items()
        ]
        self.show_panorama_dashboard(0, batch, {}, consensus or {}, False)

    def show_overlay_text(self, text: str, *, hold: float = 1.2) -> None:
        if not text:
            return
        label = Text(str(text), font_size=26, line_spacing=0.9).to_edge(DOWN, buff=0.5)
        if label.width > 12:
            label.scale(12 / label.width)
        self.play(Write(label), run_time=0.6)
        self.wait(hold)
        self.play(FadeOut(label), run_time=0.4)
