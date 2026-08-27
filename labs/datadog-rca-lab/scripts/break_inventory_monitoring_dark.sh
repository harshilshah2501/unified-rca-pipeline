#!/usr/bin/env bash
# Code-only MONITORING_UNAVAILABLE: SCENARIO_MODE=MONITORING_DARK
# (HTTP 200; skip patch_all + DogStatsD). Not container stop, not KeyError/slow.
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
idle = '''# --- RESOURCE_BURN markers (break/heal scripts swap IDLE / BURN) ---
# IDLE: no background CPU burn (RESOURCE_CONTENTION lab off).
# --- end RESOURCE_BURN ---'''
pat_burn = re.compile(r"# --- RESOURCE_BURN markers.*?\# --- end RESOURCE_BURN ---", re.S)
if pat_burn.search(text):
    text = pat_burn.sub(idle.strip(), text, count=1)
text, n = re.subn(
    r'SCENARIO_MODE\s*=\s*"(HEALTHY|MONITORING_DARK|AVAILABILITY_DOWN)"',
    'SCENARIO_MODE = "MONITORING_DARK"',
    text,
    count=1,
)
if not n:
    raise SystemExit("SCENARIO_MODE marker missing")
p.write_text(text)
print("SCENARIO_MODE → MONITORING_DARK")
PY

cd "$ROOT"
docker compose up -d --build inventory product frontend
echo "monitoring dark up — probe (expect HTTP 200; APM/metrics quiet for inventory):"
sleep 4
python3 - <<'PY'
import time, urllib.request, json
t = time.time()
r = urllib.request.urlopen("http://127.0.0.1:18082/health", timeout=15)
print(f"  health {time.time()-t:.3f}s {r.read().decode()}")
t = time.time()
r = urllib.request.urlopen("http://127.0.0.1:18082/api/stock", timeout=15)
print(f"  stock {time.time()-t:.3f}s HTTP {r.status}")
t = time.time()
r = urllib.request.urlopen("http://127.0.0.1:18080/api/checkout", timeout=15)
print(f"  checkout {time.time()-t:.3f}s HTTP {r.status}")
PY
