#!/usr/bin/env bash
# Drive Dynatrace lab traffic (host port 19080 — Datadog uses 18080).
set -euo pipefail
URL="${CHECKOUT_URL:-http://127.0.0.1:19080/}"
N="${1:-30}"
echo "Hitting $URL × $N"
ok=0
for i in $(seq 1 "$N"); do
  code=$(curl -s -o /tmp/dt-checkout.json -w "%{http_code}" "$URL" || echo 000)
  echo "[$i] HTTP $code $(head -c 100 /tmp/dt-checkout.json 2>/dev/null || true)"
  [[ "$code" == "200" ]] && ok=$((ok+1))
  sleep 0.4
done
echo "ok=$ok/$N"
