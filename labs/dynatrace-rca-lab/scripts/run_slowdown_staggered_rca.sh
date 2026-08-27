#!/usr/bin/env bash
# Staggered SLOWDOWN — aim for inventory Event BEFORE product/FE (like P-260814).
#
# Why: FE→product→inventory on every checkout makes all three RT series jump on the
# same requests → same Detect bucket → rootCauseRelevant=false / rootCauseEntity=null.
# Hitting inventory alone first lets Davis open SERVICE_SLOWDOWN on INV earlier;
# then FE load cascades product/FE Events later → temporal ranking for entity RCA.
#
# Usage (from dynatrace-rca-lab/):
#   ./scripts/run_slowdown_staggered_rca.sh
#   ./scripts/run_slowdown_staggered_rca.sh --leaf-minutes 8 --cascade-minutes 12
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
chmod +x scripts/load.sh scripts/break_inventory_slow_code.sh scripts/heal_inventory_slow_code.sh 2>/dev/null || true

LEAF_MIN=8
CASCADE_MIN=12
SKIP_BREAK=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --leaf-minutes) LEAF_MIN="${2:?}"; shift 2 ;;
    --cascade-minutes) CASCADE_MIN="${2:?}"; shift 2 ;;
    --skip-break) SKIP_BREAK=1; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

pkill -f 'scripts/load.sh|load_parallel|slowdown-serial|inventory-leaf-load' 2>/dev/null || true
sleep 1

if [[ "$SKIP_BREAK" != "1" ]]; then
  echo "== 0) Ensure slow code on inventory =="
  # if already slow, break script is no-op / rebuild
  if ! grep -q '_debug_row_checksum' inventory/app.py; then
    ./scripts/break_inventory_slow_code.sh
  else
    echo "slow code already on disk — rebuilding inventory"
    docker compose up -d --build inventory
    sleep 3
  fi
fi

STARTED=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "== 1) LEAF-ONLY load on inventory (${LEAF_MIN} min) — no FE traffic =="
echo "    started $STARTED"
END_LEAF=$((SECONDS + LEAF_MIN * 60))
N=0
while (( SECONDS < END_LEAF )); do
  N=$((N + 1))
  # call inventory inside compose network (not exposed on host)
  OUT=$(docker compose exec -T product python3 - <<'PY' 2>/dev/null || true
import time, urllib.request
t=time.time()
try:
    r=urllib.request.urlopen("http://inventory:8082/inventory", timeout=60)
    print(f"HTTP {r.status} {time.time()-t:.2f}s")
except Exception as e:
    print(f"FAIL {time.time()-t:.2f}s {e}")
PY
)
  echo "[leaf #$N t+${SECONDS}s] $OUT"
  # small gap so we stay ≥1 rpm without pile-up
  sleep 2
done

echo "== 2) CASCADE load via frontend (${CASCADE_MIN} min) =="
END_C=$((SECONDS + CASCADE_MIN * 60))
B=0
while (( SECONDS < END_C )); do
  B=$((B + 1))
  echo "--- cascade batch $B (t+${SECONDS}s) ---"
  ./scripts/load.sh 4 || true
done

echo
echo "== 3) What to verify =="
cat <<EOF
Leaf-only window started: $STARTED (${LEAF_MIN} min inventory-only)
Then cascade: FE→product→inventory (${CASCADE_MIN} min)

Expect (vs P-260820 same-bucket null RC):
  • inventory SERVICE_SLOWDOWN Event start earlier than product/FE
  • inventory rootCauseRelevant=true (hopefully)
  • rootCauseEntity=inventory (like P-260814 pattern)

API:
  curl -sS -G "\$DT_ENV_URL/api/v2/problems" --data-urlencode 'from=now-2h' \\
    -H "Authorization: Api-Token \$DT_API_TOKEN"
EOF
