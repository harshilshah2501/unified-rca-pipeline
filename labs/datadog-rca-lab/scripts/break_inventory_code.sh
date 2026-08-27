#!/usr/bin/env bash
# Introduce REAL code-level ERROR in inventory (not fault-flag):
# drop WIDGET-1 from WAREHOUSE_SKU_INDEX → KeyError in lookup_stock_in_warehouse.
# Same teaching shape as dynatrace-rca-lab/scripts/break_inventory_code.sh.
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
if bad in text:
    print("already buggy (WIDGET-1 missing from index)")
    raise SystemExit(0)
if good not in text:
    raise SystemExit("unexpected WAREHOUSE_SKU_INDEX — break manually / heal first")
p.write_text(text.replace(good, bad, 1))
print("removed WIDGET-1 from WAREHOUSE_SKU_INDEX (real KeyError path)")
PY

cd "$ROOT"
docker compose up -d --build inventory product frontend
echo "buggy build up — probe (expect inventory HTTP 500 / KeyError; checkout 502):"
sleep 4
python3 - <<'PY'
import urllib.error, urllib.request
for url, name in [
    ("http://127.0.0.1:18082/api/stock", "stock"),
    ("http://127.0.0.1:18080/api/checkout", "checkout"),
]:
    try:
        r = urllib.request.urlopen(url, timeout=15)
        print(f"  {name} HTTP {r.status} {r.read()[:120]!r}")
    except urllib.error.HTTPError as e:
        body = e.read()[:160]
        print(f"  {name} HTTP {e.code} {body!r}")
PY
