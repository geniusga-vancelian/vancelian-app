#!/usr/bin/env bash

# Script de vérification du status des services Arquantix
# Usage: ./scripts/arquantix-status.sh

set -euo pipefail

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DB_CONTAINER="arquantix-db"
API_PORT=8000
WEB_PORT=3000
DB_PORT=5443
if [[ -f "$REPO_ROOT/.env.arquantix" ]]; then
  _dp="$( (grep -E '^[[:space:]]*DB_PORT=' "$REPO_ROOT/.env.arquantix" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -n "${_dp:-}" ]] && DB_PORT="$_dp"
fi
API_PID_FILE="/tmp/arquantix-api.pid"
WEB_PID_FILE="/tmp/arquantix-web.pid"
BINANCE_WS_PID_FILE="/tmp/arquantix-binance-ws.pid"
API_LOG_FILE="/tmp/arquantix-api.log"
WEB_LOG_FILE="/tmp/arquantix-web.log"
BINANCE_WS_LOG_FILE="/tmp/arquantix-binance-ws.log"

# Fonctions
success() { echo -e "${GREEN}✅${NC} $1"; }
warning() { echo -e "${YELLOW}⚠️${NC} $1"; }
error() { echo -e "${RED}❌${NC} $1"; }
info() { echo -e "${BLUE}ℹ${NC} $1"; }

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║     ARQUANTIX — STATUS CHECK                                             ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# DATABASE
# ============================================================================
info "[DB] Container: $DB_CONTAINER"

if ! docker ps -a --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    error "Container '${DB_CONTAINER}' n'existe pas"
    echo ""
    echo "STATUS: DB = NOT PRESENT"
    exit 1
fi

