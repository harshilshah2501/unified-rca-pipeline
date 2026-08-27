#!/usr/bin/env bash
# Set environment-wide FIXED response-time thresholds for SLOWDOWN lab.
# Requires API token scope: settings.write (+ settings.read)
#
# Thresholds (5-minute observation):
#   median (all)  > 2000 ms
#   slowest 10%   > 3000 ms
#   min load      ≥ 1 req/min   (was 10 — blocked our ~9s sequential load)
#   abnormal for  ≥ 1 minute
#   sensitivity   high
#
# Usage (from dynatrace-rca-lab/ with .env):
#   ./scripts/set_fixed_response_time_threshold.sh
#   ./scripts/set_fixed_response_time_threshold.sh --restore   # undo to prior auto backup
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
set -a; source .env; set +a

RESTORE=0
[[ "${1:-}" == "--restore" ]] && RESTORE=1

SCHEMA='builtin:anomaly-detection.services'
BACKUP="$ROOT/scripts/.cache/anomaly-detection.services.environment.backup.json"
mkdir -p "$ROOT/scripts/.cache"

# find environment-scoped object
OBJ_JSON=$(curl -sS -G "${DT_ENV_URL}/api/v2/settings/objects" \
  --data-urlencode "schemaIds=${SCHEMA}" \
  --data-urlencode 'scopes=environment' \
  --data-urlencode 'fields=objectId,value,scope,schemaVersion' \
  -H "Authorization: Api-Token ${DT_API_TOKEN}")

OBJ_ID=$(python3 - <<'PY' "$OBJ_JSON"
import json,sys
d=json.loads(sys.argv[1])
items=d.get('items') or []
if not items:
    raise SystemExit('no environment settings object for anomaly-detection.services')
print(items[0]['objectId'])
open('/tmp/dt_ad_env_current.json','w').write(json.dumps(items[0], indent=2))
PY
)

if [[ ! -f "$BACKUP" ]]; then
  cp /tmp/dt_ad_env_current.json "$BACKUP"
  echo "wrote backup $BACKUP"
fi

if [[ "$RESTORE" == "1" ]]; then
  VAL=$(python3 -c 'import json; print(json.dumps({"value": json.load(open("'"$BACKUP"'"))["value"]}))')
  curl -sS -X PUT "${DT_ENV_URL}/api/v2/settings/objects/${OBJ_ID}" \
    -H "Authorization: Api-Token ${DT_API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$VAL" -w "\nrestore:%{http_code}\n"
  exit 0
fi

PAYLOAD=$(python3 - <<'PY'
import json
cur = json.load(open("/tmp/dt_ad_env_current.json"))["value"]
# keep failureRate / load* as-is; only swap responseTime → fixed
cur["responseTime"] = {
  "enabled": True,
  "detectionMode": "fixed",
  "fixedDetection": {
    "responseTimeAll": {"degradationMilliseconds": 2000.0},
    "responseTimeSlowest": {"slowestDegradationMilliseconds": 3000.0},
    "overAlertingProtection": {
      "requestsPerMinute": 1.0,
      "minutesAbnormalState": 1,
    },
    "sensitivity": "high",
  },
}
print(json.dumps({"value": cur}))
PY
)

RESP=$(curl -sS -X PUT "${DT_ENV_URL}/api/v2/settings/objects/${OBJ_ID}" \
  -H "Authorization: Api-Token ${DT_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" -w "\nHTTP:%{http_code}")
echo "$RESP"
if echo "$RESP" | grep -q 'HTTP:403'; then
  cat <<'EOF'

Token lacks settings.write. Do this in the UI instead:

  Settings → Anomaly detection → Services → Response time

  1) Detect response time degradations: ON
  2) Detection mode: using fixed thresholds
  3) All requests (median):  2000 ms
  4) Slowest 10%:            3000 ms
  5) Only alert if ≥ 1 requests per minute   ← critical (was 10)
  6) Abnormal state ≥ 1 minute
  7) Sensitivity: high
  8) Save

Also ensure no per-service override disables response-time detection
for inventory / product / frontend.
EOF
  exit 1
fi

echo "OK — fixed response-time thresholds applied (median 2s / p90 3s / min 1 rpm)"
