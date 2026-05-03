#!/usr/bin/env bash
#
# Arquantix recovery — dashboard terminal (lecture seule).
# Aucune modification de stack : pas de restart, pas de down, pas de prune.
#
# Usage :
#   bash scripts/status.sh           # snapshot
#   bash scripts/status.sh --watch   # rafraîchissement (STATUS_REFRESH_SEC, défaut 3)
#
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT" || exit 1

WATCH=0
case "${1:-}" in --watch|-w) WATCH=1 ;; esac
REFRESH_SEC="${STATUS_REFRESH_SEC:-3}"

# shellcheck source=arquantix_compose_lib.sh
source "$SCRIPT_DIR/arquantix_compose_lib.sh"
arquantix_lib_set_root "$REPO_ROOT"

ENV_FILE="$REPO_ROOT/.env.arquantix"

read_env_kv() {
  local key="$1"
  local def="${2:-}"
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "$def"
    return
  fi
  local v
  v="$( (grep -E "^[[:space:]]*${key}=" "$ENV_FILE" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -n "$v" ]] && echo "$v" || echo "$def"
}

API_PORT="$(read_env_kv API_PORT 8000)"
WEB_PORT="$(read_env_kv WEB_PORT 3000)"
DB_PORT="$(read_env_kv DB_PORT 5443)"
REDIS_PORT="$(read_env_kv REDIS_PORT 6379)"
CPN_ENV="$(read_env_kv COMPOSE_PROJECT_NAME "")"
ACF_ENV="$(read_env_kv ARQUANTIX_COMPOSE_FILE "")"

PROJ="$(arquantix_expected_compose_project)"
CF="$(arquantix_compose_file)"
EXPECTED_PROJ="arquantixrecovery"
EXPECTED_CF="docker-compose.arquantix-recovery.yml"

BLD='\033[1m'
DIM='\033[2m'
RST='\033[0m'
GRN='\033[1;32m'
RED='\033[1;31m'
YLW='\033[1;33m'
CYN='\033[36m'

line() { printf '%s\n' "$*"; }
hr() { line "${DIM}────────────────────────────────────────────────────────────${RST}"; }

