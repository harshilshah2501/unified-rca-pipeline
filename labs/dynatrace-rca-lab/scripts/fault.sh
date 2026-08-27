#!/usr/bin/env bash
# Live fault injection without container restart.
# Usage:
#   ./scripts/fault.sh inventory fail on
#   ./scripts/fault.sh inventory fail off
#   ./scripts/fault.sh inventory latency 2
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SVC="${1:?service: frontend|product|inventory}"
KIND="${2:?kind: fail|latency}"
VAL="${3:?value}"
FILE="$ROOT/faults/${SVC}.${KIND}"
echo "$VAL" > "$FILE"
echo "wrote $FILE = $(cat "$FILE")"
curl -s -o /tmp/fault_probe.out -w "probe HTTP %{http_code}\n" http://localhost:19080/ || true
