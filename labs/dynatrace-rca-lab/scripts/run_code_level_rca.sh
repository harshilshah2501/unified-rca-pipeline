#!/usr/bin/env bash
# End-to-end code-level RCA demo:
#   1) optional CUSTOM_DEPLOYMENT on inventory
#   2) turn inventory.fail on (named exception + stack attrs on spans)
#   3) sustain load through FE→product→inventory
#   4) print what to look for on the Dynatrace Problem
#
# Usage (from dynatrace-rca-lab/):
#   ./scripts/run_code_level_rca.sh
#   ./scripts/run_code_level_rca.sh --no-deploy
#   ./scripts/run_code_level_rca.sh --minutes 12
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
chmod +x scripts/load.sh scripts/fault.sh scripts/ingest_change_event.sh 2>/dev/null || true

WITH_DEPLOY=1
MINUTES=12
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-deploy) WITH_DEPLOY=0; shift ;;
    --minutes) MINUTES="${2:?}"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

echo "== 0) Clear prior fail flag =="
./scripts/fault.sh inventory fail false || true

if [[ "$WITH_DEPLOY" == "1" ]]; then
  echo "== 1) Ingest CUSTOM_DEPLOYMENT (root-cause relevant) =="
  ./scripts/ingest_change_event.sh deployment || {
    echo "WARN: deploy ingest failed — continuing with code exception only." >&2
  }
  echo "Sleep 45s so the change sits just before the fault window…"
  sleep 45
else
  echo "== 1) Skipping deploy event (--no-deploy) =="
fi

echo "== 2) Inject named code fault on inventory =="
./scripts/fault.sh inventory fail true

echo "== 3) Probe (expect upstream failures; inventory returns error_code JSON) =="
curl -sS -w "\nHTTP %{http_code}\n" http://localhost:19080/ | head -c 500 || true
echo

echo "== 4) Sustain load for ${MINUTES} minutes =="
END=$((SECONDS + MINUTES * 60))
BATCH=0
while (( SECONDS < END )); do
  BATCH=$((BATCH + 1))
  echo "--- load batch $BATCH (t+$((SECONDS))s) ---"
  ./scripts/load.sh 25 || true
done

echo
echo "== 5) What to verify in Dynatrace =="
cat <<'EOF'
Wait until a Problem opens (prior lab ~10 min sustain).

On the Problem / inventory service, look for:
  • rootCauseEntity ≈ inventory (entity-level — same as before)
  • Trace / PurePath on inventory with:
      exception.type  = InventoryStockLookupError
      message / attrs contain WAREHOUSE_SKU_INDEX_CORRUPT
      code.function   = lookup_stock_in_warehouse
      code.filepath   = inventory/app.py
  • Logs (if log ingest on): code_pinpoint … lookup_stock_in_warehouse
  • Events: CUSTOM_DEPLOYMENT "Lab deploy inventory 1.1.0-codepin…"
    (if deploy ingest succeeded)

Grail / trace search:
  InventoryStockLookupError
  WAREHOUSE_SKU_INDEX_CORRUPT
  lookup_stock_in_warehouse

Clear when done:
  ./scripts/fault.sh inventory fail false
EOF
