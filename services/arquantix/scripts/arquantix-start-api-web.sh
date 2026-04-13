#!/usr/bin/env bash
# Démarre uniquement l'API (8000) et le Web (3000).
# À utiliser quand Docker et arquantix-db tournent déjà.
# Usage: ./scripts/arquantix-start-api-web.sh   ou   make start-api-web

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

API_PORT=8000
WEB_PORT=3000
API_PID_FILE="/tmp/arquantix-api.pid"
WEB_PID_FILE="/tmp/arquantix-web.pid"
BINANCE_WS_PID_FILE="/tmp/arquantix-binance-ws.pid"
API_LOG_FILE="/tmp/arquantix-api.log"
WEB_LOG_FILE="/tmp/arquantix-web.log"
BINANCE_WS_LOG_FILE="/tmp/arquantix-binance-ws.log"
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║     ARQUANTIX — DÉMARRAGE API + WEB (DB supposée déjà lancée)            ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Arrêter d’éventuels anciens processus (nos PIDs ou processus sur les ports)
./scripts/arquantix-stop.sh 2>/dev/null || true
rm -f "$API_PID_FILE" "$WEB_PID_FILE" "$BINANCE_WS_PID_FILE"

# Libérer les ports si occupés par un processus inconnu
for port in $API_PORT $WEB_PORT; do
  pid=$(lsof -tiTCP:$port -sTCP:LISTEN 2>/dev/null || true)
  if [[ -n "$pid" ]]; then
    echo -e "${RED}❌ Le port $port est utilisé (PID: $pid). Arrêtez-le puis relancez.${NC}"
    echo "   kill -9 $pid"
    exit 1
  fi
done

# Python pour l'API: .venv si présent
if [[ -x "$BASE_DIR/api/.venv/bin/python" ]]; then
  API_PYTHON="$BASE_DIR/api/.venv/bin/python"
else
  API_PYTHON="python3"
fi
if ! (cd "$BASE_DIR/api" && $API_PYTHON -c "import uvicorn" 2>/dev/null); then
  echo -e "${RED}❌ uvicorn introuvable. cd api && pip install -r requirements.txt${NC}"
  exit 1
fi

echo -e "${YELLOW}[1/3] Démarrage API (port $API_PORT)...${NC}"
cd "$BASE_DIR/api"
nohup $API_PYTHON -m uvicorn main:app --reload \
  --reload-include '.env' --reload-include '.env.local' \
  --host 0.0.0.0 --port $API_PORT > "$API_LOG_FILE" 2>&1 &
echo $! > "$API_PID_FILE"
echo -e "${GREEN}   API: PID $(cat $API_PID_FILE)${NC}"

echo -e "${YELLOW}[2/3] Démarrage Web (port $WEB_PORT)...${NC}"
cd "$BASE_DIR/web"
nohup npm run dev > "$WEB_LOG_FILE" 2>&1 &
echo $! > "$WEB_PID_FILE"
echo -e "${GREEN}   Web: PID $(cat $WEB_PID_FILE)${NC}"

echo -e "${YELLOW}[3/3] Démarrage ingestion Binance WebSocket...${NC}"
python3 "$BASE_DIR/api/scripts/ensure_binance_instruments.py" 2>/dev/null || true
cd "$BASE_DIR/api"
nohup ${API_PYTHON:-python3} scripts/run_binance_ws_ingestion.py > "$BINANCE_WS_LOG_FILE" 2>&1 &
echo $! > "$BINANCE_WS_PID_FILE"
sleep 1
if ps -p $(cat "$BINANCE_WS_PID_FILE" 2>/dev/null) > /dev/null 2>&1; then
  echo -e "${GREEN}   Binance WS: PID $(cat $BINANCE_WS_PID_FILE)${NC}"
else
  echo -e "${YELLOW}   Binance WS: a quitté (aucun instrument? tail $BINANCE_WS_LOG_FILE)${NC}"
  rm -f "$BINANCE_WS_PID_FILE"
fi

echo ""
echo -e "${YELLOW}Attente démarrage (15 s)...${NC}"
sleep 15

# Vérifications
ok=1
if curl -s --max-time 3 http://localhost:$API_PORT/health > /dev/null 2>&1; then
  echo -e "${GREEN}✅ API: http://localhost:$API_PORT/health${NC}"
else
  echo -e "${RED}❌ API pas encore prête. Logs: tail -f $API_LOG_FILE${NC}"
  ok=0
fi
if curl -s --max-time 3 http://localhost:$WEB_PORT > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Web: http://localhost:$WEB_PORT${NC}"
else
  echo -e "${YELLOW}⚠️  Web peut mettre 1–2 min. Logs: tail -f $WEB_LOG_FILE${NC}"
fi

echo ""
echo "📋 URLs:"
echo "   🌐 Web:     http://localhost:$WEB_PORT"
echo "   🔐 Admin:   http://localhost:$WEB_PORT/admin/login"
echo "   🔌 API:     http://localhost:$API_PORT/docs"
echo "   ❤️  Health:  http://localhost:$API_PORT/health"
echo ""
echo "📝 Logs: tail -f $API_LOG_FILE  |  tail -f $WEB_LOG_FILE  |  tail -f $BINANCE_WS_LOG_FILE"
echo "🛑 Arrêt: make stop  ou  ./scripts/arquantix-stop.sh"
echo ""

[[ $ok -eq 1 ]] && exit 0 || exit 1
