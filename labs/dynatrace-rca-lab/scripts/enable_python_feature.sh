#!/usr/bin/env bash
# Enable Dynatrace OneAgent Python deep monitoring via Settings API.
# Requires DT_API_TOKEN with settings.read + settings.write
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/.env"

: "${DT_ENV_URL:?}"
: "${DT_API_TOKEN:?Set DT_API_TOKEN in .env}"

AUTH="Api-Token ${DT_API_TOKEN}"
BASE="${DT_ENV_URL%/}"

echo "== Looking up OneAgent feature schema objects for Python =="
curl -fsS -H "Authorization: ${AUTH}" \
  "${BASE}/api/v2/settings/objects?schemaIds=builtin:oneagent.features&fields=objectId,value,scope&pageSize=500" \
  | python3 - <<'PY'
import json,sys
data=json.load(sys.stdin)
items=data.get("items",[])
py=[i for i in items if "python" in json.dumps(i).lower()]
print(f"total features: {len(items)}, python-related: {len(py)}")
for i in py:
    print(json.dumps(i, indent=2))
open("/tmp/dt_python_features.json","w").write(json.dumps(py, indent=2))
PY

if [[ ! -s /tmp/dt_python_features.json ]]; then
  echo "No python-related OneAgent features found. Check token scopes / permissions."
  exit 1
fi

echo
echo "== Enabling every python-related OneAgent feature =="
python3 - <<PY
import json, urllib.request, os
base=os.environ.get("DT_ENV_URL","").rstrip("/")
token=os.environ["DT_API_TOKEN"]
features=json.load(open("/tmp/dt_python_features.json"))
for f in features:
    oid=f["objectId"]
    val=dict(f.get("value") or {})
    val["enabled"]=True
    body=json.dumps({"value": val}).encode()
    req=urllib.request.Request(
        f"{base}/api/v2/settings/objects/{oid}",
        data=body,
        method="PUT",
        headers={
            "Authorization": f"Api-Token {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(oid, resp.status, val.get("key"), "-> enabled")
    except Exception as e:
        print(oid, "FAILED", e)
PY

echo
echo "Done. Restart lab containers so processes reinject:"
echo "  cd $ROOT && docker compose up -d --force-recreate"
echo "Then generate traffic for 2-5 minutes."
