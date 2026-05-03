#!/usr/bin/env bash
#
# Démarrage automatique (boot / login) — stack Docker Arquantix **recovery** uniquement.
#
# Ne fait JAMAIS : docker compose down -v, volume prune, system prune --volumes,
#                   projet compose « arquantix » (namespace historique), ni arrêt d'autres stacks.
#
# Usage manuel :
#   bash scripts/start_arquantix_recovery_boot.sh
#
# Variables optionnelles :
#   ARQUANTIX_BOOT_SKIP_HEALTH=1  — compose up puis sortie 0 sans attendre /health (dépannage)
#   ARQUANTIX_BOOT_DOCKER_WAIT_SEC — défaut 300 (attente max Docker prêt)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

readonly ENV_FILE="$REPO_ROOT/.env.arquantix"
readonly COMPOSE_REL="docker-compose.arquantix-recovery.yml"
readonly COMPOSE_ABS="$REPO_ROOT/$COMPOSE_REL"
readonly PROJECT_FIXED="arquantixrecovery"

LOG_TS() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "$(LOG_TS) [arquantix-recovery-boot] $*"; }

# launchd (LaunchAgent) n’injecte pas le PATH du shell interactif — Docker CLI est souvent sous Homebrew.
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/local/sbin:/usr/bin:/bin:/usr/sbin:/sbin${PATH:+:$PATH}"

resolve_docker_bin() {
  local c
  for c in /opt/homebrew/bin/docker /usr/local/bin/docker; do
    [[ -x "$c" ]] && { echo "$c"; return 0; }
  done
  c="$(command -v docker 2>/dev/null || true)"
  [[ -n "$c" && -x "$c" ]] && { echo "$c"; return 0; }
  return 1
}

DOCKER_WAIT="${ARQUANTIX_BOOT_DOCKER_WAIT_SEC:-300}"
SKIP_HEALTH="${ARQUANTIX_BOOT_SKIP_HEALTH:-0}"

if [[ ! -f "$ENV_FILE" ]]; then
  log "ERROR: fichier manquant : $ENV_FILE"
  exit 1
fi
if [[ ! -f "$COMPOSE_ABS" ]]; then
  log "ERROR: compose manquant : $COMPOSE_ABS"
  exit 1
fi

# Garde-fou : refuser le namespace historique « arquantix » ou toute valeur autre que recovery.
_cpn="$(
  (grep -E '^[[:space:]]*COMPOSE_PROJECT_NAME=' "$ENV_FILE" || true) | head -1 \
    | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
)"
if [[ -n "$_cpn" ]]; then
  if [[ "$_cpn" == "arquantix" ]]; then
    log "ERROR: COMPOSE_PROJECT_NAME=arquantix (namespace interdit pour cet autostart). Corriger .env.arquantix vers arquantixrecovery."
    exit 1
  fi
  if [[ "$_cpn" != "$PROJECT_FIXED" ]]; then
    log "ERROR: COMPOSE_PROJECT_NAME='$_cpn' (attendu: $PROJECT_FIXED). Refus sécurité autostart."
    exit 1
  fi
else
  log "WARN: COMPOSE_PROJECT_NAME absent de .env.arquantix — poursuite avec projet imposé $PROJECT_FIXED"
fi

API_PORT=8000
_ap="$(
  (grep -E '^[[:space:]]*API_PORT=' "$ENV_FILE" || true) | head -1 \
    | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
)"
[[ -n "$_ap" ]] && API_PORT="$_ap"

HEALTH_URL="http://127.0.0.1:${API_PORT}/health"

DOCKER_BIN=""
if ! DOCKER_BIN="$(resolve_docker_bin)"; then
  log "ERROR: binaire docker introuvable (essayé /opt/homebrew/bin/docker, /usr/local/bin/docker, puis PATH étendu). Installez Docker Desktop / CLI ou ajustez le PATH."
  exit 1
fi
log "Docker CLI : $DOCKER_BIN"

log "Attente du daemon Docker (max ${DOCKER_WAIT}s)…"
_dwait=0
while ! "$DOCKER_BIN" info >/dev/null 2>&1; do
  if [[ "$_dwait" -ge "$DOCKER_WAIT" ]]; then
    log "ERROR: Docker indisponible après ${DOCKER_WAIT}s (Docker Desktop démarré ?)"
    exit 1
  fi
  sleep 3
  _dwait=$((_dwait + 3))
done
log "Docker répond."

log "Compose up — project=$PROJECT_FIXED file=$COMPOSE_REL (pas de down, pas de prune)"
# Toujours ces arguments fixes ; ne pas dériver vers docker-compose.arquantix.yml ni projet arquantix.
"$DOCKER_BIN" compose --project-name "$PROJECT_FIXED" --env-file "$ENV_FILE" -f "$COMPOSE_ABS" up -d --remove-orphans

if [[ "$SKIP_HEALTH" == "1" ]]; then
  log "WARN: ARQUANTIX_BOOT_SKIP_HEALTH=1 — santé API ignorée."
  exit 0
fi

log "Pause initiale 8s puis vérification $HEALTH_URL …"
sleep 8

_health_wait=120
_elapsed=0
while [[ "$_elapsed" -lt "$_health_wait" ]]; do
  if command -v curl >/dev/null 2>&1; then
    if curl -sf --max-time 5 "$HEALTH_URL" >/dev/null; then
      log "OK — API répond sur $HEALTH_URL"
      exit 0
    fi
  else
    log "ERROR: curl absent — impossible de vérifier /health"
    exit 1
  fi
  sleep 4
  _elapsed=$((_elapsed + 4))
done

log "ERROR: /health non joignable après ${_health_wait}s — voir : $DOCKER_BIN compose --project-name $PROJECT_FIXED ... logs arquantix-api"
exit 1
