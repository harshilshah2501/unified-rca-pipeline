#!/usr/bin/env bash
# Design v3 Stage 1: reproduce order × builder 2×2 at 500k (uniform + hubby).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BIN="${BIN:-$(cargo metadata --format-version 1 --no-deps 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["target_directory"])')/release/map_vortex_bench}"
OUT_ROOT="${OUT_ROOT:-out/design-v3/stage1}"
GIT_SHA="${GIT_SHA:-$(git -C ../../.. rev-parse --short HEAD 2>/dev/null || echo unknown)}"
mkdir -p "$OUT_ROOT"
echo "BIN=$BIN"
for shape in uniform hubby; do
  for sort in natural clustered; do
    out="$OUT_ROOT/500k-${shape}-${sort}"
    echo "===== $out ====="
    "$BIN" \
      --edges 500000 --fix-nodes-from-density --mean-out-degree 5 \
      --estate-shape "$shape" --edge-sort "$sort" \
      --load-mode spine \
      --adj-builder naive --adj-builder sort-aware \
      --layout hash \
      --coldness process-cold \
      --workload-id stage1_2x2 \
      --git-sha "$GIT_SHA" \
      --warmup 1 --repeats 20 \
      --out "$out"
  done
done
python3 "$ROOT/scripts/summarize_stage1.py" "$OUT_ROOT"
echo "STAGE1_DONE"