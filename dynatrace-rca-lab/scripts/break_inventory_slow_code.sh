#!/usr/bin/env bash
# Introduce REAL code-level SLOWDOWN in inventory (not fault-flag sleep):
# replace O(1) dict lookup with full WAREHOUSE_LEDGER scan + leftover checksum.
# Tuned ~9s wall / request so Davis response-time detection can fire (vs ~50ms baseline).
# Requires product/frontend request timeout >= 30s.
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

fast = '''# --- LOOKUP_ impl markers (break/heal scripts swap between FAST and SLOW) ---
def lookup_stock_in_warehouse(sku: str = "MACBOOK-PRO-14") -> dict:
    """FAST: O(1) index lookup."""
    qty = WAREHOUSE_SKU_INDEX[sku]
    return {"stock": qty, "sku": sku}


# --- end LOOKUP_ ---'''

slow = '''# --- LOOKUP_ impl markers (break/heal scripts swap between FAST and SLOW) ---
def _build_warehouse_ledger():
    """Unsorted bin rows + real SKUs at the end (MACBOOK last)."""
    # ~50k rows × heavy checksum ≈ ~9s wall (Davis SLOWDOWN needs clear RT jump)
    rows = [(f"BIN-{i:05d}", (i % 50) + 1) for i in range(50_000)]
    rows.extend(
        [
            ("IPAD-AIR", 40),
            ("WATCH-ULTRA", 15),
            ("MACBOOK-PRO-14", 100),
        ]
    )
    return rows


WAREHOUSE_LEDGER = _build_warehouse_ledger()


def _debug_row_checksum(sku: str) -> int:
    """Leftover debug checksum — runs on every ledger row during lookup."""
    acc = 0
    for _ in range(150):
        for ch in sku:
            acc = (acc * 31 + ord(ch)) & 0xFFFFFFFF
    return acc


def lookup_stock_in_warehouse(sku: str = "MACBOOK-PRO-14") -> dict:
    """SLOW: full ledger scan + per-row checksum instead of index lookup."""
    for row_sku, qty in WAREHOUSE_LEDGER:
        _ = _debug_row_checksum(row_sku)
        if row_sku == sku:
            return {"stock": qty, "sku": sku}
    raise KeyError(sku)


# --- end LOOKUP_ ---'''

if "range(50_000)" in text and "_debug_row_checksum" in text and "for _ in range(150):" in text:
    print("already slow (heavy ledger scan ~9s)")
    raise SystemExit(0)
if fast in text:
    p.write_text(text.replace(fast, slow, 1))
    print("patched lookup → heavy ledger scan + checksum (~9s)")
    raise SystemExit(0)
# replace any prior lighter SLOW block between markers
import re
pat = re.compile(
    r"# --- LOOKUP_ impl markers.*?\# --- end LOOKUP_ ---",
    re.S,
)
if not pat.search(text):
    raise SystemExit("unexpected app.py LOOKUP block — break manually")
p.write_text(pat.sub(slow.strip(), text, count=1))
print("replaced LOOKUP block → heavy ledger scan + checksum (~9s)")
PY

cd "$ROOT"
docker compose up -d --build inventory product frontend
echo "slow build up — probe (expect HTTP 200, ~8–12s wall):"
sleep 4
python3 - <<'PY'
import time, urllib.request
t = time.time()
r = urllib.request.urlopen("http://127.0.0.1:19080/", timeout=40)
body = r.read()
print(f"  {time.time()-t:.3f}s HTTP {r.status} {body[:90]!r}")
PY
