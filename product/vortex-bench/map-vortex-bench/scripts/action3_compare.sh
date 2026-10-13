#!/usr/bin/env bash
# Action 3 — Milestone A final comparison under approved envelope
# (motadata_like_hubby + scope_policy_mixed). Frozen layouts only.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$ROOT/target}"
BIN="${BIN:-$CARGO_TARGET_DIR/release/map_vortex_bench}"
OUT_ROOT="${OUT_ROOT:-out/design-v3/action3}"
GIT_SHA="${GIT_SHA:-$(git -C ../../.. rev-parse --short HEAD 2>/dev/null || echo unknown)}"
REPEATS_1M="${REPEATS_1M:-20}"
REPEATS_5M="${REPEATS_5M:-10}"
TRACE_LEN="${TRACE_LEN:-200}"
mkdir -p "$OUT_ROOT"
: >"$OUT_ROOT/status.log"

LAYOUTS=(hash hash-bi csr-csc)
PROFILES=(forward-dominant balanced reverse-heavy scope-policy-mixed)
FAMILIES=(uniform hubby)

if [[ ! -x "$BIN" ]]; then
  echo "Building release binary..."
  cargo build --release
fi

trace_for_profile() {
  local prep="$1" profile="$2"
  case "$profile" in
    forward-dominant) echo "$prep/traces/forward_dominant.jsonl" ;;
    balanced) echo "$prep/traces/balanced.jsonl" ;;
    reverse-heavy) echo "$prep/traces/reverse_heavy.jsonl" ;;
    scope-policy-mixed) echo "$prep/traces/scope_policy_mixed.jsonl" ;;
    *) echo "$prep/traces/${profile//-/_}.jsonl" ;;
  esac
}

run_cell() {
  local edges="$1" fam="$2" sort="$3" layout="$4" profile="$5" prep="$6" cell_out="$7" repeats="$8"
  local seed_ci trace
  seed_ci="$(tr -d '\n' <"$prep/seed_ci.txt")"
  trace="$(trace_for_profile "$prep" "$profile")"
  if [[ ! -f "$trace" ]]; then
    echo "SKIP missing trace $trace" | tee -a "$OUT_ROOT/status.log"
    return 0
  fi
  if [[ -f "$cell_out/results.json" ]]; then
    echo "skip existing $cell_out" | tee -a "$OUT_ROOT/status.log"
    return 0
  fi
  mkdir -p "$cell_out"
  echo "===== action3 $cell_out (repeats=$repeats) ====="
  if "$BIN" \
    --edges "$edges" --fix-nodes-from-density --mean-out-degree 5 \
    --estate-family "$fam" --edge-sort "$sort" \
    --load-mode spine --adj-builder sort-aware \
    --layout "$layout" \
    --hybrid-inserts 0 --hybrid-deletes 0 \
    --coldness process-cold \
    --workload-id "action3_${profile}" \
    --workload-profile "$profile" \
    --query-trace "$trace" \
    --reuse-parts "$prep" \
    --skip-estate-generate \
    --seed-ci "$seed_ci" \
    --git-sha "$GIT_SHA" \
    --warmup 1 --repeats "$repeats" \
    --max-edges 5000000 \
    --out "$cell_out"; then
    echo "OK $cell_out" | tee -a "$OUT_ROOT/status.log"
  else
    echo "FAIL_OR_OOM $cell_out" | tee -a "$OUT_ROOT/status.log"
  fi
}

prepare() {
  local edges="$1" fam="$2" sort="$3" prep="$4"
  mkdir -p "$prep/traces"
  if [[ -f "$prep/seed_ci.txt" && -f "$prep/traces/scope_policy_mixed.jsonl" ]]; then
    echo "reuse prep $prep"
    return 0
  fi
  echo "===== prepare $prep ====="
  if ! "$BIN" \
    --edges "$edges" --fix-nodes-from-density --mean-out-degree 5 \
    --estate-family "$fam" --edge-sort "$sort" \
    --validate-properties --prepare-only \
    --emit-all-workload-traces "$prep/traces" \
    --trace-len "$TRACE_LEN" \
    --max-edges 5000000 \
    --out "$prep"; then
    echo "PREP_FAIL $prep" | tee -a "$OUT_ROOT/status.log"
    return 1
  fi
}

# --- 1M full factorial: uniform+hubby × 4 profiles × 3 layouts, clustered, N=20 ---
for fam in "${FAMILIES[@]}"; do
  prep="$OUT_ROOT/prep/1M-${fam}-clustered"
  prepare 1000000 "$fam" clustered "$prep" || continue
  for profile in "${PROFILES[@]}"; do
    for layout in "${LAYOUTS[@]}"; do
      cell="$OUT_ROOT/cells/1M-${fam}-clustered-${profile}-${layout}"
      run_cell 1000000 "$fam" clustered "$layout" "$profile" "$prep" "$cell" "$REPEATS_1M" || true
    done
  done
done

# Natural-order control: 1M hubby × scope-policy-mixed × 3 layouts
prep_n="$OUT_ROOT/prep/1M-hubby-natural"
if prepare 1000000 hubby natural "$prep_n"; then
  for layout in "${LAYOUTS[@]}"; do
    cell="$OUT_ROOT/cells/1M-hubby-natural-scope-policy-mixed-${layout}"
    run_cell 1000000 hubby natural "$layout" scope-policy-mixed "$prep_n" "$cell" "$REPEATS_1M" || true
  done
fi

# --- 5M thin ladder: uniform+hubby × scope-policy-mixed × 3 layouts, N=10 ---
for fam in "${FAMILIES[@]}"; do
  prep="$OUT_ROOT/prep/5M-${fam}-clustered"
  prepare 5000000 "$fam" clustered "$prep" || continue
  for layout in "${LAYOUTS[@]}"; do
    cell="$OUT_ROOT/cells/5M-${fam}-clustered-scope-policy-mixed-${layout}"
    run_cell 5000000 "$fam" clustered "$layout" scope-policy-mixed "$prep" "$cell" "$REPEATS_5M" || true
  done
done

python3 "$ROOT/scripts/summarize_action3.py" "$OUT_ROOT"
echo "ACTION3_DONE" | tee -a "$OUT_ROOT/status.log"
