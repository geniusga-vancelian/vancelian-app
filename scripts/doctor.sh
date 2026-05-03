#!/usr/bin/env bash
#
# Arquantix — doctor DX (diagnostic lisible, lecture seule).
# Ne fait jamais : down -v, volume prune, suppression de données.
#
# Usage : bash scripts/doctor.sh   (depuis la racine du dépôt)
#
set -u

START_TS=$(date +%s)
trap 'END_TS=$(date +%s); echo "⏱️ Completed in $((END_TS - START_TS))s"' EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT" || exit 1

# Bonus : éviter les faux diagnostics si le daemon Docker n’est pas prêt
if ! command -v docker >/dev/null 2>&1; then
  echo "❌ docker CLI not found in PATH"
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "❌ Docker is not running"
  echo "👉 Fix: open Docker Desktop (Mac):"
  echo "   open -a Docker"
  exit 1
fi

# shellcheck source=arquantix_compose_lib.sh
source "$SCRIPT_DIR/arquantix_compose_lib.sh"
arquantix_lib_set_root "$REPO_ROOT"

ENV_FILE="$REPO_ROOT/.env.arquantix"

ERROR_COUNT=0
WARNING_COUNT=0

RED='\033[1;31m'
GRN='\033[1;32m'
YLW='\033[1;33m'
BLD='\033[1m'
RST='\033[0m'

line() { printf '%s\n' "$*"; }
ok() { line "${GRN}[OK]${RST} $*"; }
warning() { line "${YLW}[WARNING]${RST} $*"; WARNING_COUNT=$((WARNING_COUNT + 1)); }
error() { line "${RED}[ERROR]${RST} $*"; ERROR_COUNT=$((ERROR_COUNT + 1)); }

hdr() { printf '\n%s━━ %s ━━%s\n' "$BLD" "$*" "$RST"; }

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

hdr "Arquantix doctor (DX)"
line "REPO_ROOT=$REPO_ROOT"

# --- Docker (daemon déjà vérifié en amont) ---
hdr "Docker"
ok "docker CLI présent"
ok "docker daemon répond"
_STACK_PROJ="$(arquantix_expected_compose_project)"
_STACK_CF="$(arquantix_compose_file)"
echo "🔧 Project: ${_STACK_PROJ}"
echo "📦 Compose: ${_STACK_CF}"

# --- .env.arquantix ---
hdr "Fichier .env.arquantix"
if [[ ! -f "$ENV_FILE" ]]; then
  error "Fichier manquant : $ENV_FILE"
else
  ok "Présent : $ENV_FILE"
fi

EXPECTED_PROJ="arquantixrecovery"
EXPECTED_FILE="docker-compose.arquantix-recovery.yml"
EXPECTED_DB_PORT="5443"
EXPECTED_DB_NAME="arquantix_fresh"

CPN="$(read_env_kv COMPOSE_PROJECT_NAME "")"
ACF="$(read_env_kv ARQUANTIX_COMPOSE_FILE "")"
DBN="$(read_env_kv DB_NAME "")"
DBP="$(read_env_kv DB_PORT "")"

hdr "Alignement attendu (stack officielle locale)"
if [[ -n "$CPN" ]]; then
  if [[ "$CPN" == "$EXPECTED_PROJ" ]]; then
    ok "COMPOSE_PROJECT_NAME=$CPN"
  else
    warning "COMPOSE_PROJECT_NAME=$CPN (attendu : $EXPECTED_PROJ pour ce dépôt)"
  fi
else
  warning "COMPOSE_PROJECT_NAME absent (Makefile défaut : $EXPECTED_PROJ)"
fi

if [[ -n "$ACF" ]]; then
  if [[ "$ACF" == "$EXPECTED_FILE" ]]; then
    ok "ARQUANTIX_COMPOSE_FILE=$ACF"
  else
    warning "ARQUANTIX_COMPOSE_FILE=$ACF (attendu : $EXPECTED_FILE)"
  fi
else
  warning "ARQUANTIX_COMPOSE_FILE absent (défaut : $EXPECTED_FILE)"
fi

if [[ -n "$DBP" ]]; then
  if [[ "$DBP" == "$EXPECTED_DB_PORT" ]]; then
    ok "DB_PORT=$DBP"
  else
    warning "DB_PORT=$DBP (référence doc : $EXPECTED_DB_PORT)"
  fi
fi

if [[ -n "$DBN" ]]; then
  if [[ "$DBN" == "$EXPECTED_DB_NAME" ]]; then
    ok "DB_NAME=$DBN"
  else
    warning "DB_NAME=$DBN (référence doc : $EXPECTED_DB_NAME)"
  fi
fi

# --- Legacy namespace (détection seule) ---
hdr "Legacy (détection — aucune action)"
_legn="$(docker ps -q --filter "label=com.docker.compose.project=arquantix" 2>/dev/null | wc -l | tr -d ' ')"
if [[ "${_legn:-0}" -gt 0 ]]; then
  warning "Conteneurs encore visibles sous le projet legacy « arquantix » ($_legn) — ne pas mélanger avec la stack officielle (voir LOCAL_ENV_RUNBOOK.md)"
