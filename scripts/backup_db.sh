#!/usr/bin/env bash
# Sauvegarde logique de la base métier (pg_dump custom format) — ne modifie pas la DB.
# Sortie : $HOME/backups/arquantix_<DB_NAME>_YYYYMMDD_HHMMSS.dump
#
# Usage :
#   bash scripts/backup_db.sh              # auto : projet lu dans .env.arquantix (défaut recovery) ou recovery explicite
#   bash scripts/backup_db.sh official     # force le projet « officiel » = COMPOSE_PROJECT_NAME + ARQUANTIX_COMPOSE_FILE
#   bash scripts/backup_db.sh recovery     # force ARQUANTIX_RECOVERY_PROJECT (alias si identique à official)
#
# Variables : ARQUANTIX_RECOVERY_PROJECT (défaut arquantixrecovery) — aligné Makefile.arquantix
#
# Rotation : conserve les 20 derniers dumps pour ce DB_NAME dans $HOME/backups.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=arquantix_compose_lib.sh
source "$REPO_ROOT/scripts/arquantix_compose_lib.sh"
arquantix_lib_set_root "$REPO_ROOT"

MODE="${1:-auto}"
case "$MODE" in
  auto|official|recovery) ;;
  -h|--help)
    grep '^#' "$0" | grep -v '^#!' | sed 's/^# //' | head -20
    exit 0
    ;;
  *)
    echo "Usage: $0 [auto|official|recovery]" >&2
    exit 2
    ;;
esac

ENV_FILE="$REPO_ROOT/.env.arquantix"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Fichier manquant : $ENV_FILE" >&2
  exit 1
fi

DB_NAME="$( (grep -E '^[[:space:]]*DB_NAME=' "$ENV_FILE" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
[[ -z "$DB_NAME" ]] && DB_NAME="arquantix"

run_dump() {
  local label="$1"
  shift
  echo "→ Dump FC (${label}) de la base « ${DB_NAME} » vers ${OUT}"
  "$@" >"$OUT"
}

OUT_DIR="${HOME}/backups"
mkdir -p "$OUT_DIR"
TS="$(date +%Y%m%d_%H%M%S)"
SAFE_NAME="$(printf '%s' "$DB_NAME" | tr -cd '[:alnum:]_-')"
[[ -z "$SAFE_NAME" ]] && SAFE_NAME="db"
OUT="${OUT_DIR}/arquantix_${SAFE_NAME}_${TS}.dump"

if [[ "$MODE" == "official" ]]; then
  [[ -z "$(arquantix_cid_for_service arquantix-db)" ]] && {
    echo "Mode official : le service arquantix-db du projet « $(arquantix_expected_compose_project) » n’est pas running." >&2
    echo "Lance : make -f Makefile.arquantix arquantix-up" >&2
    exit 1
  }
  run_dump "compose (.env.arquantix)" arquantix_compose_exec arquantix-db pg_dump -U arquantix -Fc -d "$DB_NAME"
elif [[ "$MODE" == "recovery" ]]; then
  [[ -z "$(arquantix_cid_for_service_recovery arquantix-db)" ]] && {
    echo "Mode recovery : arquantix-db (projet $(arquantix_recovery_compose_project)) n’est pas running." >&2
    echo "Lance : make -f Makefile.arquantix arquantix-up (alias recovery-up)" >&2
    exit 1
  }
  run_dump "compose recovery ($(arquantix_recovery_compose_project))" arquantix_compose_exec_recovery arquantix-db pg_dump -U arquantix -Fc -d "$DB_NAME"
else
  # auto
  if [[ -n "$(arquantix_cid_for_service arquantix-db)" ]]; then
    run_dump "auto → projet .env.arquantix" arquantix_compose_exec arquantix-db pg_dump -U arquantix -Fc -d "$DB_NAME"
  elif [[ -n "$(arquantix_cid_for_service_recovery arquantix-db)" ]]; then
    echo "! Stack officielle absente — utilisation de la stack recovery ($(arquantix_recovery_compose_project))."
    run_dump "auto → recovery" arquantix_compose_exec_recovery arquantix-db pg_dump -U arquantix -Fc -d "$DB_NAME"
  else
    echo "Aucun conteneur arquantix-db running (ni officiel ni recovery)." >&2
    echo "Lance : make -f Makefile.arquantix arquantix-up" >&2
    exit 1
  fi
fi

echo "✓ Fichier écrit : $OUT"

# Rotation simple : garder les 20 derniers dumps pour ce préfixe
if ls -t "$OUT_DIR"/arquantix_"${SAFE_NAME}"_*.dump >/dev/null 2>&1; then
  _n_rm="$(ls -t "$OUT_DIR"/arquantix_"${SAFE_NAME}"_*.dump | tail -n +21 | wc -l | tr -d ' ')"
  if [[ "${_n_rm:-0}" -gt 0 ]]; then
    ls -t "$OUT_DIR"/arquantix_"${SAFE_NAME}"_*.dump | tail -n +21 | xargs rm -f
    printf '→ Rotation : %s fichier(s) ancien(s) supprimé(s) dans %s.\n' "$_n_rm" "$OUT_DIR"
  fi
fi
