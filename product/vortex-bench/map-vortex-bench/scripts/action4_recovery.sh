#!/usr/bin/env bash
# Action 4 — cold-to-hot T_ready across coldness tiers (frozen layouts).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$ROOT/target}"
BIN="${BIN:-$CARGO_TARGET_DIR/release/map_vortex_bench}"
OUT_ROOT="${OUT_ROOT:-$ROOT/out/design-v3/action4}"
GIT_SHA="${GIT_SHA:-$(git -C ../../.. rev-parse --short HEAD 2>/dev/null || echo unknown)}"
mkdir -p "$OUT_ROOT"
: >"$OUT_ROOT/status.log"

LAYOUTS=(hash hash-bi csr-csc)
COLDNESS=(process-cold disk-cold page-cache-warm remote-proxy)
REPEATS_1M="${REPEATS_1M:-15}"
REPEATS_5M="${REPEATS_5M:-8}"

[[ -x "$BIN" ]] || cargo build --release

prepare() {
  local edges="$1" label="$2"
  local prep="$OUT_ROOT/prep/${label}-hubby-clustered"
  mkdir -p "$prep/traces"
  if [[ -f "$prep/seed_ci.txt" && -f "$prep/traces/scope_policy_mixed.jsonl" ]]; then
    echo "reuse prep $prep" >&2
    printf '%s\n' "$prep"
    return 0
  fi
  echo "===== prepare $prep =====" >&2
  "$BIN" --edges "$edges" --fix-nodes-from-density --mean-out-degree 5 \
    --estate-family hubby --edge-sort clustered \
    --validate-properties --prepare-only \
    --emit-all-workload-traces "$prep/traces" --trace-len 200 \
    --max-edges 5000000 --out "$prep" >&2
  printf '%s\n' "$prep"
}

run_cell() {
  local edges="$1" prep="$2" layout="$3" cold="$4" repeats="$5" cell="$6"
  if [[ -f "$cell/results.json" ]]; then
    echo "skip existing $cell" | tee -a "$OUT_ROOT/status.log"
    return 0
  fi
  mkdir -p "$cell"
  local seed_ci trace
  seed_ci="$(tr -d '\n' <"$prep/seed_ci.txt")"
  trace="$prep/traces/scope_policy_mixed.jsonl"
  echo "===== action4 $cell ====="
  if "$BIN" \
    --edges "$edges" --fix-nodes-from-density --mean-out-degree 5 \
    --estate-family hubby --edge-sort clustered \
    --load-mode spine --adj-builder sort-aware \
    --layout "$layout" --coldness "$cold" \
    --workload-id "action4_${cold}" \
    --workload-profile scope-policy-mixed \
    --query-trace "$trace" \
    --reuse-parts "$prep" --skip-estate-generate \
    --seed-ci "$seed_ci" --git-sha "$GIT_SHA" \
    --warmup 1 --repeats "$repeats" --max-edges 5000000 \
    --out "$cell"; then
    echo "OK $cell" | tee -a "$OUT_ROOT/status.log"
  else
    echo "FAIL $cell" | tee -a "$OUT_ROOT/status.log"
  fi
}

prep1=$(prepare 1000000 1M)
for cold in "${COLDNESS[@]}"; do
  for layout in "${LAYOUTS[@]}"; do
    run_cell 1000000 "$prep1" "$layout" "$cold" "$REPEATS_1M" \
      "$OUT_ROOT/cells/1M-hubby-${cold}-${layout}" || true
  done
done

# 5M: process_cold + disk_cold only (remote_proxy copy of 5M parts is heavy)
prep5=$(prepare 5000000 5M)
for cold in process-cold disk-cold; do
  for layout in "${LAYOUTS[@]}"; do
    run_cell 5000000 "$prep5" "$layout" "$cold" "$REPEATS_5M" \
      "$OUT_ROOT/cells/5M-hubby-${cold}-${layout}" || true
  done
done

python3 "$ROOT/scripts/summarize_action4.py" "$OUT_ROOT"
echo "ACTION4_DONE" | tee -a "$OUT_ROOT/status.log"
