#!/usr/bin/env bash
#
# Reprise de session Arquantix : une seule commande pour une stack cohérente
# (même base logique partout — typ. arquantix_fresh si c’est celle où sont tes données ; voir .env.arquantix).
#
# Usage : depuis la racine du dépôt
#   bash scripts/start-arquantix.sh
#   bash scripts/start-arquantix.sh --skip-worker     # ne pas (re)lancer le worker Binance WS
#   bash scripts/start-arquantix.sh --skip-host-cleanup  # ne pas tuer node/Python sur les ports web/API
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

SKIP_WORKER=0
SKIP_HOST_CLEANUP=0
for arg in "$@"; do
  case "$arg" in
    --skip-worker) SKIP_WORKER=1 ;;
    --skip-host-cleanup) SKIP_HOST_CLEANUP=1 ;;
    -h|--help)
      echo "Usage: bash scripts/start-arquantix.sh [--skip-worker] [--skip-host-cleanup]"
      exit 0
      ;;
  esac
done

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

die() { echo -e "${RED}✖${NC} $*" >&2; exit 1; }
ok() { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }

echo ""
echo "═══ Arquantix — démarrage propre ═══"
echo ""

# ── 1. Config : même base partout (.env.arquantix + .env + .env.local) ───────
echo "→ Vérification des fichiers d’environnement…"

check_fresh_ref() {
  local f=$1
  [[ -f "$f" ]] || die "Fichier manquant : $f"
  if ! grep -qE 'arquantix_fresh|DB_NAME[[:space:]]*=[[:space:]]*arquantix_fresh' "$f" 2>/dev/null; then
    if grep -qE '/arquantix"|/arquantix\b' "$f" && ! grep -q 'arquantix_fresh' "$f"; then
      die "$f semble pointer vers la base « arquantix » et non « arquantix_fresh ». Harmoniser avec .env.arquantix (DB_NAME) avant de continuer."
    fi
    die "$f doit référencer explicitement la base de travail (DATABASE_URL ou DB_NAME alignés sur .env.arquantix)."
  fi
}

check_fresh_ref ".env.arquantix"
check_fresh_ref "services/arquantix/api/.env.local"
check_fresh_ref "services/arquantix/web/.env.local"
[[ -f .env ]] && check_fresh_ref ".env"
ok "Les fichiers .env pointent vers la même base logique (arquantix_fresh si c’est ton réglage actuel)."

# Charger les ports attendus (même logique que Makefile.arquantix)
if [[ -f .env.arquantix ]]; then
  set -a
  # shellcheck source=/dev/null
  source .env.arquantix
  set +a
fi
WEB_PORT="${WEB_PORT:-3000}"
API_PORT="${API_PORT:-8000}"
DB_PORT="${DB_PORT:-5443}"

WORKER_LOG="${ARQUANTIX_BINANCE_WS_LOG:-/tmp/run_binance_ws_ingestion.log}"

# ── 2. Nettoyage processus parasites (hôte) ─────────────────────────────────
echo ""
echo "→ Nettoyage prudent sur l’hôte…"

# Ancien worker Binance (on en relancera un propre à la fin si demandé)
if pgrep -fl run_binance_ws_ingestion.py >/dev/null 2>&1; then
  warn "Arrêt des processus run_binance_ws_ingestion.py existants…"
  pkill -f run_binance_ws_ingestion.py 2>/dev/null || true
  sleep 1
  pkill -9 -f run_binance_ws_ingestion.py 2>/dev/null || true
  ok "Anciens workers Binance WS arrêtés."
else
  ok "Aucun worker Binance WS à arrêter."
fi

# Ports web / API : éviter next dev / uvicorn en parallèle de Docker
kill_dev_on_port() {
  local port=$1
  local label=$2
  local pids
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  [[ -z "$pids" ]] && return 0
  for pid in $pids; do
    local comm
    comm="$(ps -p "$pid" -o comm= 2>/dev/null | tr -d ' ' || true)"
    case "$comm" in
      node|Python|python*|python3.9|python3.10|python3.11|python3.12|uvicorn)
        warn "Port $port ($label) occupé par « $comm » (PID $pid) — ce n’est pas Docker. Arrêt du processus…"
        kill "$pid" 2>/dev/null || true
        sleep 1
        if kill -0 "$pid" 2>/dev/null; then
          kill -9 "$pid" 2>/dev/null || true
        fi
        ;;
      com.docke|docker-proxy|Docker)
        ok "Port $port : écoute Docker (OK)."
        ;;
      *)
        ok "Port $port : PID $pid ($comm) — laissé tel quel (pas un serveur de dev classique)."
        ;;
    esac
  done
}

