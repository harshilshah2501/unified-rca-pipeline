#!/usr/bin/env bash
# Heal the REAL code bug (restore MACBOOK-PRO-14 in WAREHOUSE_SKU_INDEX) and rebuild.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/inventory/app.py"

python3 - <<'PY' "$APP"
from pathlib import Path
import sys
p = Path(sys.argv[1])
text = p.read_text()
bad = '''WAREHOUSE_SKU_INDEX = {
    "IPAD-AIR": 40,
    "WATCH-ULTRA": 15,
    # "MACBOOK-PRO-14": 100,  # ← missing — causes KeyError in lookup_stock_in_warehouse
}'''
good = '''WAREHOUSE_SKU_INDEX = {
    "IPAD-AIR": 40,
    "WATCH-ULTRA": 15,
    "MACBOOK-PRO-14": 100,
}'''
if bad not in text:
    if '"MACBOOK-PRO-14": 100' in text and "# ← missing" not in text:
        print("already healthy")
        raise SystemExit(0)
    raise SystemExit("unexpected app.py contents — heal manually")
p.write_text(text.replace(bad, good, 1))
print("patched MACBOOK-PRO-14 back into WAREHOUSE_SKU_INDEX")
PY

cd "$ROOT"
docker compose up -d --build inventory
echo "healed + rebuilt — probe:"
sleep 2
curl -sS -w "\nHTTP %{http_code}\n" http://localhost:19080/ || true
