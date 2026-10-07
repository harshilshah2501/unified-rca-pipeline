#!/usr/bin/env bash
# Drive checkout traffic for APM / Service Map (Dynatrace-lab parity).
set -euo pipefail
URL="${CHECKOUT_URL:-http://127.0.0.1:18080/api/checkout}"
N="${1:-30}"
echo "Hitting $URL × $N"
for i in $(seq 1 "$N"); do
  code=$(curl -s -o /tmp/dd-checkout.json -w "%{http_code}" "$URL" || echo 000)
  echo "[$i] HTTP $code $(head -c 120 /tmp/dd-checkout.json 2>/dev/null || true)"
  sleep 0.4
done
