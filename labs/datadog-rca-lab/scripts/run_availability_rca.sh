#!/usr/bin/env bash
# AVAILABILITY lab — code-only process exit after boot.
# Usage: ./scripts/run_availability_rca.sh [--minutes 10]
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

VER="avail-$(date -u +%Y%m%dT%H%M%SZ)"
sed -i -E "s/DD_VERSION: \"[^\"]+\"/DD_VERSION: \"${VER}\"/" docker-compose.yml

echo "== 0) Baseline heal =="
./scripts/heal_inventory_baseline.sh
./scripts/load.sh 5

echo "== 1) Break: AVAILABILITY_DOWN =="
./scripts/break_inventory_availability.sh
STARTED_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "== 2) Drive load while inventory down (${MINUTES}m) start=$STARTED_UTC ver=$VER =="
END=$((SECONDS + MINUTES * 60))
BATCH=0
while (( SECONDS < END )); do
  BATCH=$((BATCH + 1))
  echo "--- batch $BATCH t+${SECONDS}s ---"
  # inventory may be dead — load should still run against checkout
  ./scripts/load.sh 10 || true
  # keep trying to observe inventory state
  docker compose ps inventory || true
done
ENDED_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "== 3) Heal availability =="
./scripts/heal_inventory_availability.sh
./scripts/load.sh 5

cat <<EOF
== Done AVAILABILITY ==
start: $STARTED_UTC
end:   $ENDED_UTC
env:   rca-lab-e3
ver:   $VER
Leaf: inventory process exits; callers fail (not KeyError teaching chalk).
Observe in Datadog (native doors, not Davis AVAILABILITY stamp):
  • Process/container check if scoped; else APM/caller failures on FE/product
  • Host CPU pack is not the availability signal
EOF
