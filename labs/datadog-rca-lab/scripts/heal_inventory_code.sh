#!/usr/bin/env bash
# Heal code-level ERROR: restore WIDGET-1 in WAREHOUSE_SKU_INDEX and rebuild.
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
# also accept legacy commented form from older breaks
bad_legacy = '''WAREHOUSE_SKU_INDEX = {
    # "WIDGET-1": 42,  # ← missing — KeyError in lookup_stock_in_warehouse
    "IPAD-AIR": 40,
    "WATCH-ULTRA": 15,
    "MACBOOK-PRO-14": 100,
}'''
if good in text and bad not in text and bad_legacy not in text:
    print("already healthy (WIDGET-1 present)")
    raise SystemExit(0)
if bad in text:
    p.write_text(text.replace(bad, good, 1))
elif bad_legacy in text:
    p.write_text(text.replace(bad_legacy, good, 1))
else:
    raise SystemExit("unexpected WAREHOUSE_SKU_INDEX — heal manually")
print("restored WIDGET-1 in WAREHOUSE_SKU_INDEX")
PY

cd "$ROOT"
docker compose up -d --build inventory product frontend
echo "healed + rebuilt — probe (expect HTTP 200):"
sleep 4
python3 - <<'PY'
import time, urllib.request
t = time.time()
r = urllib.request.urlopen("http://127.0.0.1:18082/api/stock", timeout=15)
print(f"  stock {time.time()-t:.3f}s HTTP {r.status}")
t = time.time()
r = urllib.request.urlopen("http://127.0.0.1:18080/api/checkout", timeout=15)
print(f"  checkout {time.time()-t:.3f}s HTTP {r.status}")
PY
