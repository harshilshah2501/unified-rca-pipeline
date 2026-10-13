#!/usr/bin/env bash
# Action 6 priority 3 — crash injection + durable recovery (lab model).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$ROOT/target}"
BIN="${BIN:-$CARGO_TARGET_DIR/release/map_vortex_bench}"
OUT_ROOT="${OUT_ROOT:-$ROOT/out/design-v3/action6-durability}"
mkdir -p "$OUT_ROOT"
: >"$OUT_ROOT/status.log"
[[ -x "$BIN" ]] || cargo build --release

run_cell() {
  local edges="$1" label="$2" segs="$3" ins="$4" del="$5"
  local cell="$OUT_ROOT/cells/${label}-seg${segs}-i${ins}-d${del}"
  if [[ -f "$cell/action6_durability_results.json" ]]; then
    echo "skip $cell" | tee -a "$OUT_ROOT/status.log"
    return 0
  fi
  mkdir -p "$cell"
  echo "===== durability $cell ====="
  if "$BIN" \
    --edges "$edges" --fix-nodes-from-density --mean-out-degree 5 \
    --estate-family hubby --seed 42 \
    --action6-durability \
    --segments "$segs" \
    --mutation-batch-inserts "$ins" \
    --mutation-batch-deletes "$del" \
    --max-edges 5000000 \
    --out "$cell"; then
    echo "OK $cell" | tee -a "$OUT_ROOT/status.log"
  else
    echo "FAIL $cell" | tee -a "$OUT_ROOT/status.log"
  fi
}

# Fast ladder + one 1M cell
run_cell 200000 200k 64 10 2
run_cell 200000 200k 64 1000 200
run_cell 1000000 1M 64 10 2

python3 "$ROOT/scripts/summarize_action6_durability.py" "$OUT_ROOT"
echo "ACTION6_DURABILITY_DONE" | tee -a "$OUT_ROOT/status.log"
