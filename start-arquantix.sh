#!/usr/bin/env bash
# =============================================================================
# Vancelian / Arquantix — démarrage complet de la stack locale
# (équivalent au flux « boot » historique sous OneDrive : DB + API + Web + WS)
#
# Usage (à la racine du dépôt vancelian-app) :
#   ./start-arquantix.sh
#   chmod +x start-arquantix.sh   # une fois si besoin
#
# Prérequis : Docker Desktop (pour PostgreSQL + Redis), Node, Python 3.
# Arrêt       : services/arquantix/scripts/arquantix-stop.sh  ou  make stop
#
# Variables (optionnel) :
#   ARQUANTIX_AUTO_FREE_PORTS=1  — libère 8000/3000 si occupés par un autre processus (défaut via boot)
#   ARQUANTIX_SKIP_DOCKER=1      — ne pas lancer docker compose (DB/Redis déjà là)
# =============================================================================
set -euo pipefail

export ARQUANTIX_AUTO_FREE_PORTS="${ARQUANTIX_AUTO_FREE_PORTS:-1}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

ENV_ARQ="$ROOT/.env.arquantix"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}ℹ${NC} $1"; }
ok() { echo -e "${GREEN}✅${NC} $1"; }
warn() { echo -e "${YELLOW}⚠️${NC} $1"; }
err() { echo -e "${RED}❌${NC} $1"; }

if [[ -f "$ENV_ARQ" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ENV_ARQ"
  set +a
fi

COMPOSE_FILE="${ROOT}/${ARQUANTIX_COMPOSE_FILE:-docker-compose.arquantix-recovery.yml}"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║  VANCELIAN — DÉMARRAGE STACK ARQUANTIX (DB + Redis + API + Web + WS)    ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

export ARQUANTIX_SKIP_DOCKER=0

# Le script exige un daemon joignable (docker info OK), pas seulement le binaire docker.
if command -v docker >/dev/null 2>&1; then
  if ! docker info >/dev/null 2>&1; then
    warn "Docker est installé mais le démon ne répond pas (Docker Desktop arrêté ou en cours de démarrage)."
    warn "Démarrez Docker Desktop et attendez l’icône « vert » puis relancez ce script."
    export ARQUANTIX_SKIP_DOCKER=1
  elif [[ -f "$COMPOSE_FILE" ]] && [[ -f "$ENV_ARQ" ]]; then
    _cpn="$( (grep -E '^[[:space:]]*COMPOSE_PROJECT_NAME=' "$ENV_ARQ" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    _cpn="${_cpn:-arquantixrecovery}"
    info "Docker : démarrage arquantix-db + arquantix-redis (projet compose ${_cpn})…"
    if docker compose --project-name "$_cpn" --env-file "$ENV_ARQ" -f "$COMPOSE_FILE" up -d --remove-orphans arquantix-db arquantix-redis; then
      info "Attente PostgreSQL (pg_isready, max ~90s)…"
      DB_USER="${DB_USER:-arquantix}"
      for _ in $(seq 1 90); do
        if docker compose --project-name "$_cpn" --env-file "$ENV_ARQ" -f "$COMPOSE_FILE" exec -T arquantix-db pg_isready -U "$DB_USER" >/dev/null 2>&1; then
          ok "PostgreSQL prêt (service arquantix-db)"
          break
        fi
        sleep 1
      done
      if docker compose --project-name "$_cpn" --env-file "$ENV_ARQ" -f "$COMPOSE_FILE" exec -T arquantix-db pg_isready -U "$DB_USER" >/dev/null 2>&1; then
        ok "Redis : service arquantix-redis démarré (port hôte ${REDIS_PORT:-6379})"
      else
        warn "PostgreSQL ne répond pas après 90s."
        if docker compose --project-name "$_cpn" --env-file "$ENV_ARQ" -f "$COMPOSE_FILE" ps -q arquantix-db | grep -q .; then
          warn "Dernières lignes : docker compose … logs arquantix-db"
          docker compose --project-name "$_cpn" --env-file "$ENV_ARQ" -f "$COMPOSE_FILE" logs arquantix-db 2>&1 | tail -12 | sed 's/^/      /' || true
        else
          warn "Service arquantix-db introuvable — vérifiez : docker compose --project-name ${_cpn} … ps -a"
        fi
        export ARQUANTIX_SKIP_DOCKER=1
      fi
    else
      warn "docker compose a échoué (réseau / images / port DB déjà pris ?). Suite avec ARQUANTIX_SKIP_DOCKER=1."
      if command -v lsof >/dev/null 2>&1; then
        _dp="${DB_PORT:-5443}"
        if lsof -iTCP:"$_dp" -sTCP:LISTEN >/dev/null 2>&1; then
          warn "Le port hôte $_dp est déjà utilisé — libérez-le ou changez DB_PORT dans .env.arquantix"
          lsof -iTCP:"$_dp" -sTCP:LISTEN | sed 's/^/      /' || true
        fi
      fi
      export ARQUANTIX_SKIP_DOCKER=1
    fi
  else
    warn "Fichier compose (${COMPOSE_FILE}) ou .env.arquantix absent — saut du démarrage Docker."
    export ARQUANTIX_SKIP_DOCKER=1
  fi
else
  warn "Commande « docker » introuvable. Installez Docker Desktop ou assurez-vous que PostgreSQL tourne sur DATABASE_URL (souvent localhost:${DB_PORT:-5443})."
  export ARQUANTIX_SKIP_DOCKER=1
fi

echo ""
info "Lancement du boot Arquantix (API 8000, Web 3000, Binance WS)…"
echo ""

exec bash "$ROOT/services/arquantix/scripts/arquantix-boot.sh"
