#!/usr/bin/env bash
# End-to-end code-level SLOWDOWN lab (NOT fault-flag sleep):
#   1) ensure healthy O(1) lookup
#   2) patch inventory to ledger scan + checksum (real CPU cost, HTTP 200)
#   3) sustain load FE→product→inventory
#   4) heal
#
# Usage (from datadog-rca-lab/):
#   ./scripts/run_slowdown_rca.sh
#   ./scripts/run_slowdown_rca.sh --minutes 12
#   ./scripts/run_slowdown_rca.sh --heal-after   (default: heal after load)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
chmod +x scripts/load.sh \
  scripts/break_inventory_slow_code.sh scripts/heal_inventory_slow_code.sh 2>/dev/null || true

MINUTES=12
HEAL_AFTER=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --minutes) MINUTES="${2:?}"; shift 2 ;;
    --heal-after) HEAL_AFTER=1; shift ;;
    --no-heal) HEAL_AFTER=0; shift ;;
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
  # Fewer reqs per batch — each checkout ~9–11s wall
  ./scripts/load.sh 4 || true
done

if [[ "$HEAL_AFTER" == "1" ]]; then
  echo "== 3) Heal code =="
  ./scripts/heal_inventory_slow_code.sh
else
  echo "== 3) Leaving SLOW code ON — heal with: ./scripts/heal_inventory_slow_code.sh =="
fi

echo
echo "== 4) What to verify in Datadog =="
cat <<EOF
Fault window started: $STARTED_UTC
Leaf: lookup_stock_in_warehouse scans WAREHOUSE_LEDGER + _debug_row_checksum (HTTP 200).

Expect:
  • Spans status:ok with high @duration (~9s) on inventory /api/stock
  • Checkout still 200 (pure SLOWDOWN — not ERROR)
  • Latency metrics / p95 rise; Watchdog / Incidents may stay empty
  • Localize by longest leaf span, not error status

Docs: http://127.0.0.1:8765/dd-lab-timeline-slowdown.html
EOF
