#!/usr/bin/env bash
#
# Arquantix — corrections sûres uniquement (pas de down -v, pas de prune volumes, pas de reset DB).
#
# Autorisé : compose up -d --remove-orphans, restart ciblé api ou web.
#
# Usage :
#   bash scripts/doctor_fix.sh
#   DRY_RUN=1 bash scripts/doctor_fix.sh    # ou : DRY_RUN=1 make -f Makefile.arquantix doctor-fix
#
set -u

DRY_RUN="${DRY_RUN:-0}"

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[DRY RUN] '
    printf '%q ' "$@"
    echo
  else
    "$@"
  fi
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT" || exit 1

# shellcheck source=arquantix_compose_lib.sh
source "$SCRIPT_DIR/arquantix_compose_lib.sh"
arquantix_lib_set_root "$REPO_ROOT"

ENV_FILE="$REPO_ROOT/.env.arquantix"

BLD='\033[1m'
RST='\033[0m'
GRN='\033[1;32m'
YLW='\033[1;33m'

line() { printf '%s\n' "$*"; }

read_env_kv() {
  local key="$1"
  local def="${2:-}"
  [[ -f "$ENV_FILE" ]] || { echo "$def"; return; }
  local v
  v="$( (grep -E "^[[:space:]]*${key}=" "$ENV_FILE" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -n "$v" ]] && echo "$v" || echo "$def"
}

API_PORT="$(read_env_kv API_PORT 8000)"
WEB_PORT="$(read_env_kv WEB_PORT 3000)"

proj="$(arquantix_expected_compose_project)"
cf="$(arquantix_compose_file)"
COMPOSE=(docker compose --project-name "$proj" --env-file "$ENV_FILE" -f "$REPO_ROOT/$cf")

line "${BLD}━━ Arquantix doctor-fix (actions sûres) ━━${RST}"
if [[ "$DRY_RUN" == "1" ]]; then
  line "${YLW}[DRY RUN] Aucune modification Docker — affichage des commandes uniquement${RST}"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  line "${YLW}Abandon : créez .env.arquantix (ex. cp .env.arquantix.example .env.arquantix).${RST}"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  line "${YLW}Abandon : Docker n'est pas prêt.${RST}"
  exit 1
fi

line "→ ${GRN}compose up -d --remove-orphans${RST} (idempotent, volumes inchangés)"
run "${COMPOSE[@]}" up -d --remove-orphans

line "→ Attente courte (démarrage / Alembic)…"
if [[ "$DRY_RUN" != "1" ]]; then
  sleep 6
else
  echo "[DRY RUN] sleep 6"
fi

_api_ok=0
_web_ok=0
if command -v curl >/dev/null 2>&1; then
  if curl -sf --max-time 5 "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
    _api_ok=1
  fi
  _wc="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 "http://127.0.0.1:${WEB_PORT}/" 2>/dev/null || echo 000)"
  [[ "$_wc" == "200" ]] && _web_ok=1
fi

if [[ "$_api_ok" -eq 0 ]]; then
  line "→ API /health encore KO — ${GRN}restart arquantix-api${RST} uniquement"
  run "${COMPOSE[@]}" restart arquantix-api
  if [[ "$DRY_RUN" != "1" ]]; then
    sleep 8
  else
    echo "[DRY RUN] sleep 8"
  fi
  if command -v curl >/dev/null 2>&1; then
    curl -sf --max-time 5 "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1 && _api_ok=1
  fi
fi

if [[ "$_api_ok" -eq 1 ]] && [[ "$_web_ok" -eq 0 ]]; then
  line "→ API OK mais Web anormal — ${GRN}restart arquantix-web${RST} uniquement"
  run "${COMPOSE[@]}" restart arquantix-web
  if [[ "$DRY_RUN" != "1" ]]; then
    sleep 12
  else
    echo "[DRY RUN] sleep 12"
  fi
fi

line ""
if [[ "$DRY_RUN" == "1" ]]; then
  echo "[DRY RUN] bash scripts/doctor.sh"
  exit 0
fi
line "${BLD}Relance du diagnostic :${RST} bash scripts/doctor.sh"
bash "$SCRIPT_DIR/doctor.sh"
exit $?
