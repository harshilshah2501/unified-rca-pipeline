#!/usr/bin/env bash
# Design v3 Stage 4.2 — layout screen ≤5M with identical query traces.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BIN="${BIN:-$(cargo metadata --format-version 1 --no-deps 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["target_directory"])')/release/map_vortex_bench}"
OUT_ROOT="${OUT_ROOT:-out/design-v3/stage4/screen}"
GIT_SHA="${GIT_SHA:-$(git -C ../../.. rev-parse --short HEAD 2>/dev/null || echo unknown)}"
mkdir -p "$OUT_ROOT"

FAMILIES=(uniform hubby power-law hierarchical community layered)
LAYOUTS=(hash hash-bi csr csr-csc hybrid)
PROFILES=(forward-dominant balanced reverse-heavy)
# Full matrix at 500k + 1M. 5M is a thin ladder only (see below) — full 5M×6×3×5 is multi-hour.
SCALES=(500000 1000000)

run_cell() {
  local edges="$1" fam="$2" sort="$3" layout="$4" profile="$5" prep="$6" cell_out="$7"
  local seed_ci
  seed_ci="$(cat "$prep/seed_ci.txt" | tr -d '\n')"
  local trace="$prep/traces/${profile//-/_}.jsonl"
  # clap enum ids use underscores in file names from emit
  case "$profile" in
    forward-dominant) trace="$prep/traces/forward_dominant.jsonl" ;;
    balanced) trace="$prep/traces/balanced.jsonl" ;;
    reverse-heavy) trace="$prep/traces/reverse_heavy.jsonl" ;;
  esac
  if [[ ! -f "$trace" ]]; then
    echo "SKIP missing trace $trace" | tee -a "$OUT_ROOT/status.log"
    return 0
  fi
  mkdir -p "$cell_out"
  echo "===== screen $cell_out ====="
  if "$BIN" \
    --edges "$edges" --fix-nodes-from-density --mean-out-degree 5 \
    --estate-family "$fam" --edge-sort "$sort" \
    --load-mode spine --adj-builder sort-aware \
    --layout "$layout" \
    --hybrid-inserts 0 --hybrid-deletes 0 \
    --coldness process-cold \
    --workload-id "stage4_2_${profile}" \
    --workload-profile "$profile" \
    --query-trace "$trace" \
    --reuse-parts "$prep" \
    --skip-estate-generate \
    --seed-ci "$seed_ci" \
    --git-sha "$GIT_SHA" \
    --warmup 1 --repeats 5 \
    --max-edges 5000000 \
    --out "$cell_out"; then
    echo "OK $cell_out" | tee -a "$OUT_ROOT/status.log"
  else
    echo "FAIL_OR_OOM $cell_out" | tee -a "$OUT_ROOT/status.log"
  fi
}

for edges in "${SCALES[@]}"; do
  case $edges in
    500000) label=500k ;;
    1000000) label=1M ;;
    5000000) label=5M ;;
    *) label=$edges ;;
  esac
  for fam in "${FAMILIES[@]}"; do
    prep="$OUT_ROOT/prep/${label}-${fam}-clustered"
    mkdir -p "$prep/traces"
    echo "===== prepare $prep ====="
    if ! "$BIN" \
      --edges "$edges" --fix-nodes-from-density --mean-out-degree 5 \
      --estate-family "$fam" --edge-sort clustered \
      --validate-properties --prepare-only \
      --emit-all-workload-traces "$prep/traces" \
      --trace-len 200 \
      --max-edges 5000000 \
      --out "$prep"; then
      echo "PREP_FAIL $prep" | tee -a "$OUT_ROOT/status.log"
      continue
    fi

    for profile in "${PROFILES[@]}"; do
      for layout in "${LAYOUTS[@]}"; do
        cell="$OUT_ROOT/cells/${label}-${fam}-clustered-${profile}-${layout}"
        run_cell "$edges" "$fam" clustered "$layout" "$profile" "$prep" "$cell" || true
      done
    done

    # Natural edge-order control at 500k only (balanced profile, all layouts)
    if [[ "$edges" == "500000" ]]; then
      prep_n="$OUT_ROOT/prep/${label}-${fam}-natural"
      mkdir -p "$prep_n/traces"
      echo "===== prepare natural $prep_n ====="
      if "$BIN" \
        --edges "$edges" --fix-nodes-from-density --mean-out-degree 5 \
        --estate-family "$fam" --edge-sort natural \
        --validate-properties --prepare-only \
        --emit-all-workload-traces "$prep_n/traces" \
        --trace-len 200 \
        --max-edges 5000000 \
        --out "$prep_n"; then
        for layout in "${LAYOUTS[@]}"; do
          cell="$OUT_ROOT/cells/${label}-${fam}-natural-balanced-${layout}"
          run_cell "$edges" "$fam" natural "$layout" balanced "$prep_n" "$cell" || true
        done
      else
        echo "PREP_FAIL $prep_n" | tee -a "$OUT_ROOT/status.log"
      fi
    fi
  done
done

# Thin 5M ladder: uniform + hubby × balanced × all layouts (ceiling check, not full factorial).
for fam in uniform hubby; do
  prep="$OUT_ROOT/prep/5M-${fam}-clustered"
  mkdir -p "$prep/traces"
  echo "===== prepare thin 5M $prep ====="
  if ! "$BIN" \
    --edges 5000000 --fix-nodes-from-density --mean-out-degree 5 \
    --estate-family "$fam" --edge-sort clustered \
    --validate-properties --prepare-only \
    --emit-all-workload-traces "$prep/traces" \
    --trace-len 200 --max-edges 5000000 --out "$prep"; then
    echo "PREP_FAIL $prep" | tee -a "$OUT_ROOT/status.log"
    continue
  fi
  for layout in "${LAYOUTS[@]}"; do
    cell="$OUT_ROOT/cells/5M-${fam}-clustered-balanced-${layout}"
    if [[ -f "$cell/results.json" ]]; then
      echo "skip existing $cell"
      continue
    fi
    run_cell 5000000 "$fam" clustered "$layout" balanced "$prep" "$cell" || true
  done
done
echo "SKIP remaining 5M full-matrix cells — thin ladder only (uniform+hubby × balanced × 5 layouts)" \
  | tee -a "$OUT_ROOT/status.log"

python3 "$ROOT/scripts/summarize_stage4_2.py" "$OUT_ROOT"
echo "STAGE4_2_DONE"
