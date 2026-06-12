#!/usr/bin/env bash
# Garde l'API FastAPI (uvicorn) vivante en local : relance si le processus sort.
# Usage :
#   bash scripts/arquantix-api-dev-daemon.sh          # premier plan
#   bash scripts/arquantix-api-dev-daemon.sh --bg     # arrière-plan (dev-reset)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
API_DIR="$REPO_ROOT/services/arquantix/api"

API_PID_FILE="${TMPDIR:-/tmp}/arquantix-api-dev.pid"
API_LOG_FILE="${TMPDIR:-/tmp}/arquantix-api-dev.log"
DAEMON_PID_FILE="${TMPDIR:-/tmp}/arquantix-api-dev-daemon.pid"
API_PORT="${API_PORT:-8000}"

BACKGROUND=false
for arg in "$@"; do
  case "$arg" in
    --bg|--background) BACKGROUND=true ;;
  esac
done

resolve_api_python() {
  if [ -x "$API_DIR/.venv/bin/python" ]; then
    printf '%s' "$API_DIR/.venv/bin/python"
  elif [ -x "$API_DIR/.venv-r2/bin/python" ]; then
    printf '%s' "$API_DIR/.venv-r2/bin/python"
  else
    printf '%s' "python3"
  fi
}

API_PYTHON="$(resolve_api_python)"

log() { printf '[api-daemon] %s\n' "$*" >>"$API_LOG_FILE"; }

stop_previous() {
  if [ -f "$DAEMON_PID_FILE" ]; then
    local dpid
    dpid="$(cat "$DAEMON_PID_FILE" 2>/dev/null || true)"
    if [ -n "${dpid:-}" ] && kill -0 "$dpid" 2>/dev/null; then
      kill "$dpid" 2>/dev/null || true
      sleep 1
      kill -9 "$dpid" 2>/dev/null || true
    fi
    rm -f "$DAEMON_PID_FILE"
  fi
  if [ -f "$API_PID_FILE" ]; then
    local apid
    apid="$(cat "$API_PID_FILE" 2>/dev/null || true)"
    if [ -n "${apid:-}" ] && kill -0 "$apid" 2>/dev/null; then
      kill "$apid" 2>/dev/null || true
      sleep 1
      kill -9 "$apid" 2>/dev/null || true
    fi
    rm -f "$API_PID_FILE"
  fi
  if lsof -ti ":$API_PORT" >/dev/null 2>&1; then
    lsof -ti ":$API_PORT" | xargs kill -9 2>/dev/null || true
  fi
}

SUPERVISOR_LOOP='
log() { printf "[api-daemon] %s\n" "$*" >>"$API_LOG_FILE"; }
log "superviseur arrière-plan (PID $$)"
while true; do
  log "lancement uvicorn…"
  (
    cd "$API_DIR"
    exec "$API_PYTHON" -m uvicorn main:app --reload \
      --reload-include ".env" --reload-include ".env.local" \
      --host 0.0.0.0 --port "$API_PORT"
  ) >>"$API_LOG_FILE" 2>&1 &
  echo $! >"$API_PID_FILE"
  wait "$(cat "$API_PID_FILE" 2>/dev/null)" 2>/dev/null || true
  log "uvicorn terminé — relance dans 3 s"
  rm -f "$API_PID_FILE"
  sleep 3
done
'

if [ "$BACKGROUND" = true ]; then
  stop_previous
  : >>"$API_LOG_FILE"
  if command -v python3 >/dev/null 2>&1; then
    spid="$(API_DIR="$API_DIR" API_PYTHON="$API_PYTHON" API_PORT="$API_PORT" \
      API_PID_FILE="$API_PID_FILE" API_LOG_FILE="$API_LOG_FILE" \
      SUPERVISOR_LOOP="$SUPERVISOR_LOOP" python3 - <<'PY'
import os, subprocess
script = os.environ.get("SUPERVISOR_LOOP", "")
log_path = os.environ["API_LOG_FILE"]
with open(log_path, "a", encoding="utf-8") as logf:
    p = subprocess.Popen(
        ["/bin/bash", "-c", script],
        env=os.environ.copy(),
        stdin=subprocess.DEVNULL,
        stdout=logf,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    print(p.pid)
PY
)"
    printf '%s\n' "$spid" >"$DAEMON_PID_FILE"
  else
    nohup env API_DIR="$API_DIR" API_PYTHON="$API_PYTHON" API_PORT="$API_PORT" \
      API_PID_FILE="$API_PID_FILE" API_LOG_FILE="$API_LOG_FILE" \
      SUPERVISOR_LOOP="$SUPERVISOR_LOOP" \
      bash -c 'eval "$SUPERVISOR_LOOP"' </dev/null >>"$API_LOG_FILE" 2>&1 &
    echo $! >"$DAEMON_PID_FILE"
    disown -h "$(cat "$DAEMON_PID_FILE")" 2>/dev/null || true
  fi
  printf '[api-daemon] superviseur PID %s — log %s\n' "$(cat "$DAEMON_PID_FILE")" "$API_LOG_FILE"
  # Compat scripts qui lisent /tmp/arquantix-api.pid
  ln -sf "$API_PID_FILE" /tmp/arquantix-api.pid 2>/dev/null || cp "$API_PID_FILE" /tmp/arquantix-api.pid 2>/dev/null || true
  exit 0
fi

trap 'log "daemon arrêté (signal)"; exit 0' INT TERM
stop_previous
echo $$ >"$DAEMON_PID_FILE"
eval "$SUPERVISOR_LOOP"
