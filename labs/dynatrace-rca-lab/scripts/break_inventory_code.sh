#!/usr/bin/env bash
# Re-introduce the REAL KeyError bug (drop MACBOOK-PRO-14 from index) and rebuild.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/inventory/app.py"

python3 - <<'PY' "$APP"
from pathlib import Path
import sys
p = Path(sys.argv[1])
text = p.read_text()
good = '''WAREHOUSE_SKU_INDEX = {
    "IPAD-AIR": 40,
    "WATCH-ULTRA": 15,
    "MACBOOK-PRO-14": 100,
}'''
bad = '''WAREHOUSE_SKU_INDEX = {
    "IPAD-AIR": 40,
    "WATCH-ULTRA": 15,
    # "MACBOOK-PRO-14": 100,  # ← missing — causes KeyError in lookup_stock_in_warehouse
}'''
if bad in text:
    print("already buggy")
    raise SystemExit(0)
if good not in text:
    raise SystemExit("unexpected app.py contents — break manually")
p.write_text(text.replace(good, bad, 1))
print("removed MACBOOK-PRO-14 from WAREHOUSE_SKU_INDEX (real KeyError path)")
PY

cd "$ROOT"
docker compose up -d --build inventory
echo "buggy build up — probe (expect 500 / KeyError):"
sleep 2
curl -sS -w "\nHTTP %{http_code}\n" http://localhost:19080/ | head -c 400 || true
echo
