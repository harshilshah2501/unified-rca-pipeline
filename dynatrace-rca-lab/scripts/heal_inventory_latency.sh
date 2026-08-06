#!/usr/bin/env bash
# Clear inventory latency (and sibling latency/fail flags) — restore fast path.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for svc in inventory product frontend; do
  echo 0 > "$ROOT/faults/${svc}.latency"
  echo false > "$ROOT/faults/${svc}.fail"
done
echo "healed — all latency=0, fail=false"
python3 - <<'PY'
import time, urllib.request
t = time.time()
r = urllib.request.urlopen("http://127.0.0.1:19080/", timeout=10)
print(f"probe {time.time()-t:.3f}s HTTP {r.status}")
PY
