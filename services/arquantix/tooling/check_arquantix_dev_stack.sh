#!/usr/bin/env bash
# Santé stack dev — aligné sur le mode par défaut actuel :
#   • API FastAPI en Docker sur l’hôte (API_PORT, souvent 8000) — vérité = GET /health
#   • Next local (npm) sur NEXT_LOCAL_PORT (souvent 3000) — peut être surchargé par WEB_PORT=… en ligne de commande
#   • Next Docker (arquantix-web) sur le port publié WEB_PORT du .env.arquantix (souvent 3000) — optionnel
#   • Postgres : conteneur arquantix-db (pg_isready) et/ou port hôte DB_PORT (Prisma depuis l’hôte)
#
# Usage :
#   bash services/arquantix/tooling/check_arquantix_dev_stack.sh
#   WEB_PORT=3000 bash …   # force le port Next *local* testé (comme dev-reset.sh)
# ou : make -f Makefile.arquantix arquantix-check
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
ENV_FILE="$REPO_ROOT/.env.arquantix"

# Ligne de commande prime sur le fichier (ex. WEB_PORT=3000 depuis dev-reset pour Next npm)
_saved_next_local="${WEB_PORT-}"
_saved_api="${API_PORT-}"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

# Port publié par Docker pour arquantix-web (souvent 3000) — avant d’écraser WEB_PORT pour le test Next local
DOCKER_WEB_PORT="${WEB_PORT:-3000}"
# Next local à tester : argument explicite, sinon défaut 3000 (npm run dev)
if [ -n "${_saved_next_local}" ]; then
  NEXT_LOCAL_PORT="$_saved_next_local"
else
  NEXT_LOCAL_PORT="${NEXT_LOCAL_PORT:-3000}"
fi
# Ne jamais prendre PORT (shell/npm) pour l’API
if [ -n "${_saved_api}" ]; then
  API_PORT="$_saved_api"
fi
API_PORT="${API_PORT:-8000}"
DB_PORT="${DB_PORT:-5443}"
DB_USER="${DB_USER:-arquantix}"

# shellcheck source=../../../../scripts/arquantix_compose_lib.sh
source "$REPO_ROOT/scripts/arquantix_compose_lib.sh"
arquantix_lib_set_root "$REPO_ROOT"

# Même logique que scripts/dev-reset.sh — évite les sorties type « 000000 ».
curl_http_code() {
  local raw url="$1"
  raw="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 --max-time 12 "$url" 2>/dev/null || true)"
  raw="$(printf '%s' "$raw" | tr -cd '0-9')"
  printf '%.3s' "${raw}000"
}

red() { printf "\033[1;31m%s\033[0m\n" "$*"; }
green() { printf "\033[1;32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[1;33m%s\033[0m\n" "$*"; }
blue() { printf "\033[1;34m%s\033[0m\n" "$*"; }

blue "═══ Arquantix — santé stack dev ═══"
echo "REPO_ROOT=$REPO_ROOT"
echo "Mode attendu : API Docker → :${API_PORT} | Next local (npm) → :${NEXT_LOCAL_PORT} | Next Docker (optionnel) → :${DOCKER_WEB_PORT}"
echo ""

# --- 1) API FastAPI : même critère que scripts/dev-reset.sh (GET /health) ---
code_health="$(curl_http_code "http://127.0.0.1:${API_PORT}/health")"
# /docs : dernier code après redirections ; normalisé sur 3 chiffres
_raw_docs="$(curl -sS -L -o /dev/null -w '%{http_code}' --connect-timeout 2 --max-time 12 "http://127.0.0.1:${API_PORT}/docs" 2>/dev/null || true)"
code_docs="$(printf '%s' "$_raw_docs" | tr -cd '0-9')"
code_docs="$(printf '%.3s' "${code_docs}000")"

if [ "$code_health" = "200" ]; then
  green "✓ API FastAPI (Docker ou hôte) : GET /health → 200  (référence)"
