#!/usr/bin/env bash
# Action 6 — conventional csr_csc full rebuild vs segmented_csr_csc incremental publish.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$ROOT/target}"
BIN="${BIN:-$CARGO_TARGET_DIR/release/map_vortex_bench}"
OUT_ROOT="${OUT_ROOT:-$ROOT/out/design-v3/action6}"
mkdir -p "$OUT_ROOT"
: >"$OUT_ROOT/status.log"

[[ -x "$BIN" ]] || cargo build --release

SEGMENTS_LIST=(16 64 256)
# 1M primary; optional 5M via ACTION6_5M=1
SCALES=(1000000)
[[ "${ACTION6_5M:-0}" == "1" ]] && SCALES+=(5000000)

for edges in "${SCALES[@]}"; do
  case $edges in
    1000000) label=1M ;;
    5000000) label=5M ;;
    *) label=$edges ;;
  esac
  for segs in "${SEGMENTS_LIST[@]}"; do
    cell="$OUT_ROOT/cells/${label}-hubby-seg${segs}"
    if [[ -f "$cell/action6_results.json" ]]; then
      echo "skip existing $cell" | tee -a "$OUT_ROOT/status.log"
      continue
    fi
    mkdir -p "$cell"
    echo "===== action6 $cell ====="
    if "$BIN" \
      --edges "$edges" --fix-nodes-from-density --mean-out-degree 5 \
      --estate-family hubby --seed 42 \
      --action6-mutation \
      --segments "$segs" \
      --mutation-batches "${MUTATION_BATCHES:-20}" \
      --mutation-batch-inserts "${MUTATION_INS:-1000}" \
      --mutation-batch-deletes "${MUTATION_DEL:-200}" \
      --max-edges 5000000 \
      --out "$cell"; then
      echo "OK $cell" | tee -a "$OUT_ROOT/status.log"
    else
      echo "FAIL $cell" | tee -a "$OUT_ROOT/status.log"
    fi
  done
done

python3 "$ROOT/scripts/summarize_action6.py" "$OUT_ROOT"
echo "ACTION6_DONE" | tee -a "$OUT_ROOT/status.log"
