#!/usr/bin/env bash
# Decision-validation Action 1 — independent typed-multigraph oracle.
# Frozen candidates: hash · hash_bi · csr_csc × clustered · natural.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BIN="${BIN:-$(cargo metadata --format-version 1 --no-deps 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["target_directory"])')/release/map_vortex_bench}"
OUT_ROOT="${OUT_ROOT:-out/design-v3/action1}"
mkdir -p "$OUT_ROOT"

# Representative shapes for correctness (not full Stage 4.2 matrix).
FAMILIES=(uniform hubby power-law)
# Scales: 100k smoke + 500k primary (1M optional via ACTION1_INCLUDE_1M=1)
SCALES=(100000 500000)
if [[ "${ACTION1_INCLUDE_1M:-0}" == "1" ]]; then
  SCALES+=(1000000)
fi

fail=0
for edges in "${SCALES[@]}"; do
  case $edges in
    100000) label=100k ;;
    500000) label=500k ;;
    1000000) label=1M ;;
    *) label=$edges ;;
  esac
  for fam in "${FAMILIES[@]}"; do
    out="$OUT_ROOT/${label}-${fam}"
    echo "===== action1 $out ====="
    if "$BIN" \
      --edges "$edges" --fix-nodes-from-density --mean-out-degree 5 \
      --estate-family "$fam" --seed 42 \
      --action1-oracle --max-edges 5000000 \
      --out "$out"; then
      echo "OK $out" | tee -a "$OUT_ROOT/status.log"
    else
      echo "FAIL $out" | tee -a "$OUT_ROOT/status.log"
      fail=1
    fi
  done
done

python3 "$ROOT/scripts/summarize_action1.py" "$OUT_ROOT" || true
if [[ "$fail" -ne 0 ]]; then
  echo "ACTION1_FAILED"
  exit 1
fi
echo "ACTION1_DONE"
