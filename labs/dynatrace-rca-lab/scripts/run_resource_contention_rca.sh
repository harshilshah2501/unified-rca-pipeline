#!/usr/bin/env bash
# RESOURCE_CONTENTION agent task runner: CPU burn → load → optional heal.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
chmod +x scripts/break_inventory_resource_burn.sh scripts/heal_inventory_resource_burn.sh scripts/load.sh 2>/dev/null || true

MINUTES=15
HEAL_AFTER=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --minutes) MINUTES="${2:?}"; shift 2 ;;
    --heal-after) HEAL_AFTER=1; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

./scripts/break_inventory_resource_burn.sh
STARTED_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "== Load ${MINUTES}m from $STARTED_UTC (HTTP fast; CPU burn background) =="
END=$((SECONDS + MINUTES * 60))
while (( SECONDS < END )); do
  ./scripts/load.sh 10 || true
done
if [[ "$HEAL_AFTER" == "1" ]]; then
  ./scripts/heal_inventory_resource_burn.sh
else
  echo "Leaving burn ON — heal: ./scripts/heal_inventory_resource_burn.sh"
fi
echo "Docs task: http://127.0.0.1:8765/dt-cat-resource-contention-lab.html"
echo "Agent prompt: docs/agent-tasks/dt-resource-contention.md"