print_block() {
  local ts
  ts="$(date '+%Y-%m-%d %H:%M:%S')"
  if [[ -n "${STATUS_TICK:-}" ]]; then
    ts="$ts  ${DIM}(tick #${STATUS_TICK})${RST}"
  fi

  echo ""
  line "${BLD}${CYN}━━ Arquantix recovery — status ━━${RST}"
  hr
  line "${BLD}Stack${RST}     🔧 ${PROJ}   📦 ${CF}"
  line "${BLD}Env${RST}       ${NODE_ENV:-—} (NODE_ENV shell ; conteneurs inchangés)"
  line "${BLD}Time${RST}      ${ts}"
  hr

  # --- Docker ---
  line "${BLD}Docker${RST}"
  if ! command -v docker >/dev/null 2>&1; then
    line "  ${RED}CLI docker absent du PATH${RST}"
  elif ! docker info >/dev/null 2>&1; then
    line "  ${RED}Daemon indisponible (Docker Desktop lancé ?)${RST}"
  else
    _dv="$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "?")"
    _ctx="$(docker context show 2>/dev/null || echo "default")"
    line "  ${GRN}OK${RST} — server ${_dv} · context ${_ctx}"
  fi
  hr

  # --- Services ---
  line "${BLD}Services (projet ${PROJ})${RST}"
  SERVICES=(arquantix-db arquantix-redis arquantix-api arquantix-web)
  for svc in "${SERVICES[@]}"; do
    cid="$(arquantix_cid_for_service "$svc")"
    if [[ -z "$cid" ]]; then
      line "  ${RED}✗${RST} ${svc} — ${RED}not running${RST}"
      continue
    fi
    st="$(docker inspect --format '{{.State.Status}}' "$cid" 2>/dev/null || echo "?")"
    hn="$(docker inspect --format '{{.Name}}' "$cid" 2>/dev/null | sed 's#^/##')"
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}n/a{{end}}' "$cid" 2>/dev/null || echo "n/a")"
    [[ -z "$health" ]] && health="n/a"
    ports="$(docker port "$cid" 2>/dev/null | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
    [[ -z "$ports" ]] && ports="(aucun publish vu)"
    if [[ "$st" == "running" ]]; then
      line "  ${GRN}●${RST} ${svc} — ${GRN}running${RST} · health ${health}"
    else
      line "  ${RED}●${RST} ${svc} — ${RED}${st}${RST} · health ${health}"
    fi
    line "      ${DIM}container ${hn}${RST}"
    line "      ${DIM}ports ${ports}${RST}"
  done
  hr

  # --- Health applicatif ---
  line "${BLD}Health${RST}"
  if command -v curl >/dev/null 2>&1; then
    if curl -sf --max-time 4 "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
      line "  ${GRN}API${RST}  GET /health → OK (http://127.0.0.1:${API_PORT})"
    else
      line "  ${RED}API${RST}  GET /health → ${RED}fail${RST} (http://127.0.0.1:${API_PORT})"
    fi
    _wc="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 6 "http://127.0.0.1:${WEB_PORT}/" 2>/dev/null || echo 000)"
    if [[ "$_wc" == "200" ]]; then
      line "  ${GRN}Web${RST}  GET / → ${_wc} (http://127.0.0.1:${WEB_PORT})"
    else
      line "  ${YLW}Web${RST}  GET / → ${_wc} (http://127.0.0.1:${WEB_PORT})"
    fi
  else
    line "  ${YLW}curl absent — HTTP non testé${RST}"
  fi

  _cdb="$(arquantix_cid_for_service arquantix-db)"
  _crd="$(arquantix_cid_for_service arquantix-redis)"
  if [[ -n "$_cdb" ]] && docker exec "$_cdb" pg_isready -U arquantix >/dev/null 2>&1; then
    line "  ${GRN}DB${RST}   pg_isready → OK (hôte DB_PORT=${DB_PORT})"
  elif [[ -n "$_cdb" ]]; then
    line "  ${RED}DB${RST}   pg_isready → ${RED}fail${RST}"
  else
    line "  ${RED}DB${RST}   conteneur absent"
  fi
  if [[ -n "$_crd" ]] && docker exec "$_crd" redis-cli ping 2>/dev/null | grep -qx PONG; then
    line "  ${GRN}Redis${RST} PING → PONG (hôte REDIS_PORT=${REDIS_PORT})"
  elif [[ -n "$_crd" ]]; then
    line "  ${RED}Redis${RST} PING → ${RED}fail${RST}"
  else
    line "  ${RED}Redis${RST} conteneur absent"
  fi
  hr

  # --- Warnings ---
  line "${BLD}Warnings${RST}"
  _warn=0
  _legn="$(docker ps -q --filter "label=com.docker.compose.project=arquantix" 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "${_legn:-0}" -gt 0 ]]; then
    line "  ${YLW}!${RST} Conteneurs legacy (projet compose « arquantix ») : ${_legn} — ne pas confondre avec recovery"
    _warn=1
  fi
  if [[ -n "$CPN_ENV" ]] && [[ "$CPN_ENV" != "$EXPECTED_PROJ" ]]; then
    line "  ${YLW}!${RST} COMPOSE_PROJECT_NAME dans .env = ${CPN_ENV} (référence doc : ${EXPECTED_PROJ})"
    _warn=1
  fi
  if [[ -n "$ACF_ENV" ]] && [[ "$ACF_ENV" != "$EXPECTED_CF" ]]; then
    line "  ${YLW}!${RST} ARQUANTIX_COMPOSE_FILE dans .env = ${ACF_ENV} (référence doc : ${EXPECTED_CF})"
    _warn=1
  fi
  if command -v curl >/dev/null 2>&1 && command -v lsof >/dev/null 2>&1; then
    if ! curl -sf --max-time 2 "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
      if lsof -nP -iTCP:"$API_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
        line "  ${YLW}!${RST} Port ${API_PORT} : listener présent mais /health échoue (autre processus ou API pas prête ?)"
        _warn=1
      fi
    fi
  fi
  if [[ "$_warn" -eq 0 ]]; then
    line "  ${GRN}Aucun avertissement détecté (heuristiques locales).${RST}"
  fi
  hr
  line "${DIM}Lecture seule — \`make doctor\` pour diagnostic, \`make doctor-fix\` pour correctifs sûrs.${RST}"
  echo ""
}

run_watch() {
  local tick=0
  while true; do
    STATUS_TICK=$tick
    if [[ -t 1 ]]; then
      clear 2>/dev/null || true
    else
      echo ""
      echo "======== refresh #${tick} ========"
    fi
    print_block
    tick=$((tick + 1))
    sleep "$REFRESH_SEC"
  done
}

if [[ "$WATCH" == "1" ]]; then
  run_watch
else
  print_block
fi
