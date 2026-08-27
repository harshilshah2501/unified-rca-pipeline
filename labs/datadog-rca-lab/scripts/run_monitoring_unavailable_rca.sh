#!/usr/bin/env bash
# MONITORING_UNAVAILABLE lab — code-only MONITORING_DARK (HTTP up, APM/metrics quiet).
# Usage: ./scripts/run_monitoring_unavailable_rca.sh [--minutes 10]
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

VER="mu-$(date -u +%Y%m%dT%H%M%SZ)"
sed -i -E "s/DD_VERSION: \"[^\"]+\"/DD_VERSION: \"${VER}\"/" docker-compose.yml

echo "== 0) Baseline heal =="
./scripts/heal_inventory_baseline.sh
./scripts/load.sh 5

echo "== 1) Break: MONITORING_DARK =="
./scripts/break_inventory_monitoring_dark.sh
STARTED_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "== 2) Load ${MINUTES}m while HTTP stays up (start $STARTED_UTC ver=$VER) =="
END=$((SECONDS + MINUTES * 60))
BATCH=0
while (( SECONDS < END )); do
  BATCH=$((BATCH + 1))
  echo "--- batch $BATCH t+${SECONDS}s ---"
  ./scripts/load.sh 15 || true
done
ENDED_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "== 3) Heal monitoring dark =="
./scripts/heal_inventory_monitoring_dark.sh
./scripts/load.sh 5

cat <<EOF
== Done MONITORING_UNAVAILABLE ==
start: $STARTED_UTC
end:   $ENDED_UTC
env:   rca-lab-e3
ver:   $VER
Leaf: inventory HTTP 200; APM patch_all skipped + DogStatsD no-op (code-only).
Observe in Datadog (no twin Davis category expected):
  • Inventory APM/metrics gap vs FE/product still writing
  • Checkout stays successful — not AVAILABILITY, not ERROR
  • Empty / partial Detect is a valid Observed outcome
EOF
