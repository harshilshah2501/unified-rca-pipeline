#!/usr/bin/env bash
# Heal AVAILABILITY: SCENARIO_MODE → HEALTHY and rebuild.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/inventory/app.py"

python3 - <<'PY' "$APP"
from pathlib import Path
import sys, re
p = Path(sys.argv[1])
text = p.read_text()
text, n = re.subn(
    r'SCENARIO_MODE\s*=\s*"(HEALTHY|MONITORING_DARK|AVAILABILITY_DOWN)"',
    'SCENARIO_MODE = "HEALTHY"',
    text,
    count=1,
)
if not n:
    raise SystemExit("SCENARIO_MODE marker missing")
p.write_text(text)
print("SCENARIO_MODE → HEALTHY")
PY

cd "$ROOT"
docker compose up -d --build inventory product frontend
echo "availability healed — probe:"
sleep 4
python3 - <<'PY'
import time, urllib.request
for url, name in [
    ("http://127.0.0.1:18082/api/stock", "stock"),
    ("http://127.0.0.1:18080/api/checkout", "checkout"),
]:
    t = time.time()
    r = urllib.request.urlopen(url, timeout=15)
    print(f"  {name} {time.time()-t:.3f}s HTTP {r.status}")
PY
