from pathlib import Path

POC_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = POC_ROOT / "fixtures" / "lab_checkout"
CONTRACTS = POC_ROOT.parent / "contracts"
