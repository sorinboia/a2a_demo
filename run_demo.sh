#!/usr/bin/env bash
set -euo pipefail

SCOUT_LOG=${SCOUT_LOG:-/tmp/a2a_track_scout.log}
ORCH_LOG=${ORCH_LOG:-/tmp/a2a_playlist_orch.log}
PYTHONUNBUFFERED=${PYTHONUNBUFFERED:-1}

cleanup() {
  if [[ -n "${SCOUT_PID:-}" ]]; then
    kill "$SCOUT_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${ORCH_PID:-}" ]]; then
    kill "$ORCH_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${SCOUT_TAIL_PID:-}" ]]; then
    kill "$SCOUT_TAIL_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${ORCH_TAIL_PID:-}" ]]; then
    kill "$ORCH_TAIL_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

PYTHONUNBUFFERED=$PYTHONUNBUFFERED python -u track_scout_agent.py >"$SCOUT_LOG" 2>&1 &
SCOUT_PID=$!
PYTHONUNBUFFERED=$PYTHONUNBUFFERED python -u playlist_agent.py >"$ORCH_LOG" 2>&1 &
ORCH_PID=$!

tail -n +1 -f "$SCOUT_LOG" | sed -u "s/^/[SCOUT] /" &
SCOUT_TAIL_PID=$!
tail -n +1 -f "$ORCH_LOG" | sed -u "s/^/[ORCH] /" &
ORCH_TAIL_PID=$!

sleep 2

if [[ $# -gt 0 ]]; then
  python client.py "$*"
else
  python client.py
fi
