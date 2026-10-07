#!/usr/bin/env bash
# Code-only AVAILABILITY: SCENARIO_MODE=AVAILABILITY_DOWN → process exits ~2s after boot.
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
# Ensure burn idle so scenarios stay orthogonal.
idle = '''# --- RESOURCE_BURN markers (break/heal scripts swap IDLE / BURN) ---
# IDLE: no background CPU burn (RESOURCE_CONTENTION lab off).
# --- end RESOURCE_BURN ---'''
pat_burn = re.compile(r"# --- RESOURCE_BURN markers.*?\# --- end RESOURCE_BURN ---", re.S)
if pat_burn.search(text):
    text = pat_burn.sub(idle.strip(), text, count=1)
text, n = re.subn(
    r'SCENARIO_MODE\s*=\s*"(HEALTHY|MONITORING_DARK|AVAILABILITY_DOWN)"',
    'SCENARIO_MODE = "AVAILABILITY_DOWN"',
    text,
    count=1,
)
if not n:
    raise SystemExit("SCENARIO_MODE marker missing")
p.write_text(text)
print("SCENARIO_MODE → AVAILABILITY_DOWN")
PY

cd "$ROOT"
docker compose up -d --build inventory product frontend
echo "availability break applied — inventory should die ~2s after boot:"
sleep 5
python3 - <<'PY'
import urllib.request, urllib.error
for url, name in [
    ("http://127.0.0.1:18082/api/stock", "stock"),
    ("http://127.0.0.1:18080/api/checkout", "checkout"),
]:
    try:
        r = urllib.request.urlopen(url, timeout=8)
        print(f"  {name} HTTP {r.status} (unexpected up)")
    except Exception as e:
        print(f"  {name} FAIL (expected): {type(e).__name__}: {e}")
PY
docker compose ps inventory || true
