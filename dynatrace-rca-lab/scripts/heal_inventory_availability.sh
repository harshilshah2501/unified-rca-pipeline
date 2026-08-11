#!/usr/bin/env bash
# Bring inventory back after availability break.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
rm -f faults/inventory.availability_down
echo "== AVAILABILITY heal: docker compose start inventory =="
docker compose start inventory
# If never created, start via up
docker compose up -d --no-deps inventory
sleep 2
curl -s -o /tmp/av_heal.out -w "probe HTTP %{http_code}\n" http://localhost:19080/ || true
echo "Cleared faults/inventory.availability_down"
