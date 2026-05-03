#!/usr/bin/env bash
#
# Arquantix — doctor local (ports, Docker vs Next hôte, HTTP, Postgres).
# Lecture seule. Ne modifie rien.
#
# Usage (racine du dépôt) :
#   bash scripts/arquantix_local_stack_doctor.sh
#   make -f Makefile.arquantix local-doctor
#
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT" || exit 1

# shellcheck source=arquantix_compose_lib.sh
source "$SCRIPT_DIR/arquantix_compose_lib.sh"
arquantix_lib_set_root "$REPO_ROOT"

ENVF="$REPO_ROOT/.env.arquantix"

read_kv() {
  local k="$1" def="${2:-}"
  if [[ ! -f "$ENVF" ]]; then echo "$def"; return; fi
  local v
  v="$( (grep -E "^[[:space:]]*${k}=" "$ENVF" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -n "$v" ]] && echo "$v" || echo "$def"
}

WEB_PORT="$(read_kv WEB_PORT 3000)"
API_PORT="$(read_kv API_PORT 8000)"
DB_PORT="$(read_kv DB_PORT 5443)"
DB_NAME="$(read_kv DB_NAME arquantix_fresh)"
DB_USER="$(read_kv DB_USER arquantix)"

RED='\033[1;31m'
GRN='\033[1;32m'
YLW='\033[1;33m'
BLD='\033[1m'
DIM='\033[2m'
RST='\033[0m'

ERR=0
WRN=0

line() { printf '%s\n' "$*"; }
ok() { line "${GRN}[OK]${RST} $*"; }
warn() { line "${YLW}[WARNING]${RST} $*"; WRN=$((WRN + 1)); }
err() { line "${RED}[ERROR]${RST} $*"; ERR=$((ERR + 1)); }
hdr() { printf '\n%s━━ %s ━━%s\n' "$BLD" "$*" "$RST"; }

# Premier processus en écoute TCP sur le port (nom de commande lsof)
tcp_listener_cmd() {
  local p="${1:?port}"
  lsof -nP -iTCP:"$p" -sTCP:LISTEN 2>/dev/null | awk 'NR==2 {print $1}' | head -1
}

tcp_listener_full() {
  local p="${1:?port}"
  lsof -nP -iTCP:"$p" -sTCP:LISTEN 2>/dev/null | tail -n +2 | head -3
}

classify_listener() {
  local cmd="$1"
  [[ -z "$cmd" ]] && { echo "none"; return; }
  # macOS : colonne COMMAND de lsof souvent tronquée (ex. com.docke = com.docker.backend).
  case "$cmd" in
    node|nodejs) echo "node" ;;
    docker-proxy) echo "docker" ;;
    com.docker*|com.docke) echo "docker" ;;
    *) echo "other:$cmd" ;;
  esac
}

docker_web_cid() {
  arquantix_cid_for_service arquantix-web
}

docker_api_cid() {
  arquantix_cid_for_service arquantix-api
}

