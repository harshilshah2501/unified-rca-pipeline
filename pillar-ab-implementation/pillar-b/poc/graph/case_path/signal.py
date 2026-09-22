"""E6 Detect output — a Signal is not a root-cause claim."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Signal:
    """One Detect emission (Door C teaching shape)."""

    signal_id: str
    tenant: str
    ci_id: str
    ci_type: str
    detect_class: str  # e.g. SLOWDOWN, ERROR, AVAILABILITY
    ts: str
    metric_id: str | None = None
    severity: str = "warning"
    observed: dict[str, Any] = field(default_factory=dict)
    labels: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Signal:
        return cls(
            signal_id=str(d["signal_id"]),
            tenant=str(d.get("tenant", "default")),
            ci_id=str(d["ci_id"]),
            ci_type=str(d.get("ci_type", "Service")),
            detect_class=str(d["detect_class"]),
            ts=str(d["ts"]),
            metric_id=d.get("metric_id"),
            severity=str(d.get("severity", "warning")),
            observed=dict(d.get("observed") or {}),
            labels=dict(d.get("labels") or {}),
        )
