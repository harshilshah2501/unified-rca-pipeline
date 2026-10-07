#!/usr/bin/env bash
# Same-dataset bakeoff: federated run → lean run → comparative analysis
set -euo pipefail
cd "$(dirname "$0")/../.."
VENV="${VENV:-.venv}"
if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q -r federated-pipeline/requirements.txt -r federated-pipeline/murphy/requirements.txt
fi
PY="$VENV/bin/python"
RUN_ID="${RUN_ID:-bakeoff-$(date -u +%Y%m%dT%H%M%SZ)}"

echo "=== 0. validate shared dataset ==="
"$PY" benchmarking/benchmark/validate_corpus.py

echo "=== 1. federated pipeline on datasets/observeops (run_id=$RUN_ID) ==="
"$PY" benchmarking/benchmark/run_federated.py --all --run-id "$RUN_ID"

echo "=== 2. lean pipeline on the same dataset (run_id=$RUN_ID) ==="
"$PY" benchmarking/benchmark/run_lean.py --all --run-id "$RUN_ID"

echo "=== 3. comparative analysis ==="
"$PY" benchmarking/benchmark/compare.py --run-id "$RUN_ID"

echo ""
echo "Individual runs:"
echo "  benchmarking/results/federated/UC-*/run-$RUN_ID/"
echo "  benchmarking/results/lean/UC-*/run-$RUN_ID/"
echo "Comparison:"
echo "  benchmarking/results/comparison/COMPARISON.md"
echo "  benchmarking/results/comparison/comparison.json"
