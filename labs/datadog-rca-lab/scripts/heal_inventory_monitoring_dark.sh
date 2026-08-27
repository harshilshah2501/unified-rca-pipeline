#!/usr/bin/env bash
# Heal MONITORING_DARK → HEALTHY.
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
echo "monitoring dark healed — probe:"
sleep 4
python3 - <<'PY'
import time, urllib.request
t = time.time()
r = urllib.request.urlopen("http://127.0.0.1:18082/api/stock", timeout=15)
print(f"  stock {time.time()-t:.3f}s HTTP {r.status}")
t = time.time()
r = urllib.request.urlopen("http://127.0.0.1:18080/api/checkout", timeout=15)
print(f"  checkout {time.time()-t:.3f}s HTTP {r.status}")
PY
