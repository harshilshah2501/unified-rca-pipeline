#!/usr/bin/env bash
# Guard cold-start + Motadata teaching pages: fact_kind must not appear as live
# Motadata writer-router vocab. Mentions that teach retirement / bridge / legacy are allowed.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Pages that must stay clean for the slim docs home / eval door / Motadata SoT teaching
CHECK_PATHS=(
  "docs/index.html"
  "docs/reference/eval-reference.html"
  "docs/fabric/README.md"
  "docs/HUB_PORTAL_AUDIT.md"
  "docs/REPO_AUDIT.md"
  "docs/observeops/observeops-pipeline-hld.html"
  "docs/observeops/hld-archive.html"
  "docs/fabric/pillar-b-poc-hub.html"
  "docs/fabric/pillar-b-stream-graph-demo.html"
  "docs/fabric/edge-platform-detect-simulation.html"
)

# Explicit Collect / corpus bridge docs — skip content scan (they own fact_kind enum).
# Listed so operators know they are out of scope for Motadata writer SoT checks.
BRIDGE_ALLOWLIST=(
  "docs/INGEST_DATA_FORMAT.md"
  "docs/observeops/LLD-E1-Collect.md"
  "docs/INGESTION_PIPELINE_VECTOR.md"
  "docs/fabric/data-shape-journey.html"
)

is_negation_or_retirement() {
  local line="$1"
  # Allow teaching that fact_kind is retired / bridge / dual-admit / presence SoT.
  # HTML may wrap tokens in <code>.
  echo "$line" | rg -qi \
    "no.{0,40}fact_kind|without.{0,20}fact_kind|not a fact_kind|retired fact_kind|legacy.{0,40}fact_kind|fact_kind.{0,40}(retired|legacy|bridge)|stale.{0,40}fact_kind|mixes stale|against SoT|drift|bridge|dual-admit|dual admit|presence predicate|topology block|writer_stream|Collect fact_kind|corpus|lab wire|lab fixtures|lab JSONL|until (fixtures )?migrat"
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
  echo "Bridge allowlist (not scanned; Collect corpus owns fact_kind):"
  printf '  %s\n' "${BRIDGE_ALLOWLIST[@]}"
  exit 1
fi
echo "check_doc_drift: OK (cold-start + Motadata teaching paths clean)"
echo "Bridge allowlist (Collect corpus — not Motadata writer SoT):"
printf '  %s\n' "${BRIDGE_ALLOWLIST[@]}"
exit 0
