#!/usr/bin/env bash

# Script d'arrêt propre des services Arquantix
# Usage: ./scripts/arquantix-stop.sh [--db]
#
# Options:
#   --db    Arrête aussi le container arquantix-db

set -euo pipefail

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
API_PID_FILE="/tmp/arquantix-api.pid"
WEB_PID_FILE="/tmp/arquantix-web.pid"
BINANCE_WS_PID_FILE="/tmp/arquantix-binance-ws.pid"
DB_CONTAINER="arquantix-db"

# Fonctions
success() { echo -e "${GREEN}✅${NC} $1"; }
warning() { echo -e "${YELLOW}⚠️${NC} $1"; }
error() { echo -e "${RED}❌${NC} $1"; }
info() { echo -e "${YELLOW}ℹ${NC} $1"; }

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║     ARQUANTIX — ARRÊT DES SERVICES                                       ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Fonction pour arrêter un service
stop_service() {
    local service=$1
    local pid_file=$2
    local port=$3
    local process_pattern=$4
    
    if [[ ! -f "$pid_file" ]]; then
        warning "$service: PID file non trouvé ($pid_file)"
        # Vérifier si le port est utilisé quand même
        local port_pid=$(lsof -tiTCP:$port -sTCP:LISTEN 2>/dev/null || echo "")
        if [[ -n "$port_pid" ]]; then
            info "$service: Port $port utilisé par PID $port_pid (pas notre PID file)"
            warning "$service: Arrêt manuel requis: kill $port_pid"
        else
            info "$service: Port $port libre (service déjà arrêté)"
        fi
        return 0
    fi
    
    local pid=$(cat "$pid_file" 2>/dev/null || echo "")
    if [[ -z "$pid" ]]; then
        warning "$service: PID file vide"
        rm -f "$pid_file"
        return 0
    fi
    
    if ! ps -p "$pid" > /dev/null 2>&1; then
        warning "$service: Processus PID $pid n'existe plus (déjà arrêté)"
        rm -f "$pid_file"
        return 0
    fi
    
    # Vérifier que c'est bien notre processus (par command)
    local cmd=$(ps -p "$pid" -o command= 2>/dev/null || echo "")
    if [[ -z "$cmd" ]]; then
        warning "$service: Impossible de vérifier le processus PID $pid"
        rm -f "$pid_file"
        return 0
    fi
    
    # Arrêt gracieux
    info "$service: Arrêt gracieux (PID: $pid)..."
    kill "$pid" 2>/dev/null || true
    
    # Attendre max 5 secondes
    local waited=0
    while ps -p "$pid" > /dev/null 2>&1 && [[ $waited -lt 5 ]]; do
        sleep 1
        waited=$((waited + 1))
    done
    
    # Vérifier si toujours actif
    if ps -p "$pid" > /dev/null 2>&1; then
        warning "$service: Processus toujours actif, arrêt forcé (kill -9)..."
        kill -9 "$pid" 2>/dev/null || true
        sleep 1
    fi
    
    # Nettoyer PID file
    rm -f "$pid_file"
    
    if ps -p "$pid" > /dev/null 2>&1; then
        error "$service: Impossible d'arrêter le processus PID $pid"
        return 1
    else
        success "$service: Arrêté (PID: $pid)"
    fi
}

# Arrêter API
stop_service "API" "$API_PID_FILE" "8000" "uvicorn"
echo ""

# Arrêter Web
stop_service "Web" "$WEB_PID_FILE" "3000" "next dev"
echo ""

# Arrêter Binance WebSocket ingestion (pas de port dédié)
stop_service "Binance WS" "$BINANCE_WS_PID_FILE" "65535" "run_binance_ws_ingestion"
echo ""

# Arrêter aussi les processus orphelins (pattern matching)
info "Recherche de processus orphelins..."

# Processus uvicorn orphelins (pas via PID file)
pkill -f "uvicorn main:app.*--port 8000" 2>/dev/null && warning "Processus uvicorn orphelin arrêté" || true

# Processus Next.js orphelins (pas via PID file)
pkill -f "next dev" 2>/dev/null && warning "Processus Next.js orphelin arrêté" || true

# Processus Binance WS orphelins (pas via PID file)
pkill -f "run_binance_ws_ingestion" 2>/dev/null && warning "Processus Binance WS orphelin arrêté" || true

echo ""

# Option: arrêter aussi la DB
STOP_DB=false
if [[ "${1:-}" == "--db" ]]; then
    STOP_DB=true
fi

if [[ "$STOP_DB" == "true" ]]; then
    info "Arrêt du container DB (--db spécifié)..."
    if docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
        docker stop "$DB_CONTAINER"
        success "Container $DB_CONTAINER arrêté"
    else
        info "Container $DB_CONTAINER n'est pas en cours d'exécution"
    fi
    echo ""
else
    info "Container DB NON arrêté (utilisez --db pour l'arrêter aussi)"
    echo ""
fi

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║     ARRÊT TERMINÉ                                                        ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""
success "Tous les services ont été arrêtés"
echo ""
info "Pour redémarrer:"
echo "   ./scripts/arquantix-boot.sh"
echo "   make boot"
echo ""

