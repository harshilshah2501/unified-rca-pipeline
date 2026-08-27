from __future__ import annotations

from dataclasses import dataclass

from ab_shared import reject_codes as rc


@dataclass(frozen=True)
class GateResult:
    accepted: bool
    reason: str | None = None


class IdentityGate:
    def admit(self, record: dict) -> GateResult: ...


class ResolvedOnlyGate:
    """Pass only identity.status = resolved."""

    def admit(self, record: dict) -> GateResult:
        identity = record.get("identity")
        if not isinstance(identity, dict):
            return GateResult(False, rc.IDENTITY_UNRESOLVED)
        status = identity.get("status")
        if status == "resolved":
            return GateResult(True, None)
        if status == "synthesized":
            return GateResult(False, rc.IDENTITY_SYNTHESIZED)
        return GateResult(False, rc.IDENTITY_UNRESOLVED)
