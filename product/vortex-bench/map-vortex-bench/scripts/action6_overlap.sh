#!/usr/bin/env bash
# Action 6 residual — atomic publish under pinned readers + dual-hold RSS.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$ROOT/target}"
BIN="${BIN:-$CARGO_TARGET_DIR/release/map_vortex_bench}"
OUT_ROOT="${OUT_ROOT:-$ROOT/out/design-v3/action6-overlap}"
mkdir -p "$OUT_ROOT"
: >"$OUT_ROOT/status.log"
[[ -x "$BIN" ]] || cargo build --release

# Localized small batches (where segmented is promising) + medium batches.
run_cell() {
  local label="$1" segs="$2" ins="$3" del="$4" readers="$5"
  local cell="$OUT_ROOT/cells/${label}-seg${segs}-i${ins}-d${del}-r${readers}"
  if [[ -f "$cell/action6_overlap_results.json" ]]; then
    echo "skip $cell" | tee -a "$OUT_ROOT/status.log"
    return 0
  fi
  mkdir -p "$cell"
  echo "===== overlap $cell ====="
  if "$BIN" \
    --edges 1000000 --fix-nodes-from-density --mean-out-degree 5 \
    --estate-family hubby --seed 42 \
    --action6-overlap \
    --segments "$segs" \
    --mutation-batches "${MUTATION_BATCHES:-20}" \
    --mutation-batch-inserts "$ins" \
    --mutation-batch-deletes "$del" \
    --overlap-readers "$readers" \
    --max-edges 5000000 \
    --out "$cell"; then
    echo "OK $cell" | tee -a "$OUT_ROOT/status.log"
  else
    echo "FAIL $cell" | tee -a "$OUT_ROOT/status.log"
  fi
}

run_cell 1M 64 10 2 8
run_cell 1M 256 10 2 8
run_cell 1M 64 1000 200 8
run_cell 1M 256 10 2 16

python3 "$ROOT/scripts/summarize_action6_overlap.py" "$OUT_ROOT"
echo "ACTION6_OVERLAP_DONE" | tee -a "$OUT_ROOT/status.log"
