#!/usr/bin/env bash

# Script de démarrage robuste Arquantix (cold boot)
# Usage: ./scripts/arquantix-boot.sh
#        ARQUANTIX_SKIP_DOCKER=1 ./scripts/arquantix-boot.sh  # si Docker/DB déjà OK
#
# Gère:
# - Docker Desktop check (sauf si ARQUANTIX_SKIP_DOCKER=1)
# - Container arquantix-db (health, port hôte = DB_PORT dans .env.arquantix)
# - Validation env (pas de zitadel-db/5434)
# - Ports 3000 / 8000 : PID obsolètes, npm→node, uvicorn --reload, libération auto
# - PID files et logs
# - Vérifications finales (health endpoints)
#
# Variables utiles :
#   ARQUANTIX_SKIP_DOCKER=1     — ne pas vérifier Docker / arquantix-db
#   ARQUANTIX_AUTO_FREE_PORTS=1 — tuer les processus étrangers sur 8000/3000 (défaut : 1)
#   ARQUANTIX_AUTO_FREE_PORTS=0 — échouer si port pris (comportement strict)

set -euo pipefail
SKIP_DOCKER="${ARQUANTIX_SKIP_DOCKER:-0}"
ARQUANTIX_AUTO_FREE_PORTS="${ARQUANTIX_AUTO_FREE_PORTS:-1}"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DB_CONTAINER="arquantix-db"
API_PORT=8000
WEB_PORT=3000
# Surchargé après lecture de .env.arquantix (racine du dépôt)
DB_PORT=5443
API_PID_FILE="/tmp/arquantix-api.pid"
WEB_PID_FILE="/tmp/arquantix-web.pid"
BINANCE_WS_PID_FILE="/tmp/arquantix-binance-ws.pid"
API_LOG_FILE="/tmp/arquantix-api.log"
WEB_LOG_FILE="/tmp/arquantix-web.log"
BINANCE_WS_LOG_FILE="/tmp/arquantix-binance-ws.log"
HEALTH_CHECK_TIMEOUT=30
DB_HEALTH_TIMEOUT=60

# Répertoire de base
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

# Fonction d'affichage
info() { echo -e "${BLUE}ℹ${NC} $1"; }
success() { echo -e "${GREEN}✅${NC} $1"; }
warning() { echo -e "${YELLOW}⚠️${NC} $1"; }
error() { echo -e "${RED}❌${NC} $1"; }
step() { echo -e "${YELLOW}[$1]${NC} $2"; }

# Remonte la chaîne des parents jusqu'à trouver « saved » (npm→node, uvicorn reload, etc.)
listener_descends_from_saved_pid() {
    local listener=$1
    local saved=$2
    [[ -z "$listener" || -z "$saved" ]] && return 1
    [[ "$listener" == "$saved" ]] && return 0
    local cur=$listener
    local guard=0
    while [[ -n "$cur" ]] && [[ $guard -lt 50 ]]; do
        [[ "$cur" == "$saved" ]] && return 0
        cur=$(ps -o ppid= -p "$cur" 2>/dev/null | tr -d ' ')
        [[ -z "$cur" || "$cur" == "-" ]] && break
        if [[ "$cur" =~ ^[0-9]+$ ]] && [[ "$cur" -le 1 ]]; then
            break
        fi
        guard=$((guard + 1))
    done
    return 1
}

# Tue tout ce qui écoute sur le port (TERM puis KILL)
free_listen_port() {
    local port=$1
    local pids
    pids=$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
    [[ -z "$pids" ]] && return 0
    for pid in $pids; do
        kill -TERM "$pid" 2>/dev/null || true
    done
    sleep 2
    pids=$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
    for pid in $pids; do
        kill -9 "$pid" 2>/dev/null || true
    done
}

# Fonction de nettoyage en cas d'erreur
cleanup_on_error() {
    error "Erreur détectée. Nettoyage..."
    exit 1
}
trap cleanup_on_error ERR

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║     ARQUANTIX — DÉMARRAGE ROBUSTE (COLD BOOT)                            ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# ÉTAPES 1–2.5: Docker + arquantix-db (ignorées si ARQUANTIX_SKIP_DOCKER=1)
# ============================================================================
if [[ "$SKIP_DOCKER" != "1" ]]; then

