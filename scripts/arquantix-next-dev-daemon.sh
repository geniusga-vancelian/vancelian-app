#!/usr/bin/env bash
# Garde Next.js (npm run dev) vivant en local : relance automatique si le processus sort.
# Usage :
#   bash scripts/arquantix-next-dev-daemon.sh          # premier plan (Ctrl+C arrête tout)
#   bash scripts/arquantix-next-dev-daemon.sh --bg   # arrière-plan (dev-reset)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WEB_DIR="$REPO_ROOT/services/arquantix/web"

NEXT_PID_FILE="${TMPDIR:-/tmp}/arquantix-next-dev.pid"
NEXT_LOG_FILE="${TMPDIR:-/tmp}/arquantix-next-dev.log"
DAEMON_PID_FILE="${TMPDIR:-/tmp}/arquantix-next-dev-daemon.pid"

BACKGROUND=false
for arg in "$@"; do
  case "$arg" in
    --bg|--background) BACKGROUND=true ;;
  esac
done

log() { printf '[next-daemon] %s\n' "$*" >>"$NEXT_LOG_FILE"; }

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
  if [ -f "$NEXT_PID_FILE" ]; then
    local npid
    npid="$(cat "$NEXT_PID_FILE" 2>/dev/null || true)"
    if [ -n "${npid:-}" ] && kill -0 "$npid" 2>/dev/null; then
      kill "$npid" 2>/dev/null || true
      sleep 1
      kill -9 "$npid" 2>/dev/null || true
    fi
    rm -f "$NEXT_PID_FILE"
  fi
  if lsof -ti ":3000" >/dev/null 2>&1; then
    lsof -ti ":3000" | xargs kill -9 2>/dev/null || true
  fi
}

run_loop() {
  log "boucle superviseur démarrée (WEB_DIR=$WEB_DIR)"
  while true; do
    log "lancement npm run dev…"
    (
      cd "$WEB_DIR"
      export HOSTNAME=0.0.0.0
      export PORT=3000
      exec npm run dev
    ) >>"$NEXT_LOG_FILE" 2>&1 &
    local child=$!
    echo "$child" >"$NEXT_PID_FILE"
    log "Next PID $child"
    if ! wait "$child" 2>/dev/null; then
      log "Next terminé (code $?) — relance dans 3 s"
    fi
    rm -f "$NEXT_PID_FILE"
    sleep 3
  done
}

# Boucle superviseur (partagée premier plan / arrière-plan détaché).
SUPERVISOR_LOOP='
log() { printf "[next-daemon] %s\n" "$*" >>"$NEXT_LOG_FILE"; }
log "superviseur arrière-plan (PID $$)"
while true; do
  log "lancement npm run dev…"
  (cd "$WEB_DIR" && export HOSTNAME=0.0.0.0 PORT=3000 && exec npm run dev) >>"$NEXT_LOG_FILE" 2>&1 &
  echo $! >"$NEXT_PID_FILE"
  wait "$(cat "$NEXT_PID_FILE" 2>/dev/null)" 2>/dev/null || true
  log "Next terminé — relance dans 3 s"
  rm -f "$NEXT_PID_FILE"
  sleep 3
done
'

if [ "$BACKGROUND" = true ]; then
  stop_previous
  : >>"$NEXT_LOG_FILE"
  # Nouvelle session POSIX : évite que le superviseur reçoive SIGTERM quand le shell
  # parent (ex. commande Cursor) se termine — cause fréquente de « port 3000 libre ».
  if command -v python3 >/dev/null 2>&1; then
    spid="$(WEB_DIR="$WEB_DIR" NEXT_PID_FILE="$NEXT_PID_FILE" NEXT_LOG_FILE="$NEXT_LOG_FILE" \
      SUPERVISOR_LOOP="$SUPERVISOR_LOOP" python3 - <<'PY'
import os, subprocess
script = os.environ.get("SUPERVISOR_LOOP", "")
log_path = os.environ["NEXT_LOG_FILE"]
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
    nohup env WEB_DIR="$WEB_DIR" NEXT_PID_FILE="$NEXT_PID_FILE" NEXT_LOG_FILE="$NEXT_LOG_FILE" \
      SUPERVISOR_LOOP="$SUPERVISOR_LOOP" \
      bash -c 'eval "$SUPERVISOR_LOOP"' </dev/null >>"$NEXT_LOG_FILE" 2>&1 &
    echo $! >"$DAEMON_PID_FILE"
    disown -h "$(cat "$DAEMON_PID_FILE")" 2>/dev/null || true
  fi
  printf '[next-daemon] superviseur PID %s — log %s\n' "$(cat "$DAEMON_PID_FILE")" "$NEXT_LOG_FILE"
  exit 0
fi

trap 'log "daemon arrêté (signal)"; exit 0' INT TERM
stop_previous
echo $$ >"$DAEMON_PID_FILE"
run_loop
