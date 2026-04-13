#!/usr/bin/env bash
# Stack dev Arquantix complète : Docker (Postgres, Redis, API WeasyPrint, CMS, Web) + Next local (npm run dev).
# Prérequis : Docker Desktop allumé, .env.arquantix présent.
#
# Usage (depuis la racine du dépôt vancelian-app) :
#   bash scripts/dev-reset.sh              # reset + compose up + Next en arrière-plan
#   bash scripts/dev-reset.sh --no-next    # Docker uniquement
#   bash scripts/dev-reset.sh --build      # idem + docker compose --build
#   bash scripts/dev-reset.sh --stop       # arrêt compose + libération ports (API, Next, DB, Redis, CMS) + Next PID
#
# Docker : si le daemon est off, tentative de lancement (macOS : open -a Docker) puis attente ≤ 20 s.
# Projet compose : COMPOSE_PROJECT_NAME + ARQUANTIX_COMPOSE_FILE dans .env.arquantix (défaut recovery).
# Volumes nommés inchangés (arquantix_arquantix-db-data) — voir docs/arquantix/LOCAL_ENV_RUNBOOK.md.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

resolve_compose_project_name() {
  if [ -n "${COMPOSE_PROJECT_NAME:-}" ]; then
    printf '%s' "$COMPOSE_PROJECT_NAME"
    return
  fi
  if [ -f "$REPO_ROOT/.env.arquantix" ]; then
    _cpn="$( (grep -E '^[[:space:]]*COMPOSE_PROJECT_NAME=' "$REPO_ROOT/.env.arquantix" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    if [ -n "${_cpn:-}" ]; then
      printf '%s' "$_cpn"
      return
    fi
  fi
  printf '%s' "arquantixrecovery"
}

resolve_compose_file() {
  if [ -f "$REPO_ROOT/.env.arquantix" ]; then
    _cf="$( (grep -E '^[[:space:]]*ARQUANTIX_COMPOSE_FILE=' "$REPO_ROOT/.env.arquantix" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    if [ -n "${_cf:-}" ]; then
      printf '%s' "$_cf"
      return
    fi
  fi
  printf '%s' "docker-compose.arquantix-recovery.yml"
}

COMPOSE_PROJECT="$(resolve_compose_project_name)"
export COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT"

COMPOSE_REL="$(resolve_compose_file)"
COMPOSE=(docker compose --project-name "$COMPOSE_PROJECT" --env-file "$REPO_ROOT/.env.arquantix" -f "$REPO_ROOT/$COMPOSE_REL")

# Anciens noms de projet (expérimentations / états corrompus) — down + purge ciblés avant le projet courant.
# Les volumes de données sont nommés explicitement dans docker-compose.arquantix.yml ; un « down » ici
# ne les supprime pas sans -v (voir docs/arquantix/LOCAL_ENV_RUNBOOK.md).
# Noms historiques / récupération manuelle — toujours « down » avant le projet courant (volumes inchangés sans -v).
# Inclut les variantes utilisées en secours quand l’état Compose « arquantix » était dead / fantôme.
# « arquantix » : namespace historique souvent corrompu (Docker Desktop) — down sans -v pour libérer l’état.
LEGACY_COMPOSE_PROJECTS=(vancelian-app arquantix_clean arquantixfresh arquantix_clean2 arquantix_recover arquantix2 arquantix_validate arquantix_live arquantix)

STOP_ONLY=false
NO_NEXT=false
WITH_BUILD=false
for arg in "$@"; do
  case "$arg" in
    --stop|stop) STOP_ONLY=true ;;
    --no-next) NO_NEXT=true ;;
    --build) WITH_BUILD=true ;;
  esac
done

NEXT_PID_FILE="${TMPDIR:-/tmp}/arquantix-next-dev.pid"
NEXT_LOG_FILE="${TMPDIR:-/tmp}/arquantix-next-dev.log"

log() { printf '[dev] %s\n' "$*"; }

