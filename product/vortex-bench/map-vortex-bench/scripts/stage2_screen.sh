#!/usr/bin/env bash
# Design v3 Stage 2: factor screening (hash layout only).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BIN="${BIN:-$(cargo metadata --format-version 1 --no-deps 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["target_directory"])')/release/map_vortex_bench}"
OUT_ROOT="${OUT_ROOT:-out/design-v3/stage2}"
GIT_SHA="${GIT_SHA:-$(git -C ../../.. rev-parse --short HEAD 2>/dev/null || echo unknown)}"
mkdir -p "$OUT_ROOT"
for edges in 100000 500000 1000000; do
  case $edges in
    100000) label=100k ;;
    500000) label=500k ;;
    1000000) label=1000k ;;
  esac
  for shape in uniform hubby; do
    for sort in natural clustered; do
      for load in spine full; do
        out="$OUT_ROOT/${label}-${shape}-${sort}-${load}"
        echo "===== $out ====="
        "$BIN" \
          --edges "$edges" --fix-nodes-from-density --mean-out-degree 5 \
          --estate-shape "$shape" --edge-sort "$sort" \
          --load-mode "$load" \
          --adj-builder naive --adj-builder sort-aware \
          --layout hash \
          --coldness process-cold \
          --emit-queries --query-replicate 2 \
          --workload-id stage2_screen \
          --git-sha "$GIT_SHA" \
          --warmup 1 --repeats 5 \
          --out "$out"
      done
    done
  done
done
python3 "$ROOT/scripts/summarize_stage2.py" "$OUT_ROOT"
echo "STAGE2_DONE"