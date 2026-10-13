#!/usr/bin/env bash
# Action 6 priority 5 — 5M thin ladder under approved mutation envelope.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$ROOT/target}"
BIN="${BIN:-$CARGO_TARGET_DIR/release/map_vortex_bench}"
OUT_ROOT="${OUT_ROOT:-$ROOT/out/design-v3/action6-5m}"
mkdir -p "$OUT_ROOT"
: >"$OUT_ROOT/status.log"
[[ -x "$BIN" ]] || cargo build --release

run_mut() {
  local segs="$1" ins="$2" del="$3" batches="${4:-15}"
  local cell="$OUT_ROOT/cells/5M-hubby-seg${segs}-i${ins}-d${del}"
  if [[ -f "$cell/action6_results.json" ]]; then
    echo "skip $cell" | tee -a "$OUT_ROOT/status.log"
    return 0
  fi
  mkdir -p "$cell"
  echo "===== 5M mutation $cell ====="
  if "$BIN" \
    --edges 5000000 --fix-nodes-from-density --mean-out-degree 5 \
    --estate-family hubby --seed 42 \
    --action6-mutation \
    --segments "$segs" \
    --mutation-batches "$batches" \
    --mutation-batch-inserts "$ins" \
    --mutation-batch-deletes "$del" \
    --max-edges 5000000 \
    --out "$cell"; then
    echo "OK $cell" | tee -a "$OUT_ROOT/status.log"
  else
    echo "FAIL $cell" | tee -a "$OUT_ROOT/status.log"
  fi
}

# Envelope: mut_localized primary (64 + 256), mut_medium sensitivity (64)
run_mut 64 10 2 15
run_mut 256 10 2 10
run_mut 64 1000 200 10

python3 "$ROOT/scripts/summarize_action6_5m.py" "$OUT_ROOT"
echo "ACTION6_5M_DONE" | tee -a "$OUT_ROOT/status.log"