has_next_dev_process() {
  # Processus typiques Next en dev sur l’hôte (hors seul Node d’un autre outil)
  if pgrep -if '(next dev|next-server|next-router-worker)' >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

curl_code() {
  local url="$1"
  local raw
  raw="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 --max-time 8 "$url" 2>/dev/null || true)"
  printf '%s' "$raw" | tr -cd '0-9'
}

hdr "Arquantix — local-doctor (Lot 1 stabilisation)"
line "REPO_ROOT=$REPO_ROOT"
line "${DIM}Ports attendus depuis .env.arquantix : WEB=$WEB_PORT API=$API_PORT DB=$DB_PORT (défauts si fichier absent)${RST}"

hdr "Tableau de vérité des ports (référence)"
line "+----------+--------------+---------------------------+-------------------------------+"
line "| Port     | Rôle         | Mode Docker (Compose)     | Mode hôte / mobile            |"
line "+----------+--------------+---------------------------+-------------------------------+"
line "| ${WEB_PORT}     | Next (web)   | arquantix-web → hôte :${WEB_PORT}  | npm run dev → :${WEB_PORT} (un seul actif) |"
line "| ${API_PORT}     | FastAPI      | arquantix-api → hôte :${API_PORT} | uvicorn local → :${API_PORT}           |"
line "| ${DB_PORT}     | PostgreSQL   | arquantix-db → hôte :${DB_PORT}  | Prisma / psql @ 127.0.0.1:${DB_PORT}   |"
line "| (LAN)    | Flutter      | —                         | API_BASE_URL=http://<IP_MAC>:${WEB_PORT} BFF ; AUTH → :8000 |"
line "+----------+--------------+---------------------------+-------------------------------+"
line "${DIM}Règle : un seul service doit écouter sur ${WEB_PORT} (Docker web OU Next npm, pas les deux).${RST}"

hdr "Conteneurs Docker (projet $(arquantix_expected_compose_project))"
if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  warn "Docker indisponible — section conteneurs partielle."
  WEB_CID=""
  API_CID=""
else
  WEB_CID="$(docker_web_cid)"
  API_CID="$(docker_api_cid)"
  if [[ -n "$WEB_CID" ]]; then
    ok "arquantix-web : conteneur actif ($(docker ps --filter "id=$WEB_CID" --format '{{.Names}}' | head -1))"
  else
    line "  arquantix-web : ${DIM}(aucun conteneur actif pour ce projet)${RST}"
  fi
  if [[ -n "$API_CID" ]]; then
    ok "arquantix-api : conteneur actif ($(docker ps --filter "id=$API_CID" --format '{{.Names}}' | head -1))"
  else
    line "  arquantix-api : ${DIM}(aucun conteneur actif pour ce projet)${RST}"
  fi
fi

hdr "Analyse port ${WEB_PORT} (web Next)"
L_CMD="$(tcp_listener_cmd "$WEB_PORT")"
CLASS="$(classify_listener "$L_CMD")"

if [[ -n "$(tcp_listener_full "$WEB_PORT")" ]]; then
  line "${DIM}Écoute sur :${WEB_PORT} —${RST}"
  tcp_listener_full "$WEB_PORT" | while read -r l; do line "  $l"; done
else
  line "${DIM}Aucun processus en LISTEN sur :${WEB_PORT}${RST}"
fi

NEXT_PROC=0
if has_next_dev_process; then
  NEXT_PROC=1
  line "${DIM}Processus Next détecté sur l’hôte (next dev / next-server).${RST}"
fi

WEB_DOCKER_UP=0
[[ -n "${WEB_CID:-}" ]] && WEB_DOCKER_UP=1

# Verdict mode web
case "$CLASS:$WEB_DOCKER_UP:$NEXT_PROC" in
  docker:1:0)
    ok "Mode web : ${BLD}OK — Docker web seul${RST} (écoute ${WEB_PORT} via stack Docker)."
    ;;
  docker:1:1)
    warn "Mode web : ${BLD}WARNING — conteneur arquantix-web actif ET processus Next détecté sur l’hôte.${RST}"
    line "  → Risque de double intention : n’utilisez qu’un mode (Docker web sur :${WEB_PORT} OU npm run dev)."
    ;;
  node:0:1)
    ok "Mode web : ${BLD}OK — Next hôte seul${RST} (node écoute :${WEB_PORT}, pas de conteneur web)."
    ;;
  node:1:*)
    warn "Mode web : anomalie — conteneur arquantix-web présent mais :${WEB_PORT} semble tenu par node."
    ;;
  none:0:0)
    line "  Mode web : ${DIM}idle — rien sur :${WEB_PORT} (stack arrêtée ou port libre).${RST}"
    ;;
  none:1:0)
    warn "Conteneur arquantix-web actif mais aucun LISTEN sur :${WEB_PORT} — vérifier mapping / crash."
    ;;
  none:0:1)
    warn "Processus Next détecté mais pas d’écoute sur :${WEB_PORT} — Next peut être sur un autre PORT."
    ;;
  *)
    if [[ "$CLASS" == other:* ]]; then
      err "Port ${WEB_PORT} : occupé par « ${L_CMD} » (ni node Next typique ni Docker) — conflit possible."
    elif [[ "$CLASS" == node ]] && [[ "$WEB_DOCKER_UP" -eq 0 ]]; then
      ok "Mode web : ${BLD}OK — Next hôte seul${RST} (node sur :${WEB_PORT})."
    elif [[ "$CLASS" == none ]] && [[ "$WEB_DOCKER_UP" -eq 0 ]] && [[ "$NEXT_PROC" -eq 0 ]]; then
      line "  ${DIM}Rien ne sert le web sur :${WEB_PORT}.${RST}"
    else
      warn "Mode web : cas mixte (listener=$CLASS, docker_web=$WEB_DOCKER_UP, next_proc=$NEXT_PROC) — inspecter manuellement."
    fi
    ;;
esac

hdr "Ports ${API_PORT} (API) et ${DB_PORT} (Postgres)"
API_LIST="$(tcp_listener_cmd "$API_PORT")"
DB_LIST="$(tcp_listener_cmd "$DB_PORT")"

if [[ -n "$API_LIST" ]]; then
  ok "TCP ${API_PORT} en écoute (commande: $API_LIST)"
else
  warn "Rien en écoute sur :${API_PORT} — API indisponible."
fi

if [[ -n "$DB_LIST" ]]; then
  ok "TCP ${DB_PORT} en écoute (Postgres exposé sur l’hôte pour Prisma)"