# Lit ports depuis .env.arquantix (pas d’export global du fichier entier).
load_arquantix_ports() {
  DEV_API_PORT=8000
  DEV_DOCKER_WEB_PORT=3000
  DEV_DB_PORT=5443
  DEV_REDIS_PORT=6379
  DEV_CMS_PORT=1337
  if [ -f "$REPO_ROOT/.env.arquantix" ]; then
    # « grep » sans match → code ≠ 0 ; avec pipefail actif, protéger par « || true ».
    _ap="$( (grep -E '^[[:space:]]*API_PORT=' "$REPO_ROOT/.env.arquantix" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    _wp="$( (grep -E '^[[:space:]]*WEB_PORT=' "$REPO_ROOT/.env.arquantix" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    _db="$( (grep -E '^[[:space:]]*DB_PORT=' "$REPO_ROOT/.env.arquantix" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    _rd="$( (grep -E '^[[:space:]]*REDIS_PORT=' "$REPO_ROOT/.env.arquantix" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    _cm="$( (grep -E '^[[:space:]]*CMS_PORT=' "$REPO_ROOT/.env.arquantix" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    [ -n "$_ap" ] && DEV_API_PORT="$_ap"
    [ -n "$_wp" ] && DEV_DOCKER_WEB_PORT="$_wp"
    [ -n "$_db" ] && DEV_DB_PORT="$_db"
    [ -n "$_rd" ] && DEV_REDIS_PORT="$_rd"
    [ -n "$_cm" ] && DEV_CMS_PORT="$_cm"
  fi
  # Next lancé sur l’hôte par ce script (next dev) — port par défaut de Next.js.
  DEV_LOCAL_NEXT_PORT=3000
}

# Libère les ports hôte habituels (processus locaux, pas seulement Docker).
# Supprime tout conteneur encore étiqueté par ce projet compose (répare l’état où arquantix-db
# pointe vers un ID fantôme ex. 529be… — « compose down » ne suffit pas toujours).
purge_compose_project_containers() {
  local proj
  proj="${1:-$COMPOSE_PROJECT}"
  log "Purge conteneurs résiduels (label com.docker.compose.project=$proj)…"
  docker ps -aq --filter "label=com.docker.compose.project=$proj" 2>/dev/null | while read -r cid; do
    [ -z "${cid:-}" ] && continue
    docker rm -f "$cid" 2>/dev/null || true
  done
}

purge_all_legacy_compose_containers() {
  local leg
  for leg in "${LEGACY_COMPOSE_PROJECTS[@]}"; do
    [ "$leg" = "$COMPOSE_PROJECT" ] && continue
    purge_compose_project_containers "$leg"
  done
}

legacy_compose_teardown() {
  if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    return 0
  fi
  if [ ! -f "$REPO_ROOT/.env.arquantix" ]; then
    return 0
  fi
  # ⚠️  Chemin LEGACY uniquement : compose standard (docker-compose.arquantix.yml), jamais -v.
  #    La stack active du repo est recovery (.env.arquantix) — ne pas confondre avec un « up » daily.
  log "Arrêt des anciens projets compose (fantôme 529be / ancien nom de dossier)…"
  local leg
  for leg in "${LEGACY_COMPOSE_PROJECTS[@]}"; do
    [ "$leg" = "$COMPOSE_PROJECT" ] && continue
    (cd "$REPO_ROOT" && docker compose --project-name "$leg" --env-file "$REPO_ROOT/.env.arquantix" -f "$REPO_ROOT/docker-compose.arquantix.yml" down --remove-orphans) 2>/dev/null || true
  done
  purge_all_legacy_compose_containers
}

free_arquantix_host_ports() {
  load_arquantix_ports
  log "Libération des ports hôte (Next, API, Postgres, Redis, CMS, variantes)…"
  kill_port 3000
  kill_port 3001
  kill_port "${DEV_API_PORT}"
  kill_port "${DEV_DOCKER_WEB_PORT}"
  kill_port "${DEV_DB_PORT}"
  kill_port "${DEV_REDIS_PORT}"
  kill_port "${DEV_CMS_PORT}"
  # Valeurs compose par défaut si .env différent / ancien setup
  kill_port 5433
  kill_port 5443
  kill_port 8000
}

msg_check() { printf '[CHECK] %s\n' "$*"; }
msg_error() { printf '[ERROR] %s\n' "$*"; }
msg_info() { printf '[INFO] %s\n' "$*"; }
msg_wait() { printf '[WAIT] %s\n' "$*"; }
msg_ok() { printf '[OK] %s\n' "$*"; }

# Attente du daemon Docker (lancement auto de Docker Desktop sur macOS). À utiliser pour le reset / dev uniquement.
ensure_docker_ready() {
  if ! command -v docker >/dev/null 2>&1; then
    msg_error "docker absent du PATH — installe Docker Desktop ou le client Docker."
    exit 1
  fi

  msg_check "Docker daemon..."
  if docker info >/dev/null 2>&1; then
    msg_ok "Docker is ready"
    return 0
  fi

  msg_error "Docker not running"

  if [ "$(uname -s)" = "Darwin" ]; then
    msg_info "Starting Docker Desktop..."
    open -a Docker 2>/dev/null || true
  else
    msg_info "Démarre le service Docker sur cette machine (ex. sudo service docker start), puis réessaie."
  fi

  msg_wait "Waiting for Docker..."
  local i=0
  while [ "$i" -lt 20 ]; do
    if docker info >/dev/null 2>&1; then
      msg_ok "Docker is ready"
      return 0
    fi
    sleep 1
    i=$((i + 1))
  done

  msg_error "Docker daemon non disponible. Lance Docker Desktop."
  printf '       Commande possible : open -a Docker\n' >&2
  exit 1
}

kill_port() {
  local port="$1"
  if lsof -ti ":$port" >/dev/null 2>&1; then
    lsof -ti ":$port" | xargs kill -9 2>/dev/null || true
    log "Port $port libéré"
  fi
}

# curl peut répéter %{http_code} dans certains cas → on ne garde que 3 chiffres.
curl_http_code() {
  local raw url="$1"
  raw="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 --max-time 12 "$url" 2>/dev/null || true)"
  raw="$(printf '%s' "$raw" | tr -cd '0-9')"
  printf '%.3s' "${raw}000"
}

stop_next_from_pidfile() {
  if [ -f "$NEXT_PID_FILE" ]; then
    local pid
    pid="$(cat "$NEXT_PID_FILE" 2>/dev/null || true)"
    if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      sleep 1
      kill -9 "$pid" 2>/dev/null || true
      log "Ancien Next (PID $pid) arrêté"
    fi
    rm -f "$NEXT_PID_FILE"
  fi
}

start_next_background() {
  if [ "$NO_NEXT" = true ]; then
    log "Next ignoré (--no-next). Lance manuellement : cd services/arquantix/web && npm run dev"
    return 0
  fi
  if ! command -v npm >/dev/null 2>&1; then
    log "npm absent — Next non démarré."
    return 0
  fi
  stop_next_from_pidfile
  kill_port 3000
  kill_port 3001

  log "Démarrage Next.js (npm run dev) en arrière-plan…"
  : >"$NEXT_LOG_FILE"
  (
    cd "$REPO_ROOT/services/arquantix/web"
    exec npm run dev
  ) >>"$NEXT_LOG_FILE" 2>&1 &
  echo $! >"$NEXT_PID_FILE"
  log "Next PID $(cat "$NEXT_PID_FILE") — log : $NEXT_LOG_FILE"
  log "URL attendue : http://localhost:3000 (ou 3001 si conflit — voir le log)"
}

# --- stop only ---
if [ "$STOP_ONLY" = true ]; then
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    legacy_compose_teardown
    log "Arrêt compose « $COMPOSE_PROJECT » (volumes conservés)…"
    (cd "$REPO_ROOT" && "${COMPOSE[@]}" down --remove-orphans) || true
    log "Purge conteneurs résiduels (labels projet, pas de noms fixes)…"
    purge_compose_project_containers
  else
    msg_info "Docker indisponible — arrêt compose / conteneurs ignorés (ports et Next nettoyés quand même)."
  fi
  stop_next_from_pidfile
  free_arquantix_host_ports
  log "Terminé (stop). Données Postgres/Redis dans les volumes Docker inchangées."
  exit 0
fi

# --- reset complet ---
ensure_docker_ready
load_arquantix_ports

log "Projet compose Docker : $COMPOSE_PROJECT — fichier $COMPOSE_REL (volumes nommés : arquantix_arquantix-db-data, arquantix_arquantix-redis-data)"
log "Repo : $REPO_ROOT"
log "Arrêt des services…"
legacy_compose_teardown
(cd "$REPO_ROOT" && "${COMPOSE[@]}" down --remove-orphans) || true

stop_next_from_pidfile
free_arquantix_host_ports

log "Suppression des conteneurs orphelins (labels projet)…"
purge_compose_project_containers
(cd "$REPO_ROOT" && "${COMPOSE[@]}" rm -sf 2>/dev/null || true)

# État compose parfois corrompu (service DB → ID fantôme) : forcer recréation des conteneurs.
UP_ARGS=(up -d --force-recreate --remove-orphans)
if [ "$WITH_BUILD" = true ]; then
  UP_ARGS=(up -d --build --force-recreate --remove-orphans)
  log "Build des images activé (--build)…"
fi
log "Démarrage Docker : Postgres, Redis, API (WeasyPrint), CMS, Web…"
(cd "$REPO_ROOT" && "${COMPOSE[@]}" "${UP_ARGS[@]}")

msg_wait "Init conteneurs + binding ports (souvent 10–30 s après démarrage à froid de Docker Desktop)…"
sleep 15

msg_check "API health..."
ok=false
i=0
while [ "$i" -lt 120 ]; do
  code="$(curl_http_code "http://127.0.0.1:${DEV_API_PORT}/health")"
  if [ "$code" = "200" ]; then
    ok=true
    break
  fi
  sleep 1
  i=$((i + 1))
done
if [ "$ok" = true ]; then
  msg_ok "API is healthy"
else
  msg_error "API not responding"
  log "Pas de HTTP 200 sur /health après ~120 s — voir : docker compose --project-name $COMPOSE_PROJECT ... logs arquantix-api --tail 80"
  msg_info "Souvent : Docker Desktop venait de démarrer ; réessaie dans 1 min ou relance ce script."
fi

log "Postgres (arquantix-db) : volume conservé ; port hôte = DB_PORT dans .env.arquantix (souvent 5443)."
log "BFF Next hôte → API : BACKEND_URL=http://127.0.0.1:${DEV_API_PORT} dans services/arquantix/web/.env.local"

start_next_background

if [ "$NO_NEXT" = false ] && [ -f "$NEXT_PID_FILE" ]; then
  msg_check "Next local (port ${DEV_LOCAL_NEXT_PORT})…"
  next_ok=false
  j=0
  while [ "$j" -lt 120 ]; do
    code_n="$(curl_http_code "http://127.0.0.1:${DEV_LOCAL_NEXT_PORT}/")"
    # Code HTTP sur 3 chiffres uniquement (évite « 000000 » qui passait != 000)
    if [ "${#code_n}" -eq 3 ] && [ "$code_n" -ge 200 ] 2>/dev/null && [ "$code_n" -lt 600 ] 2>/dev/null; then
      next_ok=true
      break
    fi
    sleep 1
    j=$((j + 1))
  done
  if [ "$next_ok" = true ]; then
    msg_ok "Next répond (HTTP $code_n)"
  else
    msg_error "Next ne répond pas sur le port ${DEV_LOCAL_NEXT_PORT} après ~120s"
    log "Diagnostic : tail -80 $NEXT_LOG_FILE"
    msg_info "Vérifie Node/npm, ou lance à la main : cd services/arquantix/web && npm run dev"
  fi
fi

if [ -f "$REPO_ROOT/services/arquantix/tooling/check_arquantix_dev_stack.sh" ]; then
  log "Santé stack (résumé) :"
  WEB_PORT="$DEV_LOCAL_NEXT_PORT" API_PORT="$DEV_API_PORT" bash "$REPO_ROOT/services/arquantix/tooling/check_arquantix_dev_stack.sh" || true
fi

log "─── URLs (127.0.0.1 = souvent plus fiable que « localhost ») ───"
log "  Santé API         : http://127.0.0.1:${DEV_API_PORT}/health"
log "  Doc API (Swagger) : http://127.0.0.1:${DEV_API_PORT}/docs"
log "  Site Next (npm)   : http://127.0.0.1:${DEV_LOCAL_NEXT_PORT}/"
log "  Admin web (UI)    : http://127.0.0.1:${DEV_LOCAL_NEXT_PORT}/admin/login"
log "  Next (Docker)     : http://127.0.0.1:${DEV_DOCKER_WEB_PORT}/  (si conteneur arquantix-web up)"
log "  Rappel : sur :${DEV_API_PORT}, les routes /admin/* sont des endpoints API (JSON), pas la page admin du navigateur."
log "Terminé. Docker : docker compose logs -f   |   Next log : tail -f $NEXT_LOG_FILE"
log "Stop tout : bash scripts/dev-reset.sh --stop"
