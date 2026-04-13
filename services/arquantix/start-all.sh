#!/bin/bash

# Script pour démarrer tous les serveurs Arquantix
# Usage: ./start-all.sh [--background]

set -e

# Couleurs pour les messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Répertoire de base
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$BASE_DIR/../.." && pwd)"
EXPECTED_DB_PORT="$( (grep -E '^[[:space:]]*DB_PORT=' "$ROOT_DIR/.env.arquantix" 2>/dev/null || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
EXPECTED_DB_PORT="${EXPECTED_DB_PORT:-5443}"

echo -e "${GREEN}🚀 Démarrage des serveurs Arquantix${NC}"
echo ""

# Vérifier si Docker est démarré
if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker n'est pas démarré. Veuillez démarrer Docker Desktop.${NC}"
    exit 1
fi

# shellcheck source=../../../scripts/arquantix_compose_lib.sh
source "$ROOT_DIR/scripts/arquantix_compose_lib.sh"
arquantix_lib_set_root "$ROOT_DIR"
COMPOSE_FILE="$ROOT_DIR/$(arquantix_compose_file)"
ENV_ARQ="$ROOT_DIR/.env.arquantix"
_cpn="$(arquantix_expected_compose_project)"

echo -e "${YELLOW}📦 Vérification du service arquantix-db (projet ${_cpn})...${NC}"
if ! docker ps -q --filter "label=com.docker.compose.project=${_cpn}" --filter "label=com.docker.compose.service=arquantix-db" | grep -q .; then
    echo -e "${YELLOW}⚠️  arquantix-db n'est pas démarré. Tentative : docker compose up -d arquantix-db...${NC}"
    (cd "$ROOT_DIR" && docker compose --project-name "$_cpn" --env-file "$ENV_ARQ" -f "$COMPOSE_FILE" up -d arquantix-db) || {
        echo -e "${RED}❌ Impossible de démarrer arquantix-db. Vérifiez : make -f Makefile.arquantix arquantix-up${NC}"
        exit 1
    }
fi
echo -e "${YELLOW}⏳ Attente que arquantix-db soit healthy...${NC}"

_DB_CID=""
for i in $(seq 1 6); do
    _DB_CID="$(arquantix_cid_for_service arquantix-db)"
    if [[ -n "$_DB_CID" ]]; then
        HEALTH=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}unknown{{end}}' "$_DB_CID" 2>/dev/null || echo "unknown")
        if [ "$HEALTH" = "healthy" ] || docker compose --project-name "$_cpn" --env-file "$ENV_ARQ" -f "$COMPOSE_FILE" exec -T arquantix-db pg_isready -U arquantix >/dev/null 2>&1; then
            echo -e "${GREEN}✅ arquantix-db est prêt${NC}"
            break
        fi
    fi
    if [ "$i" -eq 6 ]; then
        echo -e "${RED}❌ arquantix-db n'est pas healthy. Logs : docker compose --project-name ${_cpn} -f $(basename "$COMPOSE_FILE") logs arquantix-db${NC}"
        exit 1
    fi
    sleep 5
done

if docker compose --project-name "$_cpn" --env-file "$ENV_ARQ" -f "$COMPOSE_FILE" exec -T arquantix-db pg_isready -U arquantix > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL accepte les connexions${NC}"
else
    echo -e "${RED}❌ PostgreSQL n'accepte pas les connexions. Vérifiez les logs compose (service arquantix-db).${NC}"
    exit 1
fi

echo ""

# Fonction pour démarrer un serveur
start_server() {
    local name=$1
    local dir=$2
    local command=$3
    local port=$4
    
    echo -e "${YELLOW}🔄 Démarrage de $name...${NC}"
    cd "$BASE_DIR/$dir"
    
    if [ "$BACKGROUND" = "true" ]; then
        # Démarrer en arrière-plan
        nohup bash -c "$command" > "/tmp/arquantix-$name.log" 2>&1 &
        echo $! > "/tmp/arquantix-$name.pid"
        echo -e "${GREEN}✅ $name démarré en arrière-plan (PID: $(cat /tmp/arquantix-$name.pid))${NC}"
        echo -e "   📝 Logs: /tmp/arquantix-$name.log"
        echo -e "   🌐 URL: http://localhost:$port"
    else
        # Démarrer dans un nouveau terminal (macOS)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            osascript -e "tell application \"Terminal\" to do script \"cd '$BASE_DIR/$dir' && $command\""
            echo -e "${GREEN}✅ $name démarré dans un nouveau terminal${NC}"
        else
            # Linux - utiliser gnome-terminal ou xterm
            if command -v gnome-terminal &> /dev/null; then
                gnome-terminal -- bash -c "cd '$BASE_DIR/$dir' && $command; exec bash"
            elif command -v xterm &> /dev/null; then
                xterm -e "cd '$BASE_DIR/$dir' && $command" &
            else
                echo -e "${YELLOW}⚠️  Terminal non supporté. Exécutez manuellement:${NC}"
                echo -e "   cd $BASE_DIR/$dir"
                echo -e "   $command"
            fi
        fi
    fi
    echo ""
}

