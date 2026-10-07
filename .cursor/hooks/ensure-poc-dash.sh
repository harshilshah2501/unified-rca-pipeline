#!/usr/bin/env bash
# Cursor workspaceOpen / sessionStart: ensure one PoC dashboard on :8765.
set -euo pipefail

# Consume hook JSON (required); ignore contents.
cat >/dev/null

ROOT="${CURSOR_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
START="${ROOT}/start-poc-dash.sh"

if [[ ! -x "$START" ]]; then
  echo '{}' 
  exit 0
fi

# Detach so the hook returns immediately; singleton logic lives in start-poc-dash.sh.
(
  "$START" start
) >/tmp/poc-dash-hook.log 2>&1 &

echo '{}'
exit 0
