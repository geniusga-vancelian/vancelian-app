#!/usr/bin/env bash
#
# Lot 4 — détecte :3001 ou :5433 dans les fichiers d’environnement Arquantix (hors commentaires #).
# Lecture seule. Usage :
#   bash scripts/arquantix_lot4_env_guard.sh
#   make -f Makefile.arquantix local-env-guard
#
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

RED='\033[1;31m'
YLW='\033[1;33m'
BLD='\033[1m'
RST='\033[0m'

line() { printf '%s\n' "$*"; }
warn() { line "${YLW}[WARNING]${RST} $*"; }

ENV_FILES=(
  "$REPO_ROOT/.env.arquantix"
  "$REPO_ROOT/services/arquantix/web/.env.local"
  "$REPO_ROOT/services/arquantix/api/.env.local"
  "$REPO_ROOT/.env"
)

# Lignes non vides, non commentaires # en première position — recherche ports dépréciés.
line_has_deprecated_port() {
  local f="$1"
  [[ ! -f "$f" ]] && return 1
  grep -v '^\s*#' "$f" 2>/dev/null | grep -v '^\s*$' | grep -E ':3001|:5433' >/dev/null 2>&1
}

FOUND=0
for f in "${ENV_FILES[@]}"; do
  if line_has_deprecated_port "$f"; then
    rel="${f#$REPO_ROOT/}"
    warn "Fichier ${BLD}$rel${RST} contient ${BLD}:3001${RST} ou ${BLD}:5433${RST} — hors convention actuelle (web ${BLD}:3000${RST}, Postgres hôte typ. ${BLD}:5443${RST}). Voir docs/arquantix/LOCAL_SETUP.md"
    FOUND=1
  fi
done

if [[ "$FOUND" -eq 0 ]]; then
  line "${BLD}[OK]${RST} Aucun :3001 / :5433 détecté dans les fichiers env listés."
fi

exit 0
