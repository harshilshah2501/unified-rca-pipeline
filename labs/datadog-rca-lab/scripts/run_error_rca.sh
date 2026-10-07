#!/usr/bin/env bash
# End-to-end ERROR lab — code-level KeyError (missing WIDGET-1 in catalog):
#   1) heal / healthy baseline
#   2) break: drop WIDGET-1 from WAREHOUSE_SKU_INDEX
#   3) sustain checkout load
#   4) heal
#
# Usage (from datadog-rca-lab/):
#   ./scripts/run_error_rca.sh
#   ./scripts/run_error_rca.sh --minutes 6
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
chmod +x \
  scripts/load.sh \
  scripts/break_inventory_code.sh scripts/heal_inventory_code.sh \
  2>/dev/null || true

MINUTES=6
while [[ $# -gt 0 ]]; do
  case "$1" in
    --minutes) MINUTES="${2:?}"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

ENV_TAG=$(grep -m1 'DD_ENV:' docker-compose.yml | awk '{print $2}' | tr -d '"' || echo rca-lab-e3)
VER_TAG=$(grep -m1 'DD_VERSION:' docker-compose.yml | awk '{print $2}' | tr -d '"' || echo unknown)

echo "== 0) Heal catalog + healthy baseline (env=${ENV_TAG}) =="
./scripts/heal_inventory_code.sh
./scripts/load.sh 10

echo "== 1) Introduce code-level KeyError (WIDGET-1 missing from index) =="
./scripts/break_inventory_code.sh
STARTED_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "== 2) Sustain load for ${MINUTES} minutes (started $STARTED_UTC) =="
END=$((SECONDS + MINUTES * 60))
BATCH=0
while (( SECONDS < END )); do
  BATCH=$((BATCH + 1))
  echo "--- load batch $BATCH (t+$((SECONDS))s) ---"
  ./scripts/load.sh 20 || true
done

echo "== 3) Heal catalog =="
./scripts/heal_inventory_code.sh
./scripts/load.sh 5

echo
echo "== 4) What to verify in Datadog =="
cat <<EOF
Window started: $STARTED_UTC
Leaf: inventory GET /api/stock → HTTP 500 KeyError; checkout → 502.
Filter ONLY env:${ENV_TAG} version:${VER_TAG}
(retire teaching filters on env:rca-lab and env:rca-lab-e2)

Expect:
  • APM status:error — deepest KeyError / http.status_code:500 on inventory
  • Metrics: rca.inventory.stock.errors · trace.flask.request.errors
  • Logs: @event:inventory.stock.error @error_type:KeyError (no fault.* fields)
  • Door A Flask High Error Rate may stay OK under min(last_15m)
  • Door B Watchdog error_rate stories / bridge — evaluate after window
  • Bits: http://127.0.0.1:8765/dd-bits-error-review.html?cat=error

Docs: http://127.0.0.1:8765/dd-error-mtl-dissection.html?cat=error
EOF
