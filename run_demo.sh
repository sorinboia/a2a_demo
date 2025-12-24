#!/usr/bin/env bash
set -euo pipefail

SCOUT_LOG=${SCOUT_LOG:-/tmp/a2a_track_scout.log}
ORCH_LOG=${ORCH_LOG:-/tmp/a2a_playlist_orch.log}
PYTHONUNBUFFERED=${PYTHONUNBUFFERED:-1}

start_agent() {
  local name=$1
  local log_file=$2
  shift 2

  (
    PYTHONUNBUFFERED=$PYTHONUNBUFFERED "$@" 2>&1 \
      | sed -u "s/^/[$name] /" \
      | tee "$log_file"
  ) &
  echo $!
}

cleanup() {
  if [[ -n "${SCOUT_PID:-}" ]]; then
    kill -- -"$SCOUT_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${ORCH_PID:-}" ]]; then
    kill -- -"$ORCH_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

SCOUT_PID=$(start_agent "SCOUT" "$SCOUT_LOG" python -u track_scout_agent.py)
ORCH_PID=$(start_agent "ORCH" "$ORCH_LOG" python -u playlist_agent.py)

sleep 2

if [[ $# -gt 0 ]]; then
  python client.py "$*"
else
  python client.py
fi
