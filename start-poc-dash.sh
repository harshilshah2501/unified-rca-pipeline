#!/usr/bin/env bash
# Start the PoC dashboard on :8765 — at most one live instance.
# Usage: ./start-poc-dash.sh [start|status|stop]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PORT="${POC_DASHBOARD_PORT:-8765}"
HOST="${POC_DASHBOARD_HOST:-0.0.0.0}"
PIDFILE="${POC_DASH_PIDFILE:-/tmp/poc-dash-${PORT}.pid}"
LOCKFILE="${POC_DASH_LOCKFILE:-/tmp/poc-dash-${PORT}.lock}"
LOGFILE="${POC_DASH_LOGFILE:-/tmp/poc-dash-${PORT}.log}"
PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY="$(command -v python3)"
SERVER="${ROOT}/eval/benchmarking/dashboard/server.py"
# Shim path still works: ${ROOT}/benchmarking → eval/benchmarking
URL="http://127.0.0.1:${PORT}/"

cmd="${1:-start}"

is_alive() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

pid_is_ours() {
  local pid="$1" cmdline
  is_alive "$pid" || return 1
  cmdline="$(tr '\0' ' ' <"/proc/${pid}/cmdline" 2>/dev/null || true)"
  [[ "$cmdline" == *"benchmarking/dashboard/server.py"* || "$cmdline" == *"eval/benchmarking/dashboard/server.py"* ]]
}

port_up() {
  curl -sf -o /dev/null --connect-timeout 1 --max-time 2 "$URL" 2>/dev/null
}

read_pid() {
  [[ -f "$PIDFILE" ]] || return 0
  tr -d '[:space:]' <"$PIDFILE"
}

status() {
  local pid
  pid="$(read_pid || true)"
  if pid_is_ours "${pid:-}"; then
    if port_up; then
      echo "running pid=${pid} url=${URL}"
      return 0
    fi
    echo "pidfile pid=${pid} alive but ${URL} not responding yet"
    return 0
  fi
  if port_up; then
    echo "running (port ${PORT} up; no owned pidfile) url=${URL}"
    return 0
  fi
  echo "stopped"
  return 1
}

stop() {
  local pid
  pid="$(read_pid || true)"
  if pid_is_ours "${pid:-}"; then
    kill "$pid" 2>/dev/null || true
    for _ in 1 2 3 4 5; do
      is_alive "$pid" || break
      sleep 0.2
    done
    is_alive "$pid" && kill -9 "$pid" 2>/dev/null || true
  fi
  rm -f "$PIDFILE"
  echo "stopped"
}

start_unlocked() {
  local pid
  pid="$(read_pid || true)"
  if pid_is_ours "${pid:-}"; then
    echo "already running pid=${pid} url=${URL}"
    return 0
  fi
  if port_up; then
    echo "already running (port ${PORT} in use) url=${URL}"
    return 0
  fi
  rm -f "$PIDFILE"
  mkdir -p "$(dirname "$LOGFILE")"
  # Close inherited flock FD (9) so the daemon never holds the start lock.
  (
    cd "$ROOT"
    export PYTHONUNBUFFERED=1
    export POC_DASHBOARD_HOST="$HOST"
    export POC_DASHBOARD_PORT="$PORT"
    exec "$PY" "$SERVER"
  ) >>"$LOGFILE" 2>&1 9>&- &
  pid=$!
  echo "$pid" >"$PIDFILE"
  sleep 0.4
  if ! is_alive "$pid"; then
    echo "failed to start — see ${LOGFILE}" >&2
    rm -f "$PIDFILE"
    return 1
  fi
  echo "started pid=${pid} url=${URL} log=${LOGFILE}"
}

start() {
  # Exclusive lock only for the start critical section (not held by the daemon).
  (
    flock -n 9 || {
      flock 9
      status || true
      exit 0
    }
    start_unlocked
  ) 9>"$LOCKFILE"
}

case "$cmd" in
  start) start ;;
  status) status ;;
  stop) stop ;;
  *)
    echo "usage: $0 [start|status|stop]" >&2
    exit 2
    ;;
esac
