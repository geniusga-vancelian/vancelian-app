#!/usr/bin/env bash
#
# Arrêt propre : worker Binance WS + optionnellement la stack Docker Arquantix.
#
# Usage :
#   bash scripts/stop-arquantix.sh              # arrête uniquement le worker WS
#   bash scripts/stop-arquantix.sh --compose-down  # worker + make arquantix-down
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

COMPOSE_DOWN=0
for arg in "$@"; do
  case "$arg" in
    --compose-down) COMPOSE_DOWN=1 ;;
    -h|--help)
      echo "Usage: bash scripts/stop-arquantix.sh [--compose-down]"
      exit 0
      ;;
  esac
done

echo "═══ Arquantix — arrêt ═══"

if pgrep -fl run_binance_ws_ingestion.py >/dev/null 2>&1; then
  pkill -f run_binance_ws_ingestion.py 2>/dev/null || true
  sleep 1
  pkill -9 -f run_binance_ws_ingestion.py 2>/dev/null || true
  echo "✓ Worker Binance WS arrêté."
else
  echo "✓ Aucun worker Binance WS à arrêter."
fi

if [[ "$COMPOSE_DOWN" -eq 1 ]]; then
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    echo "→ make -f Makefile.arquantix arquantix-down …"
    make -f Makefile.arquantix arquantix-down
    echo "✓ Stack Docker Arquantix arrêtée (volumes conservés)."
  else
    echo "! Docker indisponible — arquantix-down ignoré."
  fi
else
  echo ""
  echo "La stack Docker tourne encore. Pour tout arrêter :"
  echo "  bash scripts/stop-arquantix.sh --compose-down"
  echo "ou : make -f Makefile.arquantix arquantix-down"
fi

echo ""
echo "Terminé."
