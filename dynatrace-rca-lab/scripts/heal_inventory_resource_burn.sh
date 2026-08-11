#!/usr/bin/env bash
# Remove RESOURCE_CONTENTION CPU burn thread; restore IDLE markers.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/inventory/app.py"
rm -f "$ROOT/faults/inventory.resource_burn"

python3 - <<'PY' "$APP"
from pathlib import Path
import sys, re

p = Path(sys.argv[1])
text = p.read_text()

idle = '''# --- RESOURCE_BURN markers (break/heal scripts swap IDLE / BURN) ---
# IDLE: no background CPU burn (RESOURCE_CONTENTION lab off).
# --- end RESOURCE_BURN ---'''

if "_resource_burn_loop" not in text:
    print("already idle (no burn thread)")
    raise SystemExit(0)
pat = re.compile(r"# --- RESOURCE_BURN markers.*?\# --- end RESOURCE_BURN ---", re.S)
if not pat.search(text):
    raise SystemExit("missing RESOURCE_BURN markers in app.py")
p.write_text(pat.sub(idle.strip(), text, count=1))
print("restored RESOURCE_BURN → IDLE")
PY

cd "$ROOT"
docker compose up -d --build inventory
sleep 3
python3 - <<'PY'
import time, urllib.request
t = time.time()
r = urllib.request.urlopen("http://127.0.0.1:19080/", timeout=15)
print(f"probe {time.time()-t:.3f}s HTTP {r.status}")
PY
