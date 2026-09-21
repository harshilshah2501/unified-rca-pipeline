"""Shared glue for Pillar A/B PoCs: gate, Dest, ingest sources, schemas, paths.

Writers depend on this package only — not on each other. Pillar B does not
reimplement Collect or a live Identity LUT; ``ResolvedOnlyGate`` is the E2 door.
"""

from ab_shared.reject_codes import REJECT_CODES

__all__ = ["REJECT_CODES"]
