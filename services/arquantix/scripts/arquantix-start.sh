#!/usr/bin/env bash

# Script de démarrage complet Arquantix
# À utiliser après un redémarrage de l'ordinateur

set -e

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║     ARQUANTIX — DÉMARRAGE COMPLET                                        ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Répertoire de base
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

# ============================================================================
# ÉTAPE 1: Vérifier Docker
# ============================================================================
echo -e "${YELLOW}[1/5] Vérification de Docker...${NC}"
if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker n'est pas démarré. Veuillez démarrer Docker Desktop.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker est démarré${NC}"
echo ""

# ============================================================================
# ÉTAPE 2: Démarrer et vérifier la base de données
# ============================================================================
echo -e "${YELLOW}[2/5] Vérification de arquantix-db...${NC}"

REPO_ROOT="$(cd "$BASE_DIR/../.." && pwd)"
# shellcheck source=../../../scripts/arquantix_compose_lib.sh
source "$REPO_ROOT/scripts/arquantix_compose_lib.sh"
arquantix_lib_set_root "$REPO_ROOT"
EXPECTED_DB_PORT="$( (grep -E '^[[:space:]]*DB_PORT=' "$REPO_ROOT/.env.arquantix" 2>/dev/null || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
EXPECTED_DB_PORT="${EXPECTED_DB_PORT:-5443}"

DB_CONTAINER="$(arquantix_cid_for_service arquantix-db)"
if [[ -z "$DB_CONTAINER" ]]; then
    echo -e "${RED}❌ Aucun conteneur running pour le service arquantix-db (projet $(arquantix_expected_compose_project)).${NC}"
    echo -e "${YELLOW}   Lancez : make -f Makefile.arquantix arquantix-up (depuis la racine du dépôt).${NC}"
    exit 1
fi

# Vérifier si le container est démarré
DB_RUNNING=$(docker inspect --format '{{.State.Running}}' "$DB_CONTAINER" 2>/dev/null || echo "false")

if [[ "$DB_RUNNING" != "true" ]]; then
    echo -e "${YELLOW}   Conteneur DB arrêté. Démarrage...${NC}"
    docker start "$DB_CONTAINER"
    echo -e "${YELLOW}   Attente que la DB soit healthy (15 secondes)...${NC}"
    sleep 15
fi

# Vérifier le health status
DB_HEALTH=$(docker inspect --format '{{.State.Health.Status}}' "$DB_CONTAINER" 2>/dev/null || echo "unknown")
DB_PORT=$(docker inspect --format '{{(index (index .NetworkSettings.Ports "5432/tcp") 0).HostPort}}' "$DB_CONTAINER" 2>/dev/null || echo "unknown")

if [[ "$DB_HEALTH" != "healthy" ]]; then
    echo -e "${YELLOW}   DB pas encore healthy. Attente supplémentaire (10 secondes)...${NC}"
    sleep 10
    DB_HEALTH=$(docker inspect --format '{{.State.Health.Status}}' "$DB_CONTAINER" 2>/dev/null || echo "unknown")
fi

if [[ "$DB_HEALTH" != "healthy" ]]; then
    echo -e "${RED}❌ DB n'est pas healthy (status: $DB_HEALTH)${NC}"
    echo -e "${YELLOW}   Logs : docker logs ${DB_CONTAINER}   ou   docker compose … logs arquantix-db${NC}"
    exit 1
fi

if [[ "$DB_PORT" != "$EXPECTED_DB_PORT" ]]; then
    echo -e "${RED}❌ Port DB hôte ($DB_PORT) ≠ DB_PORT attendu dans .env.arquantix ($EXPECTED_DB_PORT)${NC}"
    echo -e "${RED}   Vérifiez que vous ciblez bien arquantix-db (pas un autre Postgres).${NC}"
    exit 1
fi

