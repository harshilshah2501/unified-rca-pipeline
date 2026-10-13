#!/usr/bin/env bash
# Action 5 — concurrent readers + dual-index hold under approved envelope.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$ROOT/target}"
BIN="${BIN:-$CARGO_TARGET_DIR/release/map_vortex_bench}"
OUT_ROOT="${OUT_ROOT:-$ROOT/out/design-v3/action5}"
GIT_SHA="${GIT_SHA:-$(git -C ../../.. rev-parse --short HEAD 2>/dev/null || echo unknown)}"
mkdir -p "$OUT_ROOT"
: >"$OUT_ROOT/status.log"

LAYOUTS=(hash hash-bi csr-csc)
READERS=(1 4 16)
REPEATS="${REPEATS:-5}"

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
  local edges="$1" prep="$2" layout="$3" readers="$4" dual="$5" cell="$6"
  if [[ -f "$cell/results.json" ]]; then
    echo "skip existing $cell" | tee -a "$OUT_ROOT/status.log"
    return 0
  fi
  mkdir -p "$cell"
  local seed_ci
  seed_ci="$(tr -d '\n' <"$prep/seed_ci.txt")"
  local dual_flag=()
  if [[ "$dual" == "1" ]]; then
    dual_flag=(--dual-index-hold)
  fi
  echo "===== action5 $cell readers=$readers dual=$dual ====="
  if "$BIN" \
    --edges "$edges" --fix-nodes-from-density --mean-out-degree 5 \
    --estate-family hubby --edge-sort clustered \
    --load-mode spine --adj-builder sort-aware \
    --layout "$layout" --coldness process-cold \
    --workload-id "action5_r${readers}" \
    --workload-profile scope-policy-mixed \
    --query-trace "$prep/traces/scope_policy_mixed.jsonl" \
    --reuse-parts "$prep" --skip-estate-generate \
    --seed-ci "$seed_ci" --git-sha "$GIT_SHA" \
    --warmup 1 --repeats "$REPEATS" \
    --concurrent-readers "$readers" \
    "${dual_flag[@]}" \
    --max-edges 5000000 --out "$cell"; then
    echo "OK $cell" | tee -a "$OUT_ROOT/status.log"
  else
    echo "FAIL $cell" | tee -a "$OUT_ROOT/status.log"
  fi
}

prep1=$(prepare 1000000 1M)
for readers in "${READERS[@]}"; do
  dual=0
  [[ "$readers" == "1" ]] && dual=1
  for layout in "${LAYOUTS[@]}"; do
    run_cell 1000000 "$prep1" "$layout" "$readers" "$dual" \
      "$OUT_ROOT/cells/1M-hubby-r${readers}-${layout}" || true
  done
done

prep5=$(prepare 5000000 5M)
for readers in 1 16; do
  for layout in "${LAYOUTS[@]}"; do
    run_cell 5000000 "$prep5" "$layout" "$readers" 0 \
      "$OUT_ROOT/cells/5M-hubby-r${readers}-${layout}" || true
  done
done

python3 "$ROOT/scripts/summarize_action5.py" "$OUT_ROOT"
echo "ACTION5_DONE" | tee -a "$OUT_ROOT/status.log"
