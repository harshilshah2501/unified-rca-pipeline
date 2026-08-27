#!/usr/bin/env bash
# Restore ERROR + SLOWDOWN + scenario markers to healthy baseline (DD lab only).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/inventory/app.py"

for svc in inventory product frontend; do
  echo 0 > "$ROOT/faults/${svc}.latency"
  echo false > "$ROOT/faults/${svc}.fail"
done

# Heal KeyError catalog if present (no rebuild yet).
python3 - <<'PY' "$APP"
from pathlib import Path
import sys
p = Path(sys.argv[1])
text = p.read_text()
good = '''WAREHOUSE_SKU_INDEX = {
    "WIDGET-1": 42,
    "IPAD-AIR": 40,
    "WATCH-ULTRA": 15,
    "MACBOOK-PRO-14": 100,
}'''
bad = '''WAREHOUSE_SKU_INDEX = {
    # "WIDGET-1": 42,
    "IPAD-AIR": 40,
    "WATCH-ULTRA": 15,
    "MACBOOK-PRO-14": 100,
}'''
bad_legacy = '''WAREHOUSE_SKU_INDEX = {
    # "WIDGET-1": 42,  # ← missing — KeyError in lookup_stock_in_warehouse
    "IPAD-AIR": 40,
    "WATCH-ULTRA": 15,
    "MACBOOK-PRO-14": 100,
}'''
if bad in text:
    text = text.replace(bad, good, 1)
    print("restored WIDGET-1")
elif bad_legacy in text:
    text = text.replace(bad_legacy, good, 1)
    print("restored WIDGET-1 (legacy)")
else:
    print("catalog already healthy")
p.write_text(text)
PY

# Heal SLOWDOWN lookup if present.
python3 - <<'PY' "$APP"
from pathlib import Path
import sys, re
p = Path(sys.argv[1])
text = p.read_text()
fast = '''# --- LOOKUP_ impl markers (break/heal scripts swap between FAST and SLOW) ---
def lookup_stock_in_warehouse(sku: str = "WIDGET-1") -> dict:
    """FAST: O(1) index lookup."""
    qty = WAREHOUSE_SKU_INDEX[sku]
    return {"stock": qty, "sku": sku}


# --- end LOOKUP_ ---'''
if '"""FAST: O(1) index lookup."""' in text and "_debug_row_checksum" not in text:
    print("lookup already FAST")
else:
    pat = re.compile(r"# --- LOOKUP_ impl markers.*?\# --- end LOOKUP_ ---", re.S)
    if not pat.search(text):
        raise SystemExit("LOOKUP markers missing")
    text = pat.sub(fast.strip(), text, count=1)
    print("restored LOOKUP → FAST")
    p.write_text(text)
PY

# Heal SCENARIO_MODE + RESOURCE_BURN.
python3 - <<'PY' "$APP"
from pathlib import Path
import sys, re
p = Path(sys.argv[1])
text = p.read_text()
text2, n = re.subn(
    r'SCENARIO_MODE\s*=\s*"(HEALTHY|MONITORING_DARK|AVAILABILITY_DOWN)"',
    'SCENARIO_MODE = "HEALTHY"',
    text,
    count=1,
)
if n:
    text = text2
    print("SCENARIO_MODE → HEALTHY")
else:
    print("SCENARIO_MODE marker missing?", file=sys.stderr)
    raise SystemExit(1)

idle = '''# --- RESOURCE_BURN markers (break/heal scripts swap IDLE / BURN) ---
# IDLE: no background CPU burn (RESOURCE_CONTENTION lab off).
# --- end RESOURCE_BURN ---'''
pat = re.compile(r"# --- RESOURCE_BURN markers.*?\# --- end RESOURCE_BURN ---", re.S)
if not pat.search(text):
    raise SystemExit("RESOURCE_BURN markers missing")
if "lab-resource-burn" in text or "threading.Thread" in pat.search(text).group(0):
    text = pat.sub(idle.strip(), text, count=1)
    print("RESOURCE_BURN → IDLE")
else:
    print("RESOURCE_BURN already IDLE")
p.write_text(text)
PY

cd "$ROOT"
docker compose up -d --build inventory product frontend
echo "baseline healthy — probe:"
sleep 4
python3 - <<'PY'
import time, urllib.request, urllib.error
for url, name in [
    ("http://127.0.0.1:18082/api/stock", "stock"),
    ("http://127.0.0.1:18080/api/checkout", "checkout"),
]:
    t = time.time()
    try:
        r = urllib.request.urlopen(url, timeout=15)
        print(f"  {name} {time.time()-t:.3f}s HTTP {r.status}")
    except Exception as e:
        print(f"  {name} FAIL {e}")
PY
