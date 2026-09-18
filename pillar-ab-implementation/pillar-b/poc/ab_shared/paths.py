from __future__ import annotations

from pathlib import Path

# pillar-b/poc/ab_shared/paths.py → POC_ROOT = pillar-b/poc
POC_ROOT = Path(__file__).resolve().parents[1]
# Sample estate data for the customer-checkout teaching scenario (not live CMDB).
SAMPLE_ESTATE = POC_ROOT / "sample_estate" / "customer_checkout"
# pillar-b/contracts
CONTRACTS = POC_ROOT.parent / "contracts"
