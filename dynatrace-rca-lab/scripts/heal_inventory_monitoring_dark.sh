#!/usr/bin/env bash
# Restore inventory telemetry (clear monitoring-dark marker; recreate with default OTEL env).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
rm -f faults/inventory.monitoring_dark
echo "== MONITORING_UNAVAILABLE heal: recreate inventory with compose defaults =="
docker compose up -d --force-recreate --no-deps inventory
sleep 2
curl -s -o /tmp/mu_heal.out -w "probe HTTP %{http_code}\n" http://localhost:19080/ || true
echo "Cleared faults/inventory.monitoring_dark"