DB_RUNNING=$(docker inspect --format '{{.State.Running}}' "$DB_CONTAINER" 2>/dev/null || echo "false")
DB_HEALTH=$(docker inspect --format '{{.State.Health.Status}}' "$DB_CONTAINER" 2>/dev/null || echo "unknown")
DB_PORT_MAPPED=$(docker inspect --format '{{(index (index .NetworkSettings.Ports "5432/tcp") 0).HostPort}}' "$DB_CONTAINER" 2>/dev/null || echo "unknown")
RESTART_POLICY=$(docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' "$DB_CONTAINER" 2>/dev/null || echo "unknown")

echo "   Running:      $DB_RUNNING"
echo "   Health:       $DB_HEALTH"
echo "   Port (host):  $DB_PORT_MAPPED (container: 5432)"
echo "   Restart:      $RESTART_POLICY"

if [[ "$DB_RUNNING" != "true" ]]; then
    error "DB NOT RUNNING"
    echo ""
    echo "   Démarrer: docker start $DB_CONTAINER"
elif [[ "$DB_HEALTH" != "healthy" ]]; then
    error "DB NOT HEALTHY (status: $DB_HEALTH)"
    echo ""
    echo "   Logs: docker logs $DB_CONTAINER"
elif [[ "$DB_PORT_MAPPED" != "$DB_PORT" ]]; then
    error "DB WRONG PORT ($DB_PORT_MAPPED au lieu de $DB_PORT)"
    echo ""
    echo "   Vous pointez probablement vers zitadel-db (port 5434)!"
else
    success "DB: running=true | health=healthy | port=$DB_PORT_MAPPED"
    
    # Vérifier pg_isready
    if docker exec "$DB_CONTAINER" pg_isready -U arquantix > /dev/null 2>&1; then
        success "DB: PostgreSQL accepte les connexions"
    else
        error "DB: PostgreSQL n'accepte pas les connexions"
    fi
fi

echo ""

# ============================================================================
# API (FastAPI)
# ============================================================================
info "[API] FastAPI (port $API_PORT)"

# Vérifier PID file
API_PID=""
if [[ -f "$API_PID_FILE" ]]; then
    API_PID=$(cat "$API_PID_FILE" 2>/dev/null || echo "")
    if [[ -n "$API_PID" ]] && ps -p "$API_PID" > /dev/null 2>&1; then
        API_CMD=$(ps -p "$API_PID" -o command= 2>/dev/null | head -1 || echo "")
        echo "   PID file:     $API_PID_FILE (PID: $API_PID)"
        echo "   Command:      $API_CMD"
    else
        warning "PID file existe mais processus n'existe plus ($API_PID)"
        echo "   PID file:     $API_PID_FILE (stale)"
    fi
else
    info "PID file non trouvé: $API_PID_FILE"
fi

# Vérifier port
PORT_PID=$(lsof -tiTCP:$API_PORT -sTCP:LISTEN 2>/dev/null || echo "")
if [[ -n "$PORT_PID" ]]; then
    PORT_CMD=$(ps -p "$PORT_PID" -o command= 2>/dev/null | head -1 || echo "")
    echo "   Port $API_PORT: utilisé par PID $PORT_PID"
    echo "   Command:      $PORT_CMD"
    
    if [[ -n "$API_PID" ]] && [[ "$API_PID" == "$PORT_PID" ]]; then
        success "Port $API_PORT: correspond à notre PID file"
    elif [[ -z "$API_PID" ]]; then
        warning "Port $API_PORT: utilisé mais pas de PID file (processus orphelin?)"
    else
        warning "Port $API_PORT: utilisé par un autre PID ($PORT_PID != $API_PID)"
    fi
else
    info "Port $API_PORT: libre"
fi

# Vérifier HTTP endpoint
if curl -s --max-time 2 http://localhost:$API_PORT/health > /dev/null 2>&1; then
    HEALTH_RESPONSE=$(curl -s --max-time 2 http://localhost:$API_PORT/health 2>/dev/null || echo "")
    success "API: Health endpoint répond (http://localhost:$API_PORT/health)"
    if [[ -n "$HEALTH_RESPONSE" ]]; then
        echo "   Response:     $HEALTH_RESPONSE"
    fi
else
    error "API: Health endpoint ne répond pas"
    echo "   URL:          http://localhost:$API_PORT/health"
fi

# Logs
if [[ -f "$API_LOG_FILE" ]]; then
    LOG_SIZE=$(wc -l < "$API_LOG_FILE" 2>/dev/null || echo "0")
    echo "   Logs:         $API_LOG_FILE ($LOG_SIZE lignes)"
    echo "   Tail:         tail -f $API_LOG_FILE"
else
    info "Logs: $API_LOG_FILE (non trouvé)"
fi

echo ""

# ============================================================================
# WEB (Next.js)
# ============================================================================
info "[WEB] Next.js (port $WEB_PORT)"

# Vérifier PID file
WEB_PID=""
if [[ -f "$WEB_PID_FILE" ]]; then
    WEB_PID=$(cat "$WEB_PID_FILE" 2>/dev/null || echo "")
    if [[ -n "$WEB_PID" ]] && ps -p "$WEB_PID" > /dev/null 2>&1; then
        WEB_CMD=$(ps -p "$WEB_PID" -o command= 2>/dev/null | head -1 || echo "")
        echo "   PID file:     $WEB_PID_FILE (PID: $WEB_PID)"
        echo "   Command:      $WEB_CMD"
    else
        warning "PID file existe mais processus n'existe plus ($WEB_PID)"
        echo "   PID file:     $WEB_PID_FILE (stale)"
    fi
else
    info "PID file non trouvé: $WEB_PID_FILE"
fi

# Vérifier port
PORT_PID=$(lsof -tiTCP:$WEB_PORT -sTCP:LISTEN 2>/dev/null || echo "")
if [[ -n "$PORT_PID" ]]; then
    PORT_CMD=$(ps -p "$PORT_PID" -o command= 2>/dev/null | head -1 || echo "")
    echo "   Port $WEB_PORT: utilisé par PID $PORT_PID"
    echo "   Command:      $PORT_CMD"
    
    if [[ -n "$WEB_PID" ]] && [[ "$WEB_PID" == "$PORT_PID" ]]; then
        success "Port $WEB_PORT: correspond à notre PID file"
    elif [[ -z "$WEB_PID" ]]; then
        warning "Port $WEB_PORT: utilisé mais pas de PID file (processus orphelin?)"
    else
        warning "Port $WEB_PORT: utilisé par un autre PID ($PORT_PID != $WEB_PID)"
    fi
else
    info "Port $WEB_PORT: libre"
fi

# Vérifier HTTP endpoint
if curl -s --max-time 2 http://localhost:$WEB_PORT > /dev/null 2>&1; then
    success "WEB: HTTP endpoint répond (http://localhost:$WEB_PORT)"
else
    error "WEB: HTTP endpoint ne répond pas"
    echo "   URL:          http://localhost:$WEB_PORT"
fi

# Logs
if [[ -f "$WEB_LOG_FILE" ]]; then
    LOG_SIZE=$(wc -l < "$WEB_LOG_FILE" 2>/dev/null || echo "0")
    echo "   Logs:         $WEB_LOG_FILE ($LOG_SIZE lignes)"
    echo "   Tail:         tail -f $WEB_LOG_FILE"
else
    info "Logs: $WEB_LOG_FILE (non trouvé)"
fi

echo ""

# ============================================================================
# BINANCE WEBSOCKET INGESTION
# ============================================================================
info "[Binance WS] Ingestion prix temps réel"

BINANCE_WS_PID=""
if [[ -f "$BINANCE_WS_PID_FILE" ]]; then
    BINANCE_WS_PID=$(cat "$BINANCE_WS_PID_FILE" 2>/dev/null || echo "")
    if [[ -n "$BINANCE_WS_PID" ]] && ps -p "$BINANCE_WS_PID" > /dev/null 2>&1; then
        BINANCE_WS_CMD=$(ps -p "$BINANCE_WS_PID" -o command= 2>/dev/null | head -1 || echo "")
        echo "   PID file:     $BINANCE_WS_PID_FILE (PID: $BINANCE_WS_PID)"
        success "Binance WS: en cours d'exécution"
    else
        warning "PID file existe mais processus n'existe plus ($BINANCE_WS_PID)"
        echo "   PID file:     $BINANCE_WS_PID_FILE (stale)"
    fi
else
    info "PID file non trouvé: $BINANCE_WS_PID_FILE (ingestion non démarrée)"
fi

if [[ -f "$BINANCE_WS_LOG_FILE" ]]; then
    LOG_SIZE=$(wc -l < "$BINANCE_WS_LOG_FILE" 2>/dev/null || echo "0")
    echo "   Logs:         $BINANCE_WS_LOG_FILE ($LOG_SIZE lignes)"
fi

echo ""

# ============================================================================
# RÉSUMÉ
# ============================================================================
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║     STATUS SUMMARY                                                       ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Résumé DB
if [[ "$DB_RUNNING" == "true" ]] && [[ "$DB_HEALTH" == "healthy" ]] && [[ "$DB_PORT_MAPPED" == "$DB_PORT" ]]; then
    success "DB:   running=true | health=healthy | port=$DB_PORT_MAPPED | restart=$RESTART_POLICY"
else
    error "DB:   running=$DB_RUNNING | health=$DB_HEALTH | port=$DB_PORT_MAPPED"
fi

# Résumé API
if curl -s --max-time 2 http://localhost:$API_PORT/health > /dev/null 2>&1; then
    success "API:  http://localhost:$API_PORT (accessible)"
else
    error "API:  http://localhost:$API_PORT (NOT accessible)"
fi

# Résumé Web
if curl -s --max-time 2 http://localhost:$WEB_PORT > /dev/null 2>&1; then
    success "WEB:  http://localhost:$WEB_PORT (accessible)"
else
    error "WEB:  http://localhost:$WEB_PORT (NOT accessible)"
fi

# Résumé Binance WS
if [[ -f "$BINANCE_WS_PID_FILE" ]]; then
    BINANCE_WS_PID=$(cat "$BINANCE_WS_PID_FILE" 2>/dev/null || echo "")
    if [[ -n "$BINANCE_WS_PID" ]] && ps -p "$BINANCE_WS_PID" > /dev/null 2>&1; then
        success "Binance WS: running (PID: $BINANCE_WS_PID)"
    else
        warning "Binance WS: PID file présent mais processus arrêté"
    fi
else
    info "Binance WS: non démarré"
fi

echo ""
info "Commandes utiles:"
echo "   Démarrer:  ./scripts/arquantix-boot.sh  ou  make boot"
echo "   Arrêter:   ./scripts/arquantix-stop.sh  ou  make stop"
echo "   Status:    ./scripts/arquantix-status.sh  ou  make status"
echo ""
info "Logs:"
echo "   API:      tail -f $API_LOG_FILE"
echo "   WEB:      tail -f $WEB_LOG_FILE"
echo "   Binance:  tail -f $BINANCE_WS_LOG_FILE"
echo "   DB:       docker logs -f $DB_CONTAINER"
echo ""
