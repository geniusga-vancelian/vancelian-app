#!/usr/bin/env bash
# Relance toute la stack: arquantix-db (Docker) + API (8000) + Web (3000).
# À lancer depuis un terminal (Docker et ports doivent être accessibles).
# Usage: ./scripts/arquantix-relance-tout.sh

set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="$(cd "$BASE/../.." && pwd)"   # vancelian-app

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║     ARQUANTIX — RELANCE TOUTE LA STACK                                   ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# 1) Démarrer arquantix-db si docker-compose existe
_cf="docker-compose.arquantix-recovery.yml"
_cpn="arquantixrecovery"
[[ -f "$ROOT/.env.arquantix" ]] && _cf="$( (grep -E '^[[:space:]]*ARQUANTIX_COMPOSE_FILE=' "$ROOT/.env.arquantix" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
[[ -n "$_cf" ]] || _cf="docker-compose.arquantix-recovery.yml"
[[ -f "$ROOT/.env.arquantix" ]] && _cpn="$( (grep -E '^[[:space:]]*COMPOSE_PROJECT_NAME=' "$ROOT/.env.arquantix" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
[[ -n "$_cpn" ]] || _cpn="arquantixrecovery"
if [[ -f "$ROOT/$_cf" ]]; then
  echo "📦 Démarrage arquantix-db (projet $_cpn, compose $_cf)…"
  if [[ -f "$ROOT/.env.arquantix" ]]; then
    (cd "$ROOT" && docker compose --project-name "$_cpn" --env-file "$ROOT/.env.arquantix" -f "$ROOT/$_cf" up -d arquantix-db) || true
  else
    (cd "$ROOT" && docker compose --project-name "$_cpn" -f "$ROOT/$_cf" up -d arquantix-db) || true
  fi
  echo "   Attente 15s que la DB soit prête..."
  sleep 15
  echo ""
fi

# 2) Boot classique (arrêt préalable + démarrage)
cd "$BASE"
./scripts/arquantix-stop.sh 2>/dev/null || true
./scripts/arquantix-boot.sh
