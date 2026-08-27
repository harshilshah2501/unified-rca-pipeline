#!/usr/bin/env bash
# Heal RESOURCE_CONTENTION burn thread → IDLE.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/inventory/app.py"

python3 - <<'PY' "$APP"
from pathlib import Path
import sys, re
p = Path(sys.argv[1])
text = p.read_text()
idle = '''# --- RESOURCE_BURN markers (break/heal scripts swap IDLE / BURN) ---
# IDLE: no background CPU burn (RESOURCE_CONTENTION lab off).
# --- end RESOURCE_BURN ---'''
pat = re.compile(r"# --- RESOURCE_BURN markers.*?\# --- end RESOURCE_BURN ---", re.S)
if not pat.search(text):
    raise SystemExit("RESOURCE_BURN markers missing")
if "lab-resource-burn" not in text:
    print("already idle")
else:
    text = pat.sub(idle.strip(), text, count=1)
    print("RESOURCE_BURN → IDLE")
    p.write_text(text)
PY

cd "$ROOT"
docker compose up -d --build inventory product frontend
echo "burn healed — probe:"
sleep 3
python3 - <<'PY'
import time, urllib.request
t = time.time()
r = urllib.request.urlopen("http://127.0.0.1:18082/api/stock", timeout=15)
print(f"  stock {time.time()-t:.3f}s HTTP {r.status}")
PY