# ÉTAPE 1: Vérifier Docker Desktop
step "1/8" "Vérification Docker Desktop"

if ! command -v docker &> /dev/null; then
    error "Docker n'est pas installé."
    echo "   Installez Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! docker ps > /dev/null 2>&1; then
    error "Docker Desktop n'est pas démarré."
    echo ""
    echo "   Instructions:"
    echo "   1. Lancez Docker Desktop"
    echo "   2. Attendez que Docker soit prêt (icône Docker dans la barre de menu)"
    echo "   3. Relancez: ./scripts/arquantix-boot.sh"
    exit 1
fi

success "Docker Desktop est démarré"
echo ""

# ÉTAPE 2: Gérer arquantix-db
step "2/8" "Vérification/start arquantix-db"

# Répertoire racine du dépôt (…/vancelian-app) — docker-compose.arquantix.yml
REPO_ROOT="$(cd "$BASE_DIR/../.." && pwd)"
ENV_ARQ_ROOT="$REPO_ROOT/.env.arquantix"
if [[ -f "$ENV_ARQ_ROOT" ]]; then
  _acf="$( (grep -E '^[[:space:]]*ARQUANTIX_COMPOSE_FILE=' "$ENV_ARQ_ROOT" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -n "${_acf:-}" ]] || _acf="docker-compose.arquantix-recovery.yml"
else
  _acf="docker-compose.arquantix-recovery.yml"
fi
COMPOSE_ARQ="$REPO_ROOT/$_acf"
_cpn="arquantixrecovery"
if [[ -f "$ENV_ARQ_ROOT" ]]; then
  _dp="$( (grep -E '^[[:space:]]*DB_PORT=' "$ENV_ARQ_ROOT" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -n "${_dp:-}" ]] && DB_PORT="$_dp"
  _xcpn="$( (grep -E '^[[:space:]]*COMPOSE_PROJECT_NAME=' "$ENV_ARQ_ROOT" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -n "${_xcpn:-}" ]] && _cpn="$_xcpn"
fi

# Vérifier si le container existe ; sinon tenter docker compose (évite l’écart vancelian-postg vs arquantix-db)
if ! docker ps -a --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    if [[ -f "$COMPOSE_ARQ" ]] && [[ -f "$ENV_ARQ_ROOT" ]] && docker compose version >/dev/null 2>&1; then
        info "Conteneur '${DB_CONTAINER}' absent — création (PostgreSQL + Redis)…"
        if docker compose --project-name "$_cpn" --env-file "$ENV_ARQ_ROOT" -f "$COMPOSE_ARQ" up -d arquantix-db arquantix-redis; then
            success "Compose : arquantix-db + arquantix-redis démarrés"
            sleep 2
        else
            error "docker compose a échoué (port ${DB_PORT} déjà pris par un autre service ?)."
            echo ""
            echo "   Libérez ${DB_PORT} ou changez DB_PORT dans .env.arquantix, puis relancez."
            echo "   Vérification : lsof -iTCP:${DB_PORT} -sTCP:LISTEN"
            exit 1
        fi
    else
        error "Container '${DB_CONTAINER}' n'existe pas et compose indisponible"
        echo ""
        echo "   Depuis la racine du dépôt :"
        echo "   docker compose --project-name ${_cpn} --env-file .env.arquantix -f ${_acf} up -d arquantix-db arquantix-redis"
        exit 1
    fi
fi

if ! docker ps -a --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    error "Container '${DB_CONTAINER}' introuvable après compose"
    exit 1
fi

# Vérifier/démarrer le container
DB_RUNNING=$(docker inspect --format '{{.State.Running}}' "$DB_CONTAINER" 2>/dev/null || echo "false")

if [[ "$DB_RUNNING" != "true" ]]; then
    info "Container arrêté. Démarrage..."
    docker start "$DB_CONTAINER"
fi

