#!/usr/bin/env bash
# RESOURCE_CONTENTION lab — background CPU burn (HTTP stays fast).
# Usage: ./scripts/run_resource_contention_rca.sh [--minutes 10]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
chmod +x scripts/*.sh 2>/dev/null || true

MINUTES=10
while [[ $# -gt 0 ]]; do
  case "$1" in
    --minutes) MINUTES="${2:?}"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

VER="rc-$(date -u +%Y%m%dT%H%M%SZ)"
# Stamp version for this window only (all three services).
sed -i -E "s/DD_VERSION: \"[^\"]+\"/DD_VERSION: \"${VER}\"/" docker-compose.yml

echo "== 0) Baseline heal =="
./scripts/heal_inventory_baseline.sh
./scripts/load.sh 5

echo "== 1) Break: RESOURCE_BURN =="
./scripts/break_inventory_resource_burn.sh
STARTED_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "== 2) Load ${MINUTES}m (start $STARTED_UTC version=$VER) =="
END=$((SECONDS + MINUTES * 60))
BATCH=0
while (( SECONDS < END )); do
  BATCH=$((BATCH + 1))
  echo "--- batch $BATCH t+${SECONDS}s ---"
  ./scripts/load.sh 15 || true
done
ENDED_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "== 3) Heal burn =="
./scripts/heal_inventory_resource_burn.sh
./scripts/load.sh 5

cat <<EOF
== Done RESOURCE_CONTENTION ==
start: $STARTED_UTC
end:   $ENDED_UTC
env:   rca-lab-e3
ver:   $VER
Leaf: background CPU burn; /api/stock + checkout stay HTTP 200 fast.
Observe in Datadog (do not force Davis labels):
  • Host pack CPU / load / Watchdog infrastructure — may or may not Alert
  • APM error Door should stay quiet; latency Door absent unless authored
  • Negative Detect is a valid Observed teaching outcome
EOF
