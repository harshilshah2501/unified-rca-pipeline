#!/usr/bin/env bash
# Design v3 Stage 4.1 — characterize six estate families (properties only).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BIN="${BIN:-$(cargo metadata --format-version 1 --no-deps 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["target_directory"])')/release/map_vortex_bench}"
OUT_ROOT="${OUT_ROOT:-out/design-v3/stage4/characterize}"
mkdir -p "$OUT_ROOT"

FAMILIES=(uniform hubby power-law hierarchical community layered)
# 5M only after 1M succeeds for that family
SCALES=(500000 1000000)

pass_1m=()
for edges in "${SCALES[@]}"; do
  case $edges in
    500000) label=500k ;;
    1000000) label=1M ;;
    *) label=$edges ;;
  esac
  for fam in "${FAMILIES[@]}"; do
    out="$OUT_ROOT/${label}-${fam}"
    echo "===== characterize $out ====="
    if "$BIN" \
      --edges "$edges" --fix-nodes-from-density --mean-out-degree 5 \
      --estate-family "$fam" --edge-sort clustered \
      --characterize-only --validate-properties \
      --max-edges 5000000 \
      --out "$out"; then
      echo "OK $out" | tee -a "$OUT_ROOT/status.log"
      if [[ "$edges" == "1000000" ]]; then
        pass_1m+=("$fam")
      fi
    else
      echo "FAIL $out" | tee -a "$OUT_ROOT/status.log"
    fi
  done
done

# Optional 5M for families that passed 1M
for fam in "${pass_1m[@]:-}"; do
  out="$OUT_ROOT/5M-${fam}"
  echo "===== characterize $out ====="
  if "$BIN" \
    --edges 5000000 --fix-nodes-from-density --mean-out-degree 5 \
    --estate-family "$fam" --edge-sort clustered \
    --characterize-only --validate-properties \
    --max-edges 5000000 \
    --out "$out"; then
    echo "OK $out" | tee -a "$OUT_ROOT/status.log"
  else
    echo "FAIL_OR_OOM $out" | tee -a "$OUT_ROOT/status.log"
  fi
done

python3 "$ROOT/scripts/summarize_stage4_1.py" "$OUT_ROOT"
echo "STAGE4_1_DONE"