# Vérifier les arguments
BACKGROUND=false
if [ "$1" = "--background" ] || [ "$1" = "-b" ]; then
    BACKGROUND=true
fi

# Python pour l'API: .venv si présent
API_PYTHON="python3"
[ -x "$BASE_DIR/api/.venv/bin/python" ] && API_PYTHON="$BASE_DIR/api/.venv/bin/python"

# Démarrer l'API (PID: /tmp/arquantix-api.pid, aligné avec arquantix-boot/arquantix-stop)
if [ -f "$BASE_DIR/api/requirements.txt" ]; then
    _API_ENV=""
    [ -f "$BASE_DIR/api/.env.local" ] && _API_ENV="$BASE_DIR/api/.env.local"
    [ -z "$_API_ENV" ] && [ -f "$BASE_DIR/api/.env" ] && _API_ENV="$BASE_DIR/api/.env"
    if [ -n "$_API_ENV" ]; then
        if grep -qE "localhost:${EXPECTED_DB_PORT}|127\\.0\\.0\\.1:${EXPECTED_DB_PORT}" "$_API_ENV" || grep -q "arquantix-db:5432" "$_API_ENV"; then
            start_server "api" "api" "$API_PYTHON -m uvicorn main:app --reload --host 0.0.0.0 --port 8000" "8000"
        else
            echo -e "${RED}❌ api env: DATABASE_URL doit pointer vers localhost:${EXPECTED_DB_PORT} ou arquantix-db:5432${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}⚠️  api/.env.local et api/.env absents. Démarrage quand même...${NC}"
        start_server "api" "api" "$API_PYTHON -m uvicorn main:app --reload --host 0.0.0.0 --port 8000" "8000"
    fi
else
    echo -e "${RED}❌ Fichier api/requirements.txt non trouvé${NC}"
fi

# Démarrer le Web
if [ -f "$BASE_DIR/web/package.json" ]; then
    # Vérifier que DATABASE_URL pointe vers le bon port
    _WEB_ENV=""
    [ -f "$BASE_DIR/web/.env.local" ] && _WEB_ENV="$BASE_DIR/web/.env.local"
    [ -z "$_WEB_ENV" ] && [ -f "$BASE_DIR/web/.env" ] && _WEB_ENV="$BASE_DIR/web/.env"
    if [ -n "$_WEB_ENV" ]; then
        if grep -qE "localhost:${EXPECTED_DB_PORT}|127\\.0\\.0\\.1:${EXPECTED_DB_PORT}" "$_WEB_ENV" || grep -q "arquantix-db:5432" "$_WEB_ENV"; then
            start_server "web" "web" "npm run dev" "3000"
        else
            echo -e "${RED}❌ web env: DATABASE_URL doit pointer vers localhost:${EXPECTED_DB_PORT} ou arquantix-db:5432${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}⚠️  web/.env.local et web/.env absents. Démarrage quand même...${NC}"
        start_server "web" "web" "npm run dev" "3000"
    fi
else
    echo -e "${RED}❌ Fichier web/package.json non trouvé${NC}"
fi

echo -e "${GREEN}✨ Tous les serveurs sont en cours de démarrage !${NC}"
echo ""
echo -e "${YELLOW}📋 URLs:${NC}"
echo -e "   🌐 API:  http://localhost:8000/docs"
echo -e "   🖥️  Web:  http://localhost:3000"
echo -e "   🔐 Admin: http://localhost:3000/admin/login"
echo ""

if [ "$BACKGROUND" = "true" ]; then
    echo -e "${YELLOW}💡 Pour arrêter les serveurs:${NC}"
    echo -e "   ./stop-all.sh"
    echo ""
    echo -e "${YELLOW}💡 Pour voir les logs:${NC}"
    echo -e "   tail -f /tmp/arquantix-*.log"
fi