# Vérifier la restart policy
RESTART_POLICY=$(docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' "$DB_CONTAINER")
if [[ "$RESTART_POLICY" == "no" ]]; then
    echo -e "${YELLOW}   ⚠️  Restart policy est 'no'. Configuration...${NC}"
    docker update --restart unless-stopped "$DB_CONTAINER"
    echo -e "${GREEN}   ✅ Restart policy configurée${NC}"
fi

# Vérifier la connexion PostgreSQL
if ! docker exec "$DB_CONTAINER" pg_isready -U arquantix > /dev/null 2>&1; then
    echo -e "${RED}❌ PostgreSQL n'accepte pas les connexions${NC}"
    exit 1
fi

echo -e "${GREEN}✅ arquantix-db: running=true | health=healthy | port hôte=${DB_PORT}${NC}"
echo ""

# ============================================================================
# ÉTAPE 3: Vérifier les configurations .env
# ============================================================================
echo -e "${YELLOW}[3/5] Vérification des configurations...${NC}"

# Vérifier web/.env
if [ -f "$BASE_DIR/web/.env" ]; then
    if grep -qE "localhost:${EXPECTED_DB_PORT}|127\\.0\\.0\\.1:${EXPECTED_DB_PORT}" "$BASE_DIR/web/.env" || grep -q "arquantix-db:5432" "$BASE_DIR/web/.env"; then
        echo -e "${GREEN}✅ web/.env: DATABASE_URL cohérent (port hôte ${EXPECTED_DB_PORT} ou service Docker)${NC}"
    else
        echo -e "${RED}❌ web/.env: DATABASE_URL doit pointer vers localhost:${EXPECTED_DB_PORT} (ou 127.0.0.1) ou arquantix-db:5432${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  web/.env non trouvé${NC}"
fi

# Vérifier api/.env.local ou api/.env
_API_ENV=""
[ -f "$BASE_DIR/api/.env.local" ] && _API_ENV="$BASE_DIR/api/.env.local"
[ -z "$_API_ENV" ] && [ -f "$BASE_DIR/api/.env" ] && _API_ENV="$BASE_DIR/api/.env"
if [ -n "$_API_ENV" ]; then
    if grep -qE "localhost:${EXPECTED_DB_PORT}|127\\.0\\.0\\.1:${EXPECTED_DB_PORT}" "$_API_ENV" || grep -q "arquantix-db:5432" "$_API_ENV"; then
        echo -e "${GREEN}✅ api : DATABASE_URL cohérent ($_API_ENV)${NC}"
    else
        echo -e "${RED}❌ ${_API_ENV}: DATABASE_URL doit pointer vers localhost:${EXPECTED_DB_PORT} ou arquantix-db:5432${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  api/.env.local et api/.env absents${NC}"
fi

echo ""

# ============================================================================
# ÉTAPE 4: Démarrer l'API
# ============================================================================
echo -e "${YELLOW}[4/5] Démarrage de l'API (FastAPI)...${NC}"

# Vérifier si l'API est déjà en cours d'exécution
if curl -s --max-time 2 http://localhost:8000/docs > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API déjà démarrée (http://localhost:8000/docs)${NC}"
else
    echo -e "${YELLOW}   Démarrage de l'API en arrière-plan...${NC}"
    cd "$BASE_DIR/api"
    nohup python3 -m uvicorn main:app --reload \
      --reload-include '.env' --reload-include '.env.local' \
      --host 0.0.0.0 --port 8000 > /tmp/arquantix-api.log 2>&1 &
    echo $! > /tmp/arquantix-api.pid
    echo -e "${GREEN}   ✅ API démarrée (PID: $(cat /tmp/arquantix-api.pid))${NC}"
    echo -e "${YELLOW}   ⏳ Attente que l'API soit prête (5 secondes)...${NC}"
    sleep 5
    
    # Vérifier que l'API répond
    if curl -s --max-time 2 http://localhost:8000/docs > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API accessible (http://localhost:8000/docs)${NC}"
    else
        echo -e "${YELLOW}⚠️  API démarrée mais pas encore accessible. Vérifiez: tail -f /tmp/arquantix-api.log${NC}"
    fi
fi

echo ""

# ============================================================================
# ÉTAPE 5: Démarrer le Web
# ============================================================================
echo -e "${YELLOW}[5/5] Démarrage du Web (Next.js)...${NC}"

# Vérifier si le Web est déjà en cours d'exécution
if curl -s --max-time 2 http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Web déjà démarré (http://localhost:3000)${NC}"
else
    echo -e "${YELLOW}   Démarrage du Web en arrière-plan...${NC}"
    cd "$BASE_DIR/web"
    nohup npm run dev > /tmp/arquantix-web.log 2>&1 &
    echo $! > /tmp/arquantix-web.pid
    echo -e "${GREEN}   ✅ Web démarré (PID: $(cat /tmp/arquantix-web.pid))${NC}"
    echo -e "${YELLOW}   ⏳ Attente que le Web soit prêt (10 secondes)...${NC}"
    sleep 10
    
    # Vérifier que le Web répond
    if curl -s --max-time 2 http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Web accessible (http://localhost:3000)${NC}"
    else
        echo -e "${YELLOW}⚠️  Web démarré mais pas encore accessible. Vérifiez: tail -f /tmp/arquantix-web.log${NC}"
    fi
fi

echo ""

# ============================================================================
# RÉSUMÉ FINAL
# ============================================================================
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║     DÉMARRAGE TERMINÉ                                                    ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}✅ Tous les services sont démarrés${NC}"
echo ""
echo "📋 URLs:"
echo "   🌐 Web:  http://localhost:3000"
echo "   🔐 Admin: http://localhost:3000/admin/login"
echo "   🔌 API:  http://localhost:8000/docs"
echo ""
echo "📝 Logs:"
echo "   - Web: tail -f /tmp/arquantix-web.log"
echo "   - API: tail -f /tmp/arquantix-api.log"
echo "   - DB:  docker logs <id> (service arquantix-db) ou docker compose … logs arquantix-db"
echo ""
echo "🔍 Vérifier le status:"
echo "   ./scripts/arquantix-status.sh"
echo ""
echo "🛑 Arrêter tous les services:"
echo "   ./stop-all.sh"
echo ""