else
  red "✗ API FastAPI : GET /health → ${code_health} (attendu 200)"
fi
if [ "$code_docs" = "200" ] || [ "$code_docs" = "307" ] || [ "$code_docs" = "308" ]; then
  green "✓ API : GET /docs → ${code_docs}"
elif [ "$code_health" = "200" ]; then
  yellow "? API : GET /docs → ${code_docs} — ignoré si /health est déjà OK (Swagger peut rediriger différemment)"
else
  yellow "? API : GET /docs → ${code_docs}"
fi
echo ""

# --- 2) PostgreSQL : d’abord le conteneur (réalité docker-compose), sinon port hôte (Prisma depuis l’hôte) ---
pg_note=""
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  _pi=0
  while [ "$_pi" -lt 5 ]; do
    if arquantix_compose_exec arquantix-db pg_isready -U "$DB_USER" >/dev/null 2>&1; then
      green "✓ PostgreSQL : service arquantix-db (pg_isready)"
      pg_note=ok
      break
    fi
    sleep 2
    _pi=$((_pi + 1))
  done
fi
if [ "$pg_note" != ok ] && command -v nc >/dev/null 2>&1; then
  if nc -z 127.0.0.1 "$DB_PORT" 2>/dev/null; then
    green "✓ PostgreSQL : TCP 127.0.0.1:${DB_PORT} (accès hôte pour Prisma / outils)"
    pg_note=ok
  fi
fi
if [ "$pg_note" != ok ]; then
  if [ "$code_health" = "200" ]; then
    yellow "? PostgreSQL : pg_isready + port hôte ${DB_PORT} non vérifiés — l’API joint la DB dans le réseau Docker ; pour Next local + Prisma, ouvrez le port hôte (docker-compose → DB_PORT)."
  else
    red "✗ PostgreSQL : inaccessible (conteneur ou 127.0.0.1:${DB_PORT})"
  fi
fi
echo ""

# --- 3) Next local (npm) : routes BFF ---
code_prof="$(curl_http_code "http://127.0.0.1:${NEXT_LOCAL_PORT}/api/mobile/flutter/profile")"
if [ "$code_prof" = "401" ]; then
  green "✓ Next local :${NEXT_LOCAL_PORT} — GET /api/mobile/flutter/profile → 401 (normal sans Bearer)"
elif [ "$code_prof" = "500" ]; then
  red "✗ Next local :${NEXT_LOCAL_PORT} — GET profile → 500 (souvent Prisma / DATABASE_URL vers 127.0.0.1:${DB_PORT})"
elif [ "$code_prof" = "000" ]; then
  yellow "? Next local :${NEXT_LOCAL_PORT} — pas de réponse (lance npm run dev ou vérifie le port)"
else
  yellow "? Next local :${NEXT_LOCAL_PORT} — GET profile → ${code_prof} (attendu 401 sans token si OK)"
fi
echo ""

# --- 4) Next Docker (arquantix-web) : seulement si port différent du Next local ---
if [ "$DOCKER_WEB_PORT" != "$NEXT_LOCAL_PORT" ]; then
  code_docker="$(curl_http_code "http://127.0.0.1:${DOCKER_WEB_PORT}/")"
  if [ "$code_docker" != "000" ] && [ "${#code_docker}" -eq 3 ]; then
    green "✓ Next Docker (arquantix-web) : http://127.0.0.1:${DOCKER_WEB_PORT}/ → HTTP ${code_docker}"
  else
    yellow "? Next Docker :${DOCKER_WEB_PORT} — pas de réponse (normal si tu n’utilises que Next npm sur :${NEXT_LOCAL_PORT})"
  fi
  echo ""
fi

yellow "Rappel Flutter : API_BASE_URL vers ce Next (ex. http://<LAN>:${NEXT_LOCAL_PORT})."
echo ""