# Attendre que la DB soit healthy (avec timeout)
info "Attente que la DB soit healthy (timeout: ${DB_HEALTH_TIMEOUT}s)..."
DB_HEALTH="unknown"
for i in $(seq 1 $DB_HEALTH_TIMEOUT); do
    DB_HEALTH=$(docker inspect --format '{{.State.Health.Status}}' "$DB_CONTAINER" 2>/dev/null || echo "unknown")
    if [[ "$DB_HEALTH" == "healthy" ]]; then
        break
    fi
    sleep 1
done

if [[ "$DB_HEALTH" != "healthy" ]]; then
    if docker exec "$DB_CONTAINER" pg_isready -U arquantix > /dev/null 2>&1; then
        warning "Health Docker = $DB_HEALTH mais PostgreSQL répond (pg_isready) — poursuite"
    else
        error "DB n'est pas healthy après ${DB_HEALTH_TIMEOUT}s (status: $DB_HEALTH)"
        echo ""
        echo "   Vérifiez les logs:"
        echo "   docker logs ${DB_CONTAINER}"
        echo ""
        echo "   Vérifiez le health status:"
        echo "   docker inspect ${DB_CONTAINER} --format '{{.State.Health.Status}}'"
        exit 1
    fi
fi

# Vérifier le port mapping (doit correspondre à DB_PORT dans .env.arquantix)
DB_PORT_MAPPED=$(docker inspect --format '{{(index (index .NetworkSettings.Ports "5432/tcp") 0).HostPort}}' "$DB_CONTAINER" 2>/dev/null || echo "unknown")

if [[ "$DB_PORT_MAPPED" != "$DB_PORT" ]]; then
    error "Mauvais port DB ($DB_PORT_MAPPED au lieu de $DB_PORT)"
    echo ""
    echo "   Le container expose le port $DB_PORT_MAPPED au lieu de $DB_PORT"
    echo "   Vous pointez probablement vers zitadel-db (port 5434)!"
    echo ""
    echo "   Vérification:"
    echo "   docker inspect ${DB_CONTAINER} --format '{{(index (index .NetworkSettings.Ports \"5432/tcp\") 0).HostPort}}'"
    echo ""
    echo "   Container doit mapper 5432 -> $DB_PORT (pas 5434)"
    exit 1
fi

