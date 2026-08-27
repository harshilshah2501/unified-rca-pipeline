#!/usr/bin/env bash
# Restore HEALTHY mode after monitoring-dark code patch.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/inventory/app.py"
cd "$ROOT"
rm -f faults/inventory.monitoring_dark

python3 - <<'PY' "$APP"
from pathlib import Path
import re
import sys

p = Path(sys.argv[1])
text = p.read_text()
pat = re.compile(r'SCENARIO_MODE\s*=\s*"(HEALTHY|MONITORING_DARK|AVAILABILITY_DOWN)"')
if not pat.search(text):
    raise SystemExit("SCENARIO_MODE marker missing in inventory/app.py")
text2 = pat.sub('SCENARIO_MODE = "HEALTHY"', text, count=1)
p.write_text(text2)
print("restored SCENARIO_MODE -> HEALTHY")
PY

echo "== MONITORING_UNAVAILABLE heal: rebuild inventory =="
docker compose up -d --build inventory
sleep 3
curl -s -o /tmp/mu_heal.out -w "probe HTTP %{http_code}\n" http://localhost:19080/ || true
echo "Cleared faults/inventory.monitoring_dark"
