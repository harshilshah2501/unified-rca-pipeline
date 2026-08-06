#!/usr/bin/env bash
# End-to-end code-level SLOWDOWN lab (NOT fault-flag sleep):
#   1) ensure healthy O(1) lookup
#   2) patch inventory to ledger scan + checksum (real CPU cost, HTTP 200)
#   3) sustain load FE→product→inventory
#   4) print what to look for (response-time / SLOWDOWN Problem)
#
# Usage (from dynatrace-rca-lab/):
#   ./scripts/run_slowdown_rca.sh
#   ./scripts/run_slowdown_rca.sh --minutes 15
#   ./scripts/run_slowdown_rca.sh --heal-after
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
chmod +x scripts/load.sh \
  scripts/break_inventory_slow_code.sh scripts/heal_inventory_slow_code.sh 2>/dev/null || true

MINUTES=15
HEAL_AFTER=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --minutes) MINUTES="${2:?}"; shift 2 ;;
    --heal-after) HEAL_AFTER=1; shift ;;
    --latency)
      echo "ERROR: --latency removed. This lab uses code-level slowdown only." >&2
      echo "  Use: ./scripts/break_inventory_slow_code.sh" >&2
      exit 2
      ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

echo "== 0) Start from healthy O(1) lookup =="
./scripts/heal_inventory_slow_code.sh

echo "== 1) Inject REAL code-level SLOWDOWN (ledger scan + checksum) =="
./scripts/break_inventory_slow_code.sh

STARTED_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "== 2) Sustain load for ${MINUTES} minutes (started $STARTED_UTC) =="
END=$((SECONDS + MINUTES * 60))
BATCH=0
while (( SECONDS < END )); do
  BATCH=$((BATCH + 1))
  echo "--- load batch $BATCH (t+$((SECONDS))s) ---"
  ./scripts/load.sh 12 || true
done

if [[ "$HEAL_AFTER" == "1" ]]; then
  echo "== 3) Heal code =="
  ./scripts/heal_inventory_slow_code.sh
else
  echo "== 3) Leaving SLOW code ON — heal with: ./scripts/heal_inventory_slow_code.sh =="
fi

echo
echo "== 4) What to verify in Dynatrace =="
cat <<EOF
Fault window started: $STARTED_UTC
Leaf: lookup_stock_in_warehouse scans WAREHOUSE_LEDGER + _debug_row_checksum (HTTP 200).

Expect (when Davis opens a Problem — often ~5–15 min of sustained RT):
  • Event category / type around RESPONSE_TIME / SLOWDOWN
  • NOT primarily SERVICE_ERROR_RATE_INCREASED
  • Traces: long inventory span in lookup_stock_in_warehouse / _debug_row_checksum
  • rootCauseEntity may be inventory — or null if Event starts align

Docs: http://127.0.0.1:8765/dt-lab-timeline-slowdown.html
EOF
