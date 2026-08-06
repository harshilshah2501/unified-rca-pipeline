#!/usr/bin/env bash
# Ingest a Dynatrace CUSTOM_DEPLOYMENT (or CUSTOM_CONFIGURATION) event so Davis
# can correlate change → fault for code-level RCA demos.
#
# Usage (from dynatrace-rca-lab/):
#   ./scripts/ingest_change_event.sh deployment
#   ./scripts/ingest_change_event.sh config
#
# Requires .env: DT_ENV_URL, DT_API_TOKEN (events.ingest scope).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
set -a; source "$ROOT/.env"; set +a

KIND="${1:-deployment}"
: "${DT_ENV_URL:?Set DT_ENV_URL in .env}"
: "${DT_API_TOKEN:?Set DT_API_TOKEN in .env}"

VERSION="${DT_RELEASE_VERSION:-1.1.0-codepin}"
ENTITY_SELECTOR="${DT_EVENT_ENTITY_SELECTOR:-type(SERVICE),entityName.equals(inventory)}"
TITLE_DEPLOY="Lab deploy inventory ${VERSION} (code-pinpoint demo)"
TITLE_CONFIG="Lab config change inventory warehouse.index (code-pinpoint demo)"

if [[ "$KIND" == "config" ]]; then
  EVENT_TYPE="CUSTOM_CONFIGURATION"
  TITLE="$TITLE_CONFIG"
  EXTRA=$(cat <<EOF
    "dt.event.is_rootcause_relevant": "true",
    "dt.event.allow_davis_merge": "true",
    "config.item": "warehouse.sku_index",
    "config.change": "corrupt_index_rebuild",
    "fault.error_code": "WAREHOUSE_SKU_INDEX_CORRUPT",
    "code.function": "lookup_stock_in_warehouse",
    "code.filepath": "inventory/app.py",
    "lab": "dynatrace-rca-lab"
EOF
)
else
  EVENT_TYPE="CUSTOM_DEPLOYMENT"
  TITLE="$TITLE_DEPLOY"
  EXTRA=$(cat <<EOF
    "dt.event.is_rootcause_relevant": "true",
    "dt.event.allow_davis_merge": "true",
    "dt.event.deployment.name": "inventory-codepin",
    "dt.event.deployment.version": "${VERSION}",
    "dt.event.deployment.project": "dynatrace-rca-lab",
    "dt.event.deployment.release_stage": "rca-lab",
    "dt.event.deployment.release_product": "inventory",
    "fault.error_code": "WAREHOUSE_SKU_INDEX_CORRUPT",
    "code.function": "lookup_stock_in_warehouse",
    "code.filepath": "inventory/app.py",
    "lab": "dynatrace-rca-lab"
EOF
)
fi

BODY=$(cat <<EOF
{
  "eventType": "${EVENT_TYPE}",
  "title": "${TITLE}",
  "timeout": 30,
  "entitySelector": "${ENTITY_SELECTOR}",
  "properties": {
${EXTRA}
  }
}
EOF
)

echo "POST ${DT_ENV_URL}/api/v2/events/ingest"
echo "$BODY" | python3 -m json.tool
HTTP=$(curl -sS -o /tmp/dt_event_ingest.json -w "%{http_code}" \
  -X POST "${DT_ENV_URL}/api/v2/events/ingest" \
  -H "Authorization: Api-Token ${DT_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$BODY")
echo "HTTP ${HTTP}"
cat /tmp/dt_event_ingest.json
echo
if [[ "$HTTP" != "201" && "$HTTP" != "200" ]]; then
  echo "Ingest failed. Token needs events.ingest (and entity must resolve)." >&2
  exit 1
fi
echo "OK — change event ingested. Wait ~1–2 min, then inject inventory.fail + load."
