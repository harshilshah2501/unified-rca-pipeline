from __future__ import annotations

from pathlib import Path

# pillar-b/poc/ab_shared/paths.py → POC_ROOT = pillar-b/poc
POC_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = POC_ROOT / "fixtures" / "lab_checkout"
# pillar-b/contracts
CONTRACTS = POC_ROOT.parent / "contracts"
