#!/usr/bin/env bash
# MONITORING_UNAVAILABLE runner: code-induced telemetry dark → load → optional heal.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
chmod +x scripts/break_inventory_monitoring_dark.sh scripts/heal_inventory_monitoring_dark.sh scripts/load.sh 2>/dev/null || true

MINUTES=15
HEAL_AFTER=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --minutes) MINUTES="${2:?}"; shift 2 ;;
    --heal-after) HEAL_AFTER=1; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

./scripts/break_inventory_monitoring_dark.sh
STARTED_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "== Load ${MINUTES}m from $STARTED_UTC (HTTP should stay up; telemetry reduced/dark) =="
END=$((SECONDS + MINUTES * 60))
while (( SECONDS < END )); do
  ./scripts/load.sh 8 || true
done
if [[ "$HEAL_AFTER" == "1" ]]; then
  ./scripts/heal_inventory_monitoring_dark.sh
else
  echo "Leaving dark ON — heal: ./scripts/heal_inventory_monitoring_dark.sh"
fi
echo "Docs task: http://127.0.0.1:8765/dt-cat-monitoring-unavailable-lab.html"
echo "Agent prompt: docs/agent-tasks/dt-monitoring-unavailable.md"
