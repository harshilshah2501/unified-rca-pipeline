"""E7 Curate — collapse a Signal storm into one CaseSeed (D3: one seed by default).

CaseSeed never writes ``map/``. It is the tip Scope reads.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from graph.case_path.signal import Signal

# Severity / class rank for picking the seed tip (higher wins).
_CLASS_RANK = {
    "ERROR": 40,
    "AVAILABILITY": 35,
    "SLOWDOWN": 30,
    "SATURATION": 25,
    "ANOMALY": 10,
}


@dataclass(frozen=True)
class CaseSeed:
    """E7 output: one honest case tip with merge rationale."""

    case_id: str
    tenant: str
    seed_ci_id: str
    seed_ci_type: str
    detect_class: str
    first_down_ts: str
    merged_signal_ids: tuple[str, ...]
    merge_rationale: str
    window_start: str | None = None
    window_end: str | None = None
    labels: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["merged_signal_ids"] = list(self.merged_signal_ids)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CaseSeed:
        return cls(
            case_id=str(d["case_id"]),
            tenant=str(d.get("tenant", "default")),
            seed_ci_id=str(d["seed_ci_id"]),
            seed_ci_type=str(d.get("seed_ci_type", "Service")),
            detect_class=str(d["detect_class"]),
            first_down_ts=str(d["first_down_ts"]),
            merged_signal_ids=tuple(d.get("merged_signal_ids") or []),
            merge_rationale=str(d.get("merge_rationale", "")),
            window_start=d.get("window_start"),
            window_end=d.get("window_end"),
            labels=dict(d.get("labels") or {}),
        )


def load_signal_storm(path_or_list: Path | str | Iterable[dict[str, Any]]) -> list[Signal]:
    """Load a Detect storm from JSON list file or in-memory dicts."""
    if isinstance(path_or_list, (str, Path)):
        data = json.loads(Path(path_or_list).read_text(encoding="utf-8"))
        if isinstance(data, dict) and "signals" in data:
            data = data["signals"]
        return [Signal.from_dict(x) for x in data]
    return [Signal.from_dict(x) if isinstance(x, dict) else x for x in path_or_list]


def curate_storm(
    signals: Iterable[Signal],
    *,
    case_id: str = "case-checkout-1",
    prefer_seed_ci: str | None = None,
) -> CaseSeed:
    """Merge correlated Signals into one CaseSeed.

    Default policy (HLD D3): **one seed**. Tip CI = ``prefer_seed_ci`` if present
    in the storm, else the CI on the highest-ranked detect_class (then earliest ts).
    """
    storm = list(signals)
    if not storm:
        raise ValueError("curate_storm requires at least one Signal")

    tenant = storm[0].tenant
    by_ci: dict[str, list[Signal]] = {}
    for s in storm:
        by_ci.setdefault(s.ci_id, []).append(s)

    def _ci_score(ci: str) -> tuple[int, str, str]:
        group = by_ci[ci]
        best_class = max(group, key=lambda s: _CLASS_RANK.get(s.detect_class, 0))
        first_ts = min(s.ts for s in group)
        return (_CLASS_RANK.get(best_class.detect_class, 0), first_ts, ci)

    if prefer_seed_ci and prefer_seed_ci in by_ci:
        seed_ci = prefer_seed_ci
    else:
        seed_ci = max(by_ci.keys(), key=_ci_score)

    seed_group = by_ci[seed_ci]
    tip = max(seed_group, key=lambda s: _CLASS_RANK.get(s.detect_class, 0))
    first_ts = min(s.ts for s in storm)
    last_ts = max(s.ts for s in storm)
    classes = sorted({s.detect_class for s in storm})
    cis = sorted(by_ci.keys())

    rationale = (
        f"D3 one-seed: merged {len(storm)} signals across {len(cis)} CIs "
        f"({', '.join(classes)}); tip={seed_ci}/{tip.detect_class} "
        f"(shared onset window {first_ts}..{last_ts})"
    )
    return CaseSeed(
        case_id=case_id,
        tenant=tenant,
        seed_ci_id=seed_ci,
        seed_ci_type=tip.ci_type,
        detect_class=tip.detect_class,
        first_down_ts=first_ts,
        merged_signal_ids=tuple(s.signal_id for s in storm),
        merge_rationale=rationale,
        window_start=first_ts,
        window_end=last_ts,
        labels={"storm_ci_ids": cis, "detect_classes": classes},
    )
