#!/usr/bin/env bash
# Guard cold-start portal pages: fact_kind must not appear as live Motadata router vocab.
# Mentions that teach retirement ("no fact_kind") are allowed.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Pages that must stay clean for the slim docs home / eval door
CHECK_PATHS=(
  "docs/index.html"
  "docs/reference/eval-reference.html"
  "docs/fabric/README.md"
  "docs/HUB_PORTAL_AUDIT.md"
  "docs/REPO_AUDIT.md"
)

is_negation_or_retirement() {
  local line="$1"
  # Allow teaching that fact_kind is retired / absent (HTML may wrap tokens in <code>).
  echo "$line" | rg -qi "no.{0,40}fact_kind|without.{0,20}fact_kind|not a fact_kind|retired fact_kind|legacy.{0,40}fact_kind|fact_kind.{0,40}retired|stale.{0,40}fact_kind|mixes stale|against SoT|drift"
}

fail=0
for path in "${CHECK_PATHS[@]}"; do
  if [[ ! -f "$path" ]]; then
    echo "MISSING: $path"
    fail=1
    continue
  fi
  while IFS= read -r line; do
    if ! is_negation_or_retirement "$line"; then
      echo "DRIFT: $path"
      echo "  $line"
      fail=1
    fi
  done < <(rg -n "fact_kind" "$path" 2>/dev/null || true)
done

if [[ $fail -ne 0 ]]; then
  echo "check_doc_drift: FAILED"
  exit 1
fi
echo "check_doc_drift: OK (cold-start paths clean)"
echo "NOTE: observeops-pipeline-hld.html GraphWriter tabs still teach fact_kind — tracked as C3 follow-up."
exit 0
