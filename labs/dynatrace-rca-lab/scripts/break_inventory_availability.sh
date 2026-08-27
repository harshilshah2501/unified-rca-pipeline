#!/usr/bin/env bash
# Hard outage via Python code change only (no docker stop command).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/inventory/app.py"
cd "$ROOT"
mkdir -p faults
echo "on" > faults/inventory.availability_down

python3 - <<'PY' "$APP"
from pathlib import Path
import re
import sys

p = Path(sys.argv[1])
text = p.read_text()
pat = re.compile(r'SCENARIO_MODE\s*=\s*"(HEALTHY|MONITORING_DARK|AVAILABILITY_DOWN)"')
if not pat.search(text):
    raise SystemExit("SCENARIO_MODE marker missing in inventory/app.py")
text2 = pat.sub('SCENARIO_MODE = "AVAILABILITY_DOWN"', text, count=1)
p.write_text(text2)
print("patched SCENARIO_MODE -> AVAILABILITY_DOWN")
PY

echo "== AVAILABILITY break: rebuild inventory in AVAILABILITY_DOWN mode =="
docker compose up -d --build inventory
sleep 4
echo "probe FE (expect failure / incomplete):"
curl -s -o /tmp/av_probe.out -w "HTTP %{http_code}\n" --max-time 5 http://localhost:19080/ || echo "probe failed (expected while inventory down)"
echo "Heal: ./scripts/heal_inventory_availability.sh"
