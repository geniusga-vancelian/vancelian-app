#!/usr/bin/env bash
# Vérifie la présence des clés critiques dans .env.arquantix et, si Docker est up,
# compare DATABASE_URL / REDIS_URL dans les conteneurs API (lecture seule).
# Usage : bash scripts/check_env_consistency.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENVF="$REPO_ROOT/.env.arquantix"
ERR=0

red() { printf '\033[1;31m%s\033[0m\n' "$*"; }
grn() { printf '\033[1;32m%s\033[0m\n' "$*"; }
ylw() { printf '\033[1;33m%s\033[0m\n' "$*"; }

echo "=== check_env_consistency — $ENVF ==="
if [[ ! -f "$ENVF" ]]; then
  red "Fichier manquant : $ENVF"
  exit 1
fi

need() {
  local k="$1"
  if ! grep -qE "^[[:space:]]*${k}=" "$ENVF"; then
    red "MANQUANT : $k"
    ERR=1
  else
    grn "OK $k"
  fi
}

for k in COMPOSE_PROJECT_NAME ARQUANTIX_COMPOSE_FILE DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD REDIS_URL REDIS_PORT API_PORT WEB_PORT JWT_SECRET_KEY; do
  need "$k"
done

echo ""
echo "=== Valeurs lues (échantillon) ==="
grep -E '^[[:space:]]*(COMPOSE_PROJECT_NAME|ARQUANTIX_COMPOSE_FILE|DB_HOST|DB_PORT|DB_NAME|API_PORT|WEB_PORT|REDIS_URL)=' "$ENVF" | sed 's/=.*/=…/' || true

# shellcheck source=arquantix_compose_lib.sh
source "$REPO_ROOT/scripts/arquantix_compose_lib.sh"
arquantix_lib_set_root "$REPO_ROOT"

api_exec() {
  if [[ -n "$(arquantix_cid_for_service arquantix-api)" ]]; then
    arquantix_compose_exec arquantix-api "$@"
  elif [[ -n "$(arquantix_cid_for_service_recovery arquantix-api)" ]]; then
    arquantix_compose_exec_recovery arquantix-api "$@"
  else
    return 127
  fi
}

web_exec() {
  if [[ -n "$(arquantix_cid_for_service arquantix-web)" ]]; then
    arquantix_compose_exec arquantix-web "$@"
  elif [[ -n "$(arquantix_cid_for_service_recovery arquantix-web)" ]]; then
    arquantix_compose_exec_recovery arquantix-web "$@"
  else
    return 127
  fi
}

echo ""
echo "=== Runtime conteneur API (si running) ==="
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  if [[ -n "$(arquantix_cid_for_service arquantix-api)" ]]; then
    grn "Conteneur API : projet Compose officiel ($(arquantix_expected_compose_project))"
  elif [[ -n "$(arquantix_cid_for_service_recovery arquantix-api)" ]]; then
    ylw "Conteneur API : stack recovery ($(arquantix_recovery_compose_project)) — pas le projet officiel."
  fi
  set +e
  _du="$(api_exec printenv DATABASE_URL 2>/dev/null | tr -d '\r')"
  _ru="$(api_exec printenv REDIS_URL 2>/dev/null | tr -d '\r')"
  _bu="$(web_exec printenv BACKEND_API_URL 2>/dev/null | tr -d '\r')"
  _burl="$(web_exec printenv BACKEND_URL 2>/dev/null | tr -d '\r')"
  set -e
  if [[ -z "$_du" && -z "$(arquantix_cid_for_service arquantix-api)$(arquantix_cid_for_service_recovery arquantix-api)" ]]; then
    ylw "Conteneur arquantix-api absent — impossible de vérifier l’env injecté."
  else
    if echo "$_du" | grep -qE 'arquantix-db:5432'; then
      grn "API DATABASE_URL contient arquantix-db:5432"
    else
      ylw "API DATABASE_URL inattendu (attendu host arquantix-db:5432) : ${_du:0:120}"
    fi
    if echo "$_ru" | grep -q 'arquantix-redis'; then
      grn "API REDIS_URL pointe vers arquantix-redis"
    else
      ylw "API REDIS_URL : $_ru"
    fi
  fi

  echo ""
  echo "=== Runtime conteneur Web (BACKEND_*) ==="
  if [[ -n "$(arquantix_cid_for_service arquantix-web)" ]]; then
    grn "Conteneur Web : projet Compose officiel"
  elif [[ -n "$(arquantix_cid_for_service_recovery arquantix-web)" ]]; then
    ylw "Conteneur Web : stack recovery uniquement."
  fi
  if [[ -n "$_bu" || -n "$_burl" ]]; then
    if echo "$_bu$_burl" | grep -q 'arquantix-api'; then
      grn "Web BACKEND_* pointe vers arquantix-api"
    else
      ylw "Web BACKEND_API_URL=$_bu BACKEND_URL=$_burl"
    fi
  else
    ylw "arquantix-web absent ou BACKEND_* non lisibles."
  fi

else
  ylw "Docker indisponible."
fi

exit "$ERR"
