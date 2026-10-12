#!/usr/bin/env bash
# Design v3 Stage 3.5: fair layout compare (hash, hash_bi, csr, csr_csc, hybrid).
# Equal reverse mix for every layout; per-class query stats.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BIN="${BIN:-$(cargo metadata --format-version 1 --no-deps 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["target_directory"])')/release/map_vortex_bench}"
OUT_ROOT="${OUT_ROOT:-out/design-v3/stage3_5}"
GIT_SHA="${GIT_SHA:-$(git -C ../../.. rev-parse --short HEAD 2>/dev/null || echo unknown)}"
mkdir -p "$OUT_ROOT"
# Focused matrix: 500k primary + 250k; uniform + hubby; clustered primary
for edges in 250000 500000; do
  case $edges in 250000) label=250k ;; 500000) label=500k ;; esac
  for shape in uniform hubby; do
    for sort in clustered natural; do
      out="$OUT_ROOT/${label}-${shape}-${sort}"
      echo "===== $out ====="
      "$BIN" \
        --edges "$edges" --fix-nodes-from-density --mean-out-degree 5 \
        --estate-shape "$shape" --edge-sort "$sort" \
        --load-mode spine \
        --adj-builder sort-aware \
        --layout hash --layout hash-bi --layout csr --layout csr-csc --layout hybrid \
        --hybrid-inserts 1000 --hybrid-deletes 500 \
        --coldness process-cold \
        --emit-queries --query-replicate 5 \
        --workload-id stage3_5_fair \
        --git-sha "$GIT_SHA" \
        --warmup 1 --repeats 5 \
        --out "$out"
    done
  done
done
python3 "$ROOT/scripts/summarize_stage3_5.py" "$OUT_ROOT"
echo "STAGE3_5_DONE"