# Vérifier/appliquer restart policy
RESTART_POLICY=$(docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' "$DB_CONTAINER" 2>/dev/null || echo "no")
if [[ "$RESTART_POLICY" == "no" ]]; then
    warning "Restart policy est 'no'. Configuration 'unless-stopped'..."
    docker update --restart unless-stopped "$DB_CONTAINER"
    success "Restart policy configurée"
fi

# Vérifier pg_isready
if ! docker exec "$DB_CONTAINER" pg_isready -U arquantix > /dev/null 2>&1; then
    error "PostgreSQL n'accepte pas les connexions"
    echo ""
    echo "   Vérifiez: docker exec ${DB_CONTAINER} pg_isready -U arquantix"
    exit 1
fi

success "arquantix-db: running=true | health=healthy | port=$DB_PORT | restart=$RESTART_POLICY"
echo ""

else
    # ARQUANTIX_SKIP_DOCKER=1: on ignore Docker et arquantix-db
    warning "ARQUANTIX_SKIP_DOCKER=1: Docker/DB non vérifiés. Assurez-vous que arquantix-db tourne sur le port attendu (DB_PORT dans .env.arquantix, souvent 5443)."
    echo ""
fi

# ============================================================================
# ÉTAPE 2.5: Initialiser les instruments Binance
# ============================================================================
# Toujours exécuté, même avec SKIP_DOCKER, car la DB peut déjà tourner
info "Initialisation des instruments..."

info "Vérification des instruments Binance (crypto + forex)..."
if python3 "$BASE_DIR/api/scripts/ensure_binance_instruments.py" 2>/dev/null; then
    success "Instruments Binance: OK"
else
    warning "Initialisation instruments Binance: Échec"
fi

echo ""

# ============================================================================
# ÉTAPE 3: Valider les fichiers .env (pas de zitadel-db/5434)
# ============================================================================
step "3/8" "Validation des configurations .env"

# Fonction pour vérifier un fichier .env
check_env_file() {
    local env_file=$1
    local service=$2
    
    if [[ ! -f "$env_file" ]]; then
        warning "$service: $env_file non trouvé (peut être OK selon setup)"
        return 0
    fi
    
    # Vérifier qu'on ne pointe PAS vers zitadel-db ou port 5434
    if grep -qE "(zitadel-db|:5434)" "$env_file" 2>/dev/null; then
        error "$service: $env_file contient une référence à zitadel-db ou port 5434"
        echo ""
        echo "   Lignes problématiques:"
        grep -nE "(zitadel-db|:5434)" "$env_file" | sed 's/^/      /'
        echo ""
        echo "   DOIT pointer vers localhost:$DB_PORT ou ${DB_CONTAINER}:5432"
        echo "   PAS vers zitadel-db ou port 5434"
        return 1
    fi
    
    # Vérifier qu'on pointe vers le bon port (optionnel mais recommandé)
    if grep -qE "(localhost:$DB_PORT|${DB_CONTAINER}:5432)" "$env_file" 2>/dev/null; then
        success "$service: $env_file pointe vers le bon port/container"
    else
        warning "$service: $env_file ne contient pas de référence explicite à localhost:$DB_PORT ou ${DB_CONTAINER}:5432"
        echo "      (peut être OK si configuré différemment)"
    fi
}

check_env_file "$BASE_DIR/api/.env.local" "API (.env.local)"
check_env_file "$BASE_DIR/api/.env" "API (.env)"
check_env_file "$BASE_DIR/web/.env.local" "Web (.env.local)"
check_env_file "$BASE_DIR/web/.env" "Web (.env)"

echo ""

# ============================================================================
# ÉTAPE 4: Gérer les conflits de ports (3000, 8000)
# ============================================================================
step "4/8" "Vérification des ports (3000, 8000)"

# Supprimer les PID fichiers dont le processus n'existe plus
for _pidf in "$API_PID_FILE" "$WEB_PID_FILE" "$BINANCE_WS_PID_FILE"; do
    if [[ -f "$_pidf" ]]; then
        _sp=$(cat "$_pidf" 2>/dev/null || echo "")
        if [[ -z "$_sp" ]] || ! ps -p "$_sp" > /dev/null 2>&1; then
            rm -f "$_pidf"
            warning "PID fichier obsolète supprimé: $_pidf"
        fi
    fi
done

# Fonction pour gérer un port (LISTEN, détection session npm/node & uvicorn reload, libération auto)
handle_port_conflict() {
    local port=$1
    local service=$2
    local pid_file=$3
    
    local port_info
    port_info=$(lsof -tiTCP:$port -sTCP:LISTEN 2>/dev/null || echo "")
    
    if [[ -z "$port_info" ]]; then
        return 0
    fi
    
    local saved_pid=""
    [[ -f "$pid_file" ]] && saved_pid=$(cat "$pid_file" 2>/dev/null || echo "")
    
    # API : si /health répond, considérer la stack déjà up (même si PID fichier ≠ processus qui écoute)
    if [[ "$port" == "$API_PORT" ]] && command -v curl >/dev/null 2>&1; then
        if curl -sf --max-time 2 "http://127.0.0.1:${port}/health" >/dev/null 2>&1; then
            local hp
            hp=$(echo "$port_info" | head -1)
            if [[ -n "$hp" ]]; then
                echo "$hp" > "$pid_file"
            fi
            info "$service (port $port): déjà joignable (http://127.0.0.1:${port}/health, PID écoute: ${hp:-?})"
            return 2
        fi
    fi
    
    # Correspondance directe ou chaîne parentale (npm parent, node enfant ; uvicorn reload)
    if [[ -n "$saved_pid" ]] && ps -p "$saved_pid" > /dev/null 2>&1; then
        local pid
        for pid in $port_info; do
            if listener_descends_from_saved_pid "$pid" "$saved_pid"; then
                echo "$pid" > "$pid_file"
                info "$service (port $port): déjà démarré (session PID $saved_pid, écoute PID $pid)"
                return 2
            fi
        done
    fi
    
    # Port occupé par autre chose
    if [[ "$ARQUANTIX_AUTO_FREE_PORTS" == "1" ]]; then
        warning "Port $port occupé par PID(s) non reconnus comme cette session — libération (ARQUANTIX_AUTO_FREE_PORTS=1)"
        lsof -iTCP:$port -sTCP:LISTEN | sed 's/^/      /' || true
        free_listen_port "$port"
        rm -f "$pid_file"
        if [[ -n "$(lsof -tiTCP:$port -sTCP:LISTEN 2>/dev/null || true)" ]]; then
            error "Port $port toujours occupé après libération automatique"
            echo "   Lancez: ./scripts/arquantix-stop.sh   ou   kill -9 \$(lsof -tiTCP:$port -sTCP:LISTEN)"
            exit 1
        fi
        warning "Port $port libéré"
        return 0
    fi
    
    error "Port $port est utilisé par un processus inconnu"
    echo ""
    echo "   PID(s) utilisant le port:"
    lsof -iTCP:$port -sTCP:LISTEN | sed 's/^/      /'
    echo ""
    echo "   Solutions:"
    echo "   1. Libération auto au prochain lancement (défaut) : export ARQUANTIX_AUTO_FREE_PORTS=1"
    echo "   2. Arrêt propre : ./scripts/arquantix-stop.sh"
    echo "   3. kill -9 \$(lsof -tiTCP:$port -sTCP:LISTEN)"
    echo ""
    exit 1
}

handle_port_conflict $API_PORT "API" "$API_PID_FILE"
API_ALREADY_RUNNING=$?
handle_port_conflict $WEB_PORT "Web" "$WEB_PID_FILE"
WEB_ALREADY_RUNNING=$?

echo ""

# ============================================================================
# ÉTAPE 5: Démarrer l'API (si pas déjà démarrée)
# ============================================================================
step "5/8" "Démarrage de l'API (FastAPI)"

if [[ $API_ALREADY_RUNNING -eq 2 ]]; then
    success "API déjà démarrée"
else
    # Python pour l'API: .venv si présent, sinon python3
    if [[ -x "$BASE_DIR/api/.venv/bin/python" ]]; then
        API_PYTHON="$BASE_DIR/api/.venv/bin/python"
        info "Utilisation de api/.venv"
    else
        API_PYTHON="python3"
    fi
    if ! (cd "$BASE_DIR/api" && $API_PYTHON -c "import uvicorn" 2>/dev/null); then
        error "uvicorn introuvable. Depuis api/: pip install -r requirements.txt"
        exit 1
    fi

    # Nettoyer l'ancien PID file si présent
    rm -f "$API_PID_FILE"

    # Démarrer l'API
    info "Démarrage de l'API (FastAPI) en arrière-plan..."
    cd "$BASE_DIR/api"
    nohup $API_PYTHON -m uvicorn main:app --reload --host 0.0.0.0 \
      --reload-include '.env' --reload-include '.env.local' \
      --port $API_PORT > "$API_LOG_FILE" 2>&1 &
    api_pid=$!
    echo $api_pid > "$API_PID_FILE"
    success "API démarrée (PID: $api_pid)"
    
    # Attendre que l'API soit prête
    info "Attente que l'API soit prête (timeout: ${HEALTH_CHECK_TIMEOUT}s)..."
    api_ready=false
    for i in $(seq 1 $HEALTH_CHECK_TIMEOUT); do
        if curl -s --max-time 2 http://localhost:$API_PORT/health > /dev/null 2>&1; then
            api_ready=true
            break
        fi
        sleep 1
    done
    
    if [[ "$api_ready" == "true" ]]; then
        success "API accessible (http://localhost:$API_PORT/health)"
    else
        warning "API démarrée mais pas encore accessible après ${HEALTH_CHECK_TIMEOUT}s"
        echo "      Vérifiez: tail -f $API_LOG_FILE"
    fi
    # PID qui écoute (reload uvicorn peut différer du PID nohup)
    for _i in $(seq 1 15); do
        _lp=$(lsof -tiTCP:$API_PORT -sTCP:LISTEN 2>/dev/null | head -1 || true)
        if [[ -n "${_lp:-}" ]]; then
            echo "$_lp" > "$API_PID_FILE"
            break
        fi
        sleep 1
    done
fi

echo ""

# ============================================================================
# ÉTAPE 6: Démarrer le Web (si pas déjà démarré)
# ============================================================================
step "6/8" "Démarrage du Web (Next.js)"

if [[ $WEB_ALREADY_RUNNING -eq 2 ]]; then
    success "Web déjà démarré"
else
    if ! command -v node >/dev/null 2>&1; then
        error "Node.js introuvable (commande « node »). Installez Node ou activez nvm."
        exit 1
    fi
    # Nettoyer l'ancien PID file si présent
    rm -f "$WEB_PID_FILE"
    
    # Démarrer le Web
    info "Démarrage du Web (Next.js) en arrière-plan..."
    cd "$BASE_DIR/web"
    nohup npm run dev > "$WEB_LOG_FILE" 2>&1 &
    web_pid=$!
    echo $web_pid > "$WEB_PID_FILE"
    success "Web démarré (PID: $web_pid)"
    
    # Attendre que le Web soit prêt
    info "Attente que le Web soit prêt (timeout: ${HEALTH_CHECK_TIMEOUT}s)..."
    web_ready=false
    for i in $(seq 1 $HEALTH_CHECK_TIMEOUT); do
        if curl -s --max-time 2 http://localhost:$WEB_PORT > /dev/null 2>&1; then
            web_ready=true
            break
        fi
        sleep 1
    done
    
    if [[ "$web_ready" == "true" ]]; then
        success "Web accessible (http://localhost:$WEB_PORT)"
    else
        warning "Web démarré mais pas encore accessible après ${HEALTH_CHECK_TIMEOUT}s"
        echo "      Vérifiez: tail -f $WEB_LOG_FILE"
    fi
    # Enregistrer le PID qui écoute vraiment sur le port (npm parent ≠ node enfant)
    for _i in $(seq 1 20); do
        _lp=$(lsof -tiTCP:$WEB_PORT -sTCP:LISTEN 2>/dev/null | head -1 || true)
        if [[ -n "${_lp:-}" ]]; then
            echo "$_lp" > "$WEB_PID_FILE"
            break
        fi
        sleep 1
    done
fi

echo ""

# ============================================================================
# ÉTAPE 7: Démarrer l'ingestion Binance WebSocket (prix temps réel)
# ============================================================================
step "7/8" "Démarrage de l'ingestion Binance WebSocket"

if [[ -f "$BINANCE_WS_PID_FILE" ]]; then
    BINANCE_WS_PID=$(cat "$BINANCE_WS_PID_FILE" 2>/dev/null || echo "")
    if [[ -n "$BINANCE_WS_PID" ]] && ps -p "$BINANCE_WS_PID" > /dev/null 2>&1; then
        success "Ingestion Binance WebSocket déjà démarrée (PID: $BINANCE_WS_PID)"
    else
        rm -f "$BINANCE_WS_PID_FILE"
    fi
fi

if [[ ! -f "$BINANCE_WS_PID_FILE" ]] || ! ps -p "$(cat "$BINANCE_WS_PID_FILE" 2>/dev/null)" > /dev/null 2>&1; then
    if [[ -x "$BASE_DIR/api/.venv/bin/python" ]]; then
        BINANCE_WS_PYTHON="$BASE_DIR/api/.venv/bin/python"
    else
        BINANCE_WS_PYTHON="python3"
    fi
    rm -f "$BINANCE_WS_PID_FILE"
    info "Démarrage de l'ingestion Binance WebSocket en arrière-plan..."
    cd "$BASE_DIR/api"
    nohup $BINANCE_WS_PYTHON scripts/run_binance_ws_ingestion.py > "$BINANCE_WS_LOG_FILE" 2>&1 &
    binance_ws_pid=$!
    echo $binance_ws_pid > "$BINANCE_WS_PID_FILE"
    sleep 2
    if ps -p $binance_ws_pid > /dev/null 2>&1; then
        success "Ingestion Binance WebSocket démarrée (PID: $binance_ws_pid)"
    else
        warning "Ingestion Binance WebSocket a quitté (aucun instrument Binance? Vérifiez: tail $BINANCE_WS_LOG_FILE)"
        rm -f "$BINANCE_WS_PID_FILE"
    fi
fi

echo ""

# ============================================================================
# ÉTAPE 8: Vérifications finales
# ============================================================================
step "8/8" "Vérifications finales"

# Vérifier DB
if [[ "$SKIP_DOCKER" == "1" ]]; then
    warning "DB check: ignoré (ARQUANTIX_SKIP_DOCKER=1)"
else
    if docker exec "$DB_CONTAINER" pg_isready -U arquantix > /dev/null 2>&1; then
        success "DB check: OK"
    else
        error "DB check: ÉCHEC"
        exit 1
    fi
fi

# Vérifier API health
if curl -s --max-time 2 http://localhost:$API_PORT/health > /dev/null 2>&1; then
    success "API health check: OK"
else
    warning "API health check: ÉCHEC (peut être en cours de démarrage)"
fi

# Vérifier Web (HTML)
if curl -s --max-time 2 http://localhost:$WEB_PORT > /dev/null 2>&1; then
    success "Web check: OK"
else
    warning "Web check: ÉCHEC (peut être en cours de démarrage)"
fi

# Vérifier Binance WS ingestion
if [[ -f "$BINANCE_WS_PID_FILE" ]] && ps -p "$(cat "$BINANCE_WS_PID_FILE" 2>/dev/null)" > /dev/null 2>&1; then
    success "Binance WS ingestion: running (PID: $(cat "$BINANCE_WS_PID_FILE"))"
else
    warning "Binance WS ingestion: NON ACTIVE (prix crypto non mis à jour en temps réel)"
fi

# Vérifier que les données crypto sont disponibles
CRYPTO_COUNT=$(curl -s --max-time 3 "http://localhost:$API_PORT/api/market-data/all-crypto" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('summaries',[])))" 2>/dev/null || echo "0")
if [[ "$CRYPTO_COUNT" -gt 0 ]]; then
    success "Données crypto: $CRYPTO_COUNT instrument(s) avec prix"
