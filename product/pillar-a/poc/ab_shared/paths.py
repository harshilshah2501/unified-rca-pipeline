from __future__ import annotations

from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[1]
# Sample estate data for the customer-checkout teaching scenario (not live CMDB).
SAMPLE_ESTATE = POC_ROOT / "sample_estate" / "customer_checkout"
# Slice SoT (not a package-local contracts/ mirror)
CONTRACTS = POC_ROOT.parents[1] / "contracts"
