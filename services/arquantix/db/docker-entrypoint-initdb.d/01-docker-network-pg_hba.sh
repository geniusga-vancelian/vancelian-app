#!/usr/bin/env bash
# Exécuté une seule fois à l’init du data directory (nouveau volume).
# Autorise les connexions depuis le réseau Docker (API, web, etc.), pas seulement localhost.
set -euo pipefail
: "${PGDATA:?}"
if ! grep -qE '^[[:space:]]*host[[:space:]]+all[[:space:]]+all[[:space:]]+all' "$PGDATA/pg_hba.conf" 2>/dev/null; then
  echo "host all all all scram-sha-256" >>"$PGDATA/pg_hba.conf"
fi