else
    warning "Données crypto: aucune donnée (les prix peuvent prendre quelques secondes à arriver)"
fi

echo ""

# ============================================================================
# RÉSUMÉ FINAL
# ============================================================================
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║     DÉMARRAGE TERMINÉ                                                    ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""
success "Tous les services sont démarrés"
echo ""
echo "📋 URLs:"
echo "   🌐 Web:     http://localhost:$WEB_PORT"
echo "   🔐 Admin:   http://localhost:$WEB_PORT/admin/login"
echo "   🔌 API:     http://localhost:$API_PORT/docs"
echo "   ❤️  Health:  http://localhost:$API_PORT/health"
echo ""
echo "📝 Logs:"
echo "   - API:      tail -f $API_LOG_FILE"
echo "   - Web:      tail -f $WEB_LOG_FILE"
echo "   - Binance:  tail -f $BINANCE_WS_LOG_FILE"
echo "   - DB:       docker logs -f $DB_CONTAINER"
echo ""
echo "🔍 Vérifier le status:"
echo "   ./scripts/arquantix-status.sh"
echo "   make status"
echo ""
echo "🛑 Arrêter tous les services:"
echo "   ./scripts/arquantix-stop.sh"
echo "   make stop"
echo ""

# Audit docs optionnel
if [[ "${AUDIT_DOCS:-0}" == "1" ]]; then
    echo ""
    step "BONUS" "Audit documentation (AUDIT_DOCS=1)"
    if [[ -f "$BASE_DIR/scripts/audit_doc_completeness.py" ]] || [[ -f "$BASE_DIR/tools/audit_doc_completeness.py" ]]; then
        python3 "$BASE_DIR/tools/audit_doc_completeness.py" 2>/dev/null || python3 "$BASE_DIR/scripts/audit_doc_completeness.py" 2>/dev/null || true
    else
        warning "Script audit_doc_completeness.py non trouvé"
    fi
    echo ""
fi

