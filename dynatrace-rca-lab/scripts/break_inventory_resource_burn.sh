#!/usr/bin/env bash
# RESOURCE_CONTENTION: background CPU burn thread (HTTP lookup stays O(1) / fast).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/inventory/app.py"
mkdir -p "$ROOT/faults"
echo "on" > "$ROOT/faults/inventory.resource_burn"

python3 - <<'PY' "$APP"
from pathlib import Path
import sys, re

p = Path(sys.argv[1])
text = p.read_text()

idle = '''# --- RESOURCE_BURN markers (break/heal scripts swap IDLE / BURN) ---
# IDLE: no background CPU burn (RESOURCE_CONTENTION lab off).
# --- end RESOURCE_BURN ---'''

burn = '''# --- RESOURCE_BURN markers (break/heal scripts swap IDLE / BURN) ---
import threading
import time as _time


def _resource_burn_loop():
    """Background CPU spin for RESOURCE_CONTENTION Detect (not request-path SLOWDOWN)."""
    while True:
        x = 0
        for i in range(500_000):
            x = (x + i * i) & 0xFFFFFFFF
        _time.sleep(0)  # yield


_burn_thread = threading.Thread(target=_resource_burn_loop, name="lab-resource-burn", daemon=True)
_burn_thread.start()
log.info("RESOURCE_CONTENTION lab: background CPU burn thread started")
# --- end RESOURCE_BURN ---'''

if "_resource_burn_loop" in text:
    print("already burning")
    raise SystemExit(0)
pat = re.compile(r"# --- RESOURCE_BURN markers.*?\# --- end RESOURCE_BURN ---", re.S)
if not pat.search(text):
    raise SystemExit("missing RESOURCE_BURN markers in app.py")
p.write_text(pat.sub(burn.strip(), text, count=1))
print("patched → background CPU burn thread")
PY

cd "$ROOT"
docker compose up -d --build inventory
sleep 3
echo "probe (expect fast HTTP 200 while CPU burns in background):"
python3 - <<'PY'
import time, urllib.request
t = time.time()
r = urllib.request.urlopen("http://127.0.0.1:19080/", timeout=15)
print(f"  {time.time()-t:.3f}s HTTP {r.status}")
PY
echo "Heal: ./scripts/heal_inventory_resource_burn.sh"
