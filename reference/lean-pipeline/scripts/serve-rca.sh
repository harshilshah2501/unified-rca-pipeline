#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO}"

if [[ -x "${REPO}/.venv/bin/python" ]]; then
  PYTHON="${REPO}/.venv/bin/python"
else
  PYTHON="python3"
fi

export PYTHONPATH="lean-pipeline:."
export OBSERVEOPS_CORPUS="${OBSERVEOPS_CORPUS:-${REPO}/datasets/observeops}"

exec "${PYTHON}" -m lean_rca serve --host 0.0.0.0 --port "${PORT:-8780}"
