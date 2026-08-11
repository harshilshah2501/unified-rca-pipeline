#!/usr/bin/env bash
# Visibility dark: inventory keeps serving HTTP; Dynatrace ingest/OTLP is disabled.
# Usage: ./scripts/break_inventory_monitoring_dark.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p faults
echo "on" > faults/inventory.monitoring_dark
echo "== MONITORING_UNAVAILABLE break: recreate inventory with OTEL_SDK_DISABLED=true =="
OTEL_SDK_DISABLED=true docker compose up -d --force-recreate --no-deps inventory
sleep 2
echo "probe FE (should still work if product→inventory HTTP is up):"
curl -s -o /tmp/mu_probe.out -w "HTTP %{http_code}\n" http://localhost:19080/ || true
head -c 200 /tmp/mu_probe.out 2>/dev/null; echo
echo "Marker: faults/inventory.monitoring_dark=on"
echo "If host OneAgent still instruments this container, disable deep monitoring for inventory too:"
echo "  Settings API builtin:process-group.monitoring.state → MONITORING_OFF on inventory PG, then recreate."
echo "Native severity MONITORING_UNAVAILABLE is platform-wide (majority agents); lab may surface via CUSTOM_ALERT."
echo "Heal: ./scripts/heal_inventory_monitoring_dark.sh"
