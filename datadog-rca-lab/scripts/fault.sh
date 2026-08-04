#!/usr/bin/env bash
# Inject / clear faults — same UX as dynatrace-rca-lab/scripts/fault.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAULTS="$ROOT/faults"

usage() {
  cat <<EOF
Usage: $0 <service> <fail|ok|latency> [seconds]
  service: frontend | product | inventory
  fail     → force 503
  ok       → clear fail flag
  latency  → sleep N seconds (default 2) before responding
EOF
  exit 1
}

[[ $# -ge 2 ]] || usage
svc="$1"
action="$2"
case "$svc" in frontend|product|inventory) ;; *) usage ;; esac

mkdir -p "$FAULTS"
case "$action" in
  fail)
    echo true >"$FAULTS/${svc}.fail"
    echo "FAULT ON: $svc → 503"
    ;;
  ok)
    echo false >"$FAULTS/${svc}.fail"
    echo 0 >"$FAULTS/${svc}.latency"
    echo "FAULT OFF: $svc"
    ;;
  latency)
    sec="${3:-2}"
    echo "$sec" >"$FAULTS/${svc}.latency"
    echo "LATENCY ON: $svc → ${sec}s"
    ;;
  *) usage ;;
esac
