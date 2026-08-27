#!/usr/bin/env bash
# Code-only RESOURCE_CONTENTION: background CPU burn; HTTP path stays O(1).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/inventory/app.py"

for svc in inventory product frontend; do
  echo 0 > "$ROOT/faults/${svc}.latency"
  echo false > "$ROOT/faults/${svc}.fail"
done

python3 - <<'PY' "$APP"
from pathlib import Path
import sys, re
p = Path(sys.argv[1])
text = p.read_text()
# Keep scenario HEALTHY for this lab (burn is separate).
text, _ = re.subn(
    r'SCENARIO_MODE\s*=\s*"(HEALTHY|MONITORING_DARK|AVAILABILITY_DOWN)"',
    'SCENARIO_MODE = "HEALTHY"',
    text,
    count=1,
)
burn = '''# --- RESOURCE_BURN markers (break/heal scripts swap IDLE / BURN) ---
import threading as _burn_threading


def _lab_resource_burn() -> None:
    """Background CPU burn — off the /api/stock request path."""
    x = 0
    while True:
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        if x == -1:  # pragma: no cover
            break


_burn_threading.Thread(target=_lab_resource_burn, name="lab-resource-burn", daemon=True).start()
# --- end RESOURCE_BURN ---'''
pat = re.compile(r"# --- RESOURCE_BURN markers.*?\# --- end RESOURCE_BURN ---", re.S)
if not pat.search(text):
    raise SystemExit("RESOURCE_BURN markers missing")
if "lab-resource-burn" in text:
    print("already burning")
else:
    text = pat.sub(burn.strip(), text, count=1)
    print("RESOURCE_BURN → background CPU thread")
p.write_text(text)
PY

cd "$ROOT"
docker compose up -d --build inventory product frontend
echo "resource burn up — probe (expect fast HTTP 200):"
sleep 4
python3 - <<'PY'
import time, urllib.request
t = time.time()
r = urllib.request.urlopen("http://127.0.0.1:18082/api/stock", timeout=15)
print(f"  stock {time.time()-t:.3f}s HTTP {r.status} {r.read()[:80]!r}")
t = time.time()
r = urllib.request.urlopen("http://127.0.0.1:18080/api/checkout", timeout=15)
print(f"  checkout {time.time()-t:.3f}s HTTP {r.status}")
PY