else
  ok "Aucun conteneur running sous le label projet « arquantix » (legacy)"
fi

# --- Services (running) ---
hdr "Services Compose (projet attendu : $(arquantix_expected_compose_project))"
SERVICES=(arquantix-db arquantix-redis arquantix-api arquantix-web)
for svc in "${SERVICES[@]}"; do
  cid="$(arquantix_cid_for_service "$svc")"
  if [[ -z "$cid" ]]; then
    error "Service non running : $svc"
  else
    st="$(docker inspect --format '{{.State.Status}}' "$cid" 2>/dev/null || echo "?")"
    if [[ "$st" == "running" ]]; then
      ok "$svc — running ($cid)"
    else
      error "$svc — état : $st"
    fi
  fi
done

# --- Health HTTP ---
hdr "Health HTTP"
if command -v curl >/dev/null 2>&1; then
  if curl -sf --max-time 5 "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
    ok "API GET /health → 200 (http://127.0.0.1:${API_PORT})"
  else
    error "API GET /health → échec (http://127.0.0.1:${API_PORT})"
  fi
  _wc="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 8 "http://127.0.0.1:${WEB_PORT}/" 2>/dev/null || echo 000)"
  if [[ "$_wc" == "200" ]]; then
    ok "Web GET / → ${_wc} (http://127.0.0.1:${WEB_PORT})"
  else
    warning "Web GET / → ${_wc} (attendu souvent 200 — http://127.0.0.1:${WEB_PORT})"
  fi
else
  warning "curl absent — health HTTP non vérifié"
fi

# --- DB + Redis dans les conteneurs ---
hdr "Postgres & Redis (conteneurs)"
_cdb="$(arquantix_cid_for_service arquantix-db)"
_crd="$(arquantix_cid_for_service arquantix-redis)"
if [[ -n "$_cdb" ]] && docker exec "$_cdb" pg_isready -U arquantix >/dev/null 2>&1; then
  ok "Postgres pg_isready (arquantix-db)"
else
  if [[ -n "$_cdb" ]]; then
    error "Postgres pg_isready échoue (arquantix-db)"
  else
    error "Conteneur arquantix-db absent"
  fi
fi

if [[ -n "$_crd" ]] && docker exec "$_crd" redis-cli ping 2>/dev/null | grep -qx PONG; then
  ok "Redis PING → PONG (arquantix-redis)"
else
  if [[ -n "$_crd" ]]; then
    error "Redis ne répond pas PONG (arquantix-redis)"
  else
    error "Conteneur arquantix-redis absent"
  fi
fi

# --- Réseau recovery ---
hdr "Réseau"
_net="arquantix_recovery_network"
if docker network inspect "$_net" >/dev/null 2>&1; then
  ok "Réseau présent : $_net"
  _api="$(arquantix_cid_for_service arquantix-api)"
  if [[ -n "$_api" ]]; then
    if docker inspect "$_api" --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null | grep -q "$_net"; then
      ok "arquantix-api attaché à $_net"
    else
      warning "arquantix-api : pas vu sur $_net (inspect réseau)"
    fi
  fi
else
  warning "Réseau $_net absent ou inaccessible (stack pas créée ?)"
fi

_dns_ok=0
_cweb="$(arquantix_cid_for_service arquantix-web)"
if [[ -n "$_cdb" && -n "$_cweb" ]]; then
  if docker exec "$_cweb" sh -c 'command -v nc >/dev/null 2>&1 && nc -zvw2 arquantix-db 5432' >/dev/null 2>&1; then
    ok "TCP arquantix-db:5432 joignable depuis arquantix-web (nc)"
    _dns_ok=1
  elif docker exec "$_cweb" getent hosts arquantix-db >/dev/null 2>&1; then
    ok "Résolution arquantix-db OK depuis arquantix-web (getent)"
    _dns_ok=1
  fi
fi
if [[ "$_dns_ok" -eq 0 ]] && [[ -n "$_cweb" ]] && [[ -n "$_cdb" ]]; then
  warning "Test connectivité arquantix-db depuis web non concluant (nc/getent selon image)"
fi

# --- Résumé ---
hdr "Résumé"
line "Compteurs : ERROR=$ERROR_COUNT | WARNING=$WARNING_COUNT"

if [[ "$ERROR_COUNT" -gt 0 ]]; then
  echo "❌ CRITICAL — action required"
  echo ""
  echo "👉 Suggested fix: run 'make doctor-fix'"
  exit 1
fi
if [[ "$WARNING_COUNT" -gt 0 ]]; then
  echo "⚠️ WARNING — system usable but not clean"
  exit 0
fi
echo "✅ SAFE — everything is operational"
exit 0
