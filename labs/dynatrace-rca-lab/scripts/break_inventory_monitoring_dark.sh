#!/usr/bin/env bash
# Visibility dark via Python code change only (no container stop, no settings toggle).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/inventory/app.py"
cd "$ROOT"
mkdir -p faults
echo "on" > faults/inventory.monitoring_dark

python3 - <<'PY' "$APP"
from pathlib import Path
import re
import sys

p = Path(sys.argv[1])
text = p.read_text()
pat = re.compile(r'SCENARIO_MODE\s*=\s*"(HEALTHY|MONITORING_DARK|AVAILABILITY_DOWN)"')
if not pat.search(text):
    raise SystemExit("SCENARIO_MODE marker missing in inventory/app.py")
text2 = pat.sub('SCENARIO_MODE = "MONITORING_DARK"', text, count=1)
p.write_text(text2)
print("patched SCENARIO_MODE -> MONITORING_DARK")
PY

echo "== MONITORING_UNAVAILABLE break: rebuild inventory with SCENARIO_MODE=MONITORING_DARK =="
docker compose up -d --build inventory
sleep 3
echo "probe FE (should stay HTTP 200):"
curl -s -o /tmp/mu_probe.out -w "HTTP %{http_code}\n" http://localhost:19080/ || true
echo "Heal: ./scripts/heal_inventory_monitoring_dark.sh"