else
  DB_CID="$(arquantix_cid_for_service arquantix-db)"
  if docker info >/dev/null 2>&1 && [[ -n "$DB_CID" ]]; then
    if docker exec "$DB_CID" pg_isready -U "${DB_USER:-arquantix}" >/dev/null 2>&1; then
      ok "Postgres : conteneur arquantix-db répond (pg_isready) — vérifier mapping hôte :${DB_PORT}"
    else
      warn "Postgres : conteneur arquantix-db présent mais pg_isready échoue."
    fi
  else
    warn "Rien en écoute sur :${DB_PORT} — Postgres indisponible pour Prisma depuis l’hôte (ou Docker arrêté)."
  fi
fi

if command -v nc >/dev/null 2>&1; then
  if nc -z 127.0.0.1 "$DB_PORT" 2>/dev/null; then
    ok "nc : 127.0.0.1:${DB_PORT} joignable (TCP)"
  else
    [[ -n "$DB_LIST" ]] || warn "nc : 127.0.0.1:${DB_PORT} — échec (Prisma depuis l’hôte utilisera cette cible si DATABASE_URL la référence)."
  fi
fi

hdr "Garde-fous Lot 4 (ports dépréciés dans les .env)"
DEP_FOUND=0
for EF in "$ENVF" "$REPO_ROOT/services/arquantix/web/.env.local" "$REPO_ROOT/services/arquantix/api/.env.local" "$REPO_ROOT/.env"; do
  [[ ! -f "$EF" ]] && continue
  if grep -v '^\s*#' "$EF" 2>/dev/null | grep -v '^\s*$' | grep -E ':3001|:5433' >/dev/null 2>&1; then
    warn "Fichier ${EF#$REPO_ROOT/} contient :3001 ou :5433 — voir docs/arquantix/LOCAL_SETUP.md (ports officiels : web 3000, Postgres hôte 5443)."
    DEP_FOUND=1
  fi
done
[[ "$DEP_FOUND" -eq 0 ]] && ok "Aucune occurrence :3001 / :5433 dans les .env listés (hors lignes #)."

hdr "HTTP rapide"
C_HEALTH="$(curl_code "http://127.0.0.1:${API_PORT}/health")"
if [[ "$C_HEALTH" == "200" ]]; then
  ok "GET http://127.0.0.1:${API_PORT}/health → 200"
else
  warn "GET http://127.0.0.1:${API_PORT}/health → ${C_HEALTH:-timeout} (attendu 200 si API up)"
fi

C_ROOT="$(curl_code "http://127.0.0.1:${WEB_PORT}/")"
if [[ "$C_ROOT" =~ ^(200|301|302|307|308)$ ]]; then
  ok "GET http://127.0.0.1:${WEB_PORT}/ → $C_ROOT"
else
  if [[ "$C_ROOT" == "" ]] || [[ "$C_ROOT" == "000" ]]; then
    warn "GET http://127.0.0.1:${WEB_PORT}/ — pas de réponse HTTP (Next arrêté ou mauvais port)."
  else
    line "  GET / → $C_ROOT ${DIM}(peut être normal selon route)${RST}"
  fi
fi

hdr "Fichiers source de vérité (sans afficher de secrets)"
[[ -f "$ENVF" ]] && ok ".env.arquantix présent (ports, DB_NAME, compose)" || warn ".env.arquantix absent — défauts numériques utilisés ci-dessus."
[[ -f "$REPO_ROOT/services/arquantix/web/.env.local" ]] && ok "services/arquantix/web/.env.local présent (Prisma / dev)" || line "  ${DIM}web/.env.local : absent (optionnel si tout est dans .env)${RST}"
[[ -f "$REPO_ROOT/services/arquantix/api/.env.local" ]] && ok "services/arquantix/api/.env.local présent (API hors Docker)" || line "  ${DIM}api/.env.local : absent${RST}"
[[ -f "$REPO_ROOT/.env" ]] && ok ".env racine présent (souvent R2 + DATABASE_URL pour Docker web)" || line "  ${DIM}.env racine : absent${RST}"
line "${DIM}DB logique attendue : ${DB_NAME} (segment dans DATABASE_URL aligné avec .env.arquantix).${RST}"

hdr "Synthèse"
line "${DIM}Référence unique env local : ${RST}docs/arquantix/LOCAL_SETUP.md"
line "${DIM}Alignement DB détaillé (API · Alembic · Prisma, tables \`page_i18n\`, etc.) : ${RST}make -f Makefile.arquantix local-db-doctor"

if [[ "$ERR" -gt 0 ]]; then
  err "Verdict : $ERR erreur(s), $WRN avertissement(s) — corriger les [ERROR]."
  exit 1
fi
if [[ "$WRN" -gt 0 ]]; then
  warn "Verdict : $WRN avertissement(s) — revoir surtout le mode web (Docker vs Next) et Postgres."
  exit 0
fi
ok "Verdict : aucun problème critique détecté par ce doctor."
exit 0