if [[ "$SKIP_HOST_CLEANUP" -eq 0 ]]; then
  kill_dev_on_port "$WEB_PORT" "Web"
  kill_dev_on_port "$API_PORT" "API"
else
  warn "Nettoyage des ports hôte ignoré (--skip-host-cleanup)."
fi

# ── 3. Stack Docker officielle ────────────────────────────────────────────
echo ""
echo "→ Démarrage de la stack (make -f Makefile.arquantix arquantix-up)…"

if ! command -v docker >/dev/null 2>&1; then
  die "Docker n’est pas dans le PATH. Lance Docker Desktop puis réessaie."
fi
if ! docker info >/dev/null 2>&1; then
  die "Le démon Docker ne répond pas. Lance Docker Desktop puis réessaie."
fi

# Alignement projet Compose : refuser si arquantix-api existe déjà sous un autre projet que .env.arquantix
# (sinon make arquantix-up ne pilote pas la stack réellement active — voir doctor + LOCAL_ENV_RUNBOOK).
# shellcheck source=arquantix_compose_lib.sh
source "$REPO_ROOT/scripts/arquantix_compose_lib.sh"
arquantix_lib_set_root "$REPO_ROOT"
_expected_cp="$(arquantix_expected_compose_project)"
while IFS= read -r _xcid; do
  [[ -z "$_xcid" ]] && continue
  _got_cp="$(docker inspect "$_xcid" --format '{{index .Config.Labels "com.docker.compose.project"}}' 2>/dev/null || true)"
  if [[ -n "$_got_cp" && -n "$_expected_cp" && "$_got_cp" != "$_expected_cp" ]]; then
    _cf="$(arquantix_compose_file)"
    die "Projet Compose Docker : un conteneur « arquantix-api » (autre projet) tourne sous « ${_got_cp} » alors que .env.arquantix définit COMPOSE_PROJECT_NAME=${_expected_cp}. Arrêt : docker compose --project-name ${_got_cp} --env-file .env.arquantix -f ${_cf} down puis : make -f Makefile.arquantix arquantix-up — docs/arquantix/LOCAL_ENV_RUNBOOK.md"
  fi
done < <(docker ps -q --filter "label=com.docker.compose.service=arquantix-api" 2>/dev/null)

make -f Makefile.arquantix arquantix-up

echo ""
echo "→ Attente courte des conteneurs…"
sleep 3

# ── 4. Conteneurs essentiels ───────────────────────────────────────────────
echo ""
echo "→ Vérification des conteneurs…"

need_service_up() {
  local svc=$1
  docker ps -q --filter "label=com.docker.compose.project=${_expected_cp}" --filter "label=com.docker.compose.service=${svc}" | grep -q . \
    || die "Service Compose absent ou arrêté : ${svc} (projet ${_expected_cp})."
}

need_service_up arquantix-api
need_service_up arquantix-web
need_service_up arquantix-db
need_service_up arquantix-redis
ok "Services : api, web, db, redis."

# ── 5. Ports TCP ──────────────────────────────────────────────────────────
echo ""
echo "→ Vérification des ports (hôte)…"

check_listen() {
  local port=$1
  local name=$2
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    ok "Port $port ($name) : en écoute."
  else
    warn "Port $port ($name) : rien en écoute — vérifie WEB_PORT/API_PORT dans .env.arquantix."
  fi
}

check_listen "$WEB_PORT" "Next / Web"
check_listen "$API_PORT" "FastAPI"
check_listen "$DB_PORT" "Postgres (hôte)"

# ── 6. DATABASE_URL dans les conteneurs ───────────────────────────────────
echo ""
echo "→ Vérification DATABASE_URL (alignement conteneurs)…"

API_DB_URL="$(arquantix_compose_exec arquantix-api printenv DATABASE_URL 2>/dev/null || true)"
WEB_DB_URL="$(arquantix_compose_exec arquantix-web printenv DATABASE_URL 2>/dev/null || true)"

[[ -n "$API_DB_URL" ]] || die "Impossible de lire DATABASE_URL dans arquantix-api."
[[ -n "$WEB_DB_URL" ]] || die "Impossible de lire DATABASE_URL dans arquantix-web."

echo "$API_DB_URL" | grep -q 'arquantix_fresh' || die "arquantix-api : DATABASE_URL ne contient pas arquantix_fresh : $API_DB_URL"
echo "$WEB_DB_URL" | grep -q 'arquantix_fresh' || die "arquantix-web : DATABASE_URL ne contient pas arquantix_fresh : $WEB_DB_URL"
ok "API et Web pointent vers la base arquantix_fresh."

