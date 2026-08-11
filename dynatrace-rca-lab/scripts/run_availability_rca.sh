#!/usr/bin/env bash
# AVAILABILITY agent task runner: stop inventory → load → optional start.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
chmod +x scripts/break_inventory_availability.sh scripts/heal_inventory_availability.sh scripts/load.sh 2>/dev/null || true

MINUTES=10
HEAL_AFTER=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --minutes) MINUTES="${2:?}"; shift 2 ;;
    --heal-after) HEAL_AFTER=1; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

./scripts/break_inventory_availability.sh
STARTED_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "== Load ${MINUTES}m from $STARTED_UTC (expect caller failures) =="
END=$((SECONDS + MINUTES * 60))
while (( SECONDS < END )); do
  ./scripts/load.sh 6 || true
  sleep 2
done
if [[ "$HEAL_AFTER" == "1" ]]; then
  ./scripts/heal_inventory_availability.sh
else
  echo "Leaving inventory STOPPED — heal: ./scripts/heal_inventory_availability.sh"
fi
echo "Docs task: http://127.0.0.1:8765/dt-cat-availability-lab.html"
echo "Agent prompt: docs/agent-tasks/dt-availability.md"
