from __future__ import annotations

from pathlib import Path

# pillar-a/poc/ab_shared/paths.py → POC_ROOT = pillar-a/poc
POC_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = POC_ROOT / "fixtures" / "lab_checkout"
# pillar-a/contracts
CONTRACTS = POC_ROOT.parent / "contracts"
