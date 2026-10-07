#!/usr/bin/env bash
# Parallel load for SLOWDOWN lab — aim for ≥10 req/min so Dynatrace
# over-alerting protection (default 10 rpm) does not suppress Events.
#
# Usage:
#   ./scripts/load_parallel.sh            # 3 workers × endless until Ctrl-C
#   WORKERS=4 DURATION_MIN=20 ./scripts/load_parallel.sh
set -euo pipefail
URL="${CHECKOUT_URL:-http://127.0.0.1:19080/}"
WORKERS="${WORKERS:-3}"
DURATION_MIN="${DURATION_MIN:-20}"
END=$((SECONDS + DURATION_MIN * 60))
echo "parallel load URL=$URL workers=$WORKERS duration=${DURATION_MIN}m (until $(date -u -d @$(($(date +%s)+DURATION_MIN*60)) +%H:%M:%SZ 2>/dev/null || date -u))"

worker() {
  local id=$1 n=0
  while (( SECONDS < END )); do
    n=$((n+1))
    code=$(curl -s -o /tmp/dt-par-${id}.json -w "%{http_code}" --max-time 40 "$URL" || echo 000)
    echo "[w$id #$n t+${SECONDS}s] HTTP $code"
  done
}

for w in $(seq 1 "$WORKERS"); do
  worker "$w" &
done
wait
echo "parallel load done"
