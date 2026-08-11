#!/usr/bin/env bash
# Hard outage: stop inventory container (process unavailable).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p faults
echo "on" > faults/inventory.availability_down
echo "== AVAILABILITY break: docker compose stop inventory =="
docker compose stop inventory
sleep 1
echo "probe FE (expect failure / incomplete):"
curl -s -o /tmp/av_probe.out -w "HTTP %{http_code}\n" --max-time 5 http://localhost:19080/ || echo "probe failed (expected while inventory down)"
echo "Heal: ./scripts/heal_inventory_availability.sh"
