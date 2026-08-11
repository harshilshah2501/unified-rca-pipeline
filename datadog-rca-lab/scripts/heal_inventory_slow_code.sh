#!/usr/bin/env bash
# Heal code-level SLOWDOWN: restore O(1) WAREHOUSE_SKU_INDEX lookup and rebuild.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/inventory/app.py"

for svc in inventory product frontend; do
  echo 0 > "$ROOT/faults/${svc}.latency"
  echo false > "$ROOT/faults/${svc}.fail"
done

python3 - <<'PY' "$APP"
from pathlib import Path
import sys
import re

p = Path(sys.argv[1])
text = p.read_text()

fast = '''# --- LOOKUP_ impl markers (break/heal scripts swap between FAST and SLOW) ---
def lookup_stock_in_warehouse(sku: str = "WIDGET-1") -> dict:
    """FAST: O(1) index lookup."""
    qty = WAREHOUSE_SKU_INDEX[sku]
    return {"stock": qty, "sku": sku}


# --- end LOOKUP_ ---'''

if '"""FAST: O(1) index lookup."""' in text and "_debug_row_checksum" not in text:
    print("already healthy (O(1) index)")
    raise SystemExit(0)

pat = re.compile(
    r"# --- LOOKUP_ impl markers.*?\# --- end LOOKUP_ ---",
    re.S,
)
if not pat.search(text):
    raise SystemExit("unexpected app.py LOOKUP block — heal manually")
p.write_text(pat.sub(fast.strip(), text, count=1))
print("restored lookup_stock_in_warehouse → O(1) WAREHOUSE_SKU_INDEX")
PY

cd "$ROOT"
docker compose up -d --build inventory product frontend
echo "healed + rebuilt — probe (expect fast HTTP 200):"
sleep 3
python3 - <<'PY'
import time, urllib.request
t = time.time()
r = urllib.request.urlopen("http://127.0.0.1:18082/api/stock", timeout=15)
print(f"  stock {time.time()-t:.3f}s HTTP {r.status}")
t = time.time()
r = urllib.request.urlopen("http://127.0.0.1:18080/api/checkout", timeout=15)
print(f"  checkout {time.time()-t:.3f}s HTTP {r.status}")
PY