DB_CHECK="$(arquantix_compose_exec arquantix-db psql -U arquantix -d arquantix_fresh -tAc "SELECT current_database();" 2>/dev/null | tr -d '[:space:]' || true)"
[[ "$DB_CHECK" == "arquantix_fresh" ]] || warn "SELECT current_database() dans le conteneur DB : « ${DB_CHECK:-échec} » (attendu arquantix_fresh)."
[[ "$DB_CHECK" == "arquantix_fresh" ]] && ok "Postgres : current_database() = arquantix_fresh."

# ── 7. Smoke HTTP ─────────────────────────────────────────────────────────
echo ""
echo "→ Smoke tests HTTP…"

API_HEALTH=0
API_OPENAPI=0
WEB_ROOT=0
WEB_ADMIN=0

code() {
  curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 3 "$1" || echo "000"
}

hc="$(code "http://127.0.0.1:${API_PORT}/health")"
[[ "$hc" == "200" ]] && API_HEALTH=1 || warn "GET /health → $hc (attendu 200)"

oc="$(code "http://127.0.0.1:${API_PORT}/openapi.json")"
[[ "$oc" == "200" ]] && API_OPENAPI=1 || warn "GET /openapi.json → $oc (attendu 200)"

wr="$(code "http://127.0.0.1:${WEB_PORT}/")"
[[ "$wr" == "200" ]] && WEB_ROOT=1 || warn "GET / (web) → $wr (attendu 200)"

ad="$(code "http://127.0.0.1:${WEB_PORT}/admin/login")"
[[ "$ad" == "200" ]] && WEB_ADMIN=1 || warn "GET /admin/login → $ad (attendu 200)"

# ── 8. Worker Binance WS ──────────────────────────────────────────────────
WORKER_OK=0
if [[ "$SKIP_WORKER" -eq 1 ]]; then
  warn "Worker Binance WS non (re)lancé (--skip-worker)."
else
  echo ""
  echo "→ Lancement du worker Binance WS (.env.arquantix)…"
  API_DIR="$REPO_ROOT/services/arquantix/api"
  if [[ ! -f "$REPO_ROOT/.env.arquantix" ]]; then
    warn ".env.arquantix introuvable — worker non lancé."
  elif [[ ! -f "$API_DIR/scripts/run_binance_ws_ingestion.py" ]]; then
    warn "Script run_binance_ws_ingestion.py introuvable — worker non lancé."
  else
    # Un seul worker : déjà tué en début de script
    nohup bash -c "set -a && source \"$REPO_ROOT/.env.arquantix\" && set +a && cd \"$API_DIR\" && exec python3 scripts/run_binance_ws_ingestion.py" >>"$WORKER_LOG" 2>&1 &
    sleep 2
    if pgrep -fl run_binance_ws_ingestion.py >/dev/null 2>&1; then
      WORKER_OK=1
      ok "Worker Binance WS démarré — logs : $WORKER_LOG"
    else
      warn "Le worker ne semble pas actif — voir $WORKER_LOG"
    fi
  fi
fi

# ── 9. Résumé ─────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════════"
if [[ "$API_HEALTH" -eq 1 && "$WEB_ROOT" -eq 1 ]]; then
  echo -e "${GREEN}Arquantix prêt à travailler.${NC}"
else
  echo -e "${YELLOW}Arquantix démarré avec des alertes — vérifie les messages ci-dessus.${NC}"
fi
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "  Base active     : arquantix_fresh"
echo "  API /health     : $([[ "$API_HEALTH" -eq 1 ]] && echo OK || echo KO)"
echo "  API /openapi    : $([[ "$API_OPENAPI" -eq 1 ]] && echo OK || echo KO)"
echo "  Web /           : $([[ "$WEB_ROOT" -eq 1 ]] && echo OK || echo KO)"
echo "  Web /admin/login: $([[ "$WEB_ADMIN" -eq 1 ]] && echo OK || echo KO)"
echo "  Worker Binance WS : $([[ "$SKIP_WORKER" -eq 1 ]] && echo ignoré || ([[ "$WORKER_OK" -eq 1 ]] && echo OK || echo KO))"
echo ""
echo "  Web    : http://127.0.0.1:${WEB_PORT}"
echo "  API    : http://127.0.0.1:${API_PORT}"
echo "  Admin  : http://127.0.0.1:${WEB_PORT}/admin/login"
echo "  Postgres (hôte) : port ${DB_PORT}"
echo ""
exit 0
