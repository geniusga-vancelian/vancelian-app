#!/usr/bin/env bash
# Répare pg_hba lorsque :
#   • le fichier est tronqué / corrompu (octets NUL) → seules des règles localhost existent ;
#   • la règle « host all all all » manque pour le réseau Docker.
# Symptôme côté API : alembic / uvicorn échouent avec
#   FATAL: no pg_hba.conf entry for host "…", user "arquantix", …, no encryption
# et arquantix-api reste en « Restarting ».
#
# Usage (Docker actif, service arquantix-db qui tourne) — depuis la racine du dépôt :
#   bash services/arquantix/tooling/fix_arquantix_pg_hba.sh
#
# ⚠️  Utilise le fichier compose actif depuis .env.arquantix (ARQUANTIX_COMPOSE_FILE), pas le compose legacy seul.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
# shellcheck source=../../../scripts/arquantix_compose_lib.sh
source "$REPO_ROOT/scripts/arquantix_compose_lib.sh"
arquantix_lib_set_root "$REPO_ROOT"

HBA="/var/lib/postgresql/data/pg_hba.conf"

_cf="$(arquantix_compose_file)"
(cd "$REPO_ROOT" && docker compose --project-name "$(arquantix_expected_compose_project)" \
  --env-file .env.arquantix -f "$REPO_ROOT/$_cf" exec -T -u postgres arquantix-db sh -c "
  tr -d '\\000' < $HBA > /tmp/pg_hba.clean
  if ! grep -qE '^[[:space:]]*host[[:space:]]+all[[:space:]]+all[[:space:]]+all[[:space:]]+scram-sha-256' /tmp/pg_hba.clean; then
    echo 'host all all all scram-sha-256' >> /tmp/pg_hba.clean
  fi
  mv /tmp/pg_hba.clean $HBA
")
arquantix_compose_exec arquantix-db psql -U arquantix -d postgres -c "SELECT pg_reload_conf();"
echo "OK — redémarre l’API : docker compose … restart arquantix-api (Makefile / même projet que .env.arquantix)"
