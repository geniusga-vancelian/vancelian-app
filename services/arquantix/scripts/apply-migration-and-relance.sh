#!/usr/bin/env bash
# 1) Applique la migration Alembic (011 chatbot)
# 2) Arrête API + Web
# 3) Relance toute la stack (DB si besoin, API 8000, Web 3000)
# À lancer depuis la racine du projet: ./scripts/apply-migration-and-relance.sh

set -euo pipefail

BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE"

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║     MIGRATION + RELANCE (front, back, API)                               ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# 1) Migration
echo "► [1/3] Migration: alembic upgrade head"
cd "$BASE/api"
if [[ -x "$BASE/api/.venv/bin/python" ]]; then
  PY="$BASE/api/.venv/bin/python"
else
  PY="python3"
fi
$PY -m alembic upgrade head || { echo "❌ Migration échouée (DB sur localhost:5443 ?)."; exit 1; }
echo "   ✓ Migration OK"
echo ""

# 2) Stop
echo "► [2/3] Arrêt API + Web"
cd "$BASE"
./scripts/arquantix-stop.sh 2>/dev/null || true
echo ""

# 3) Relance (DB + API + Web)
echo "► [3/3] Relance: make boot (DB + API + Web)"
./scripts/arquantix-boot.sh

echo ""
echo "✅ Migration appliquée, front (Web 3000), back et API (8000) relancés."
