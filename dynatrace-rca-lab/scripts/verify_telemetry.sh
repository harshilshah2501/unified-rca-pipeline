#!/usr/bin/env bash
# Verify why Dynatrace may/may not see the lab.
set -euo pipefail

OA=/opt/dynatrace/oneagent/agent/tools/oneagentctl
CONF=/var/lib/dynatrace/oneagent/agent/config/ruxitagentproc.conf

echo "== OneAgent =="
systemctl is-active oneagent || true
"$OA" --get-monitoring-mode || true
"$OA" --get-auto-injection-enabled || true
"$OA" --get-tenant || true

echo
echo "== Python injection flag (server-controlled) =="
rg -n '^(python|pythonInjection) ' "$CONF" || true
NEWLOG=$(ls -t /var/log/dynatrace/oneagent/os/ruxitagent_host_*.log 2>/dev/null | head -1 || true)
if [[ -n "${NEWLOG:-}" ]]; then
  rg -i 'pythonInjection' "$NEWLOG" | tail -3 || true
fi

echo
echo "== Lab containers =="
docker compose -f "$(dirname "$0")/../docker-compose.yml" ps || true

echo
echo "== Recent Docker injections =="
HELPER=$(ls -t /var/log/dynatrace/oneagent/process/oneagenthelper_*.log 2>/dev/null | head -1 || true)
if [[ -n "${HELPER:-}" ]]; then
  rg -n 'dynatrace-rca-lab' "$HELPER" | tail -10 || true
fi

echo
echo "== Smoke test =="
curl -sS -o /tmp/rca-lab-smoke.json -w "HTTP %{http_code}\n" http://localhost:18080 || true
cat /tmp/rca-lab-smoke.json 2>/dev/null; echo

echo
echo "If pythonInjection=off → no Service flow from OneAgent."
echo "Fix: enable Python under Dynatrace Settings → Preferences → OneAgent features"
echo "  OR set DT_API_TOKEN + OTEL_SDK_DISABLED=false in .env (OTLP path)."
