#!/usr/bin/env bash
#
# Arquantix — visibilité DB : API / Alembic / Web·Prisma + tables CMS critiques.
# Lecture seule. Ne modifie aucune base.
#
# Usage (racine du dépôt) :
#   bash scripts/arquantix_db_visibility_doctor.sh
#   make -f Makefile.arquantix local-db-doctor
#
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT" || exit 1

# shellcheck source=arquantix_compose_lib.sh
source "$SCRIPT_DIR/arquantix_compose_lib.sh"
arquantix_lib_set_root "$REPO_ROOT"

ENV_ARQ="$REPO_ROOT/.env.arquantix"
WEB_ENV_LOCAL="$REPO_ROOT/services/arquantix/web/.env.local"
API_ENV_LOCAL="$REPO_ROOT/services/arquantix/api/.env.local"
ENV_ROOT="$REPO_ROOT/.env"

RED='\033[1;31m'
GRN='\033[1;32m'
YLW='\033[1;33m'
BLD='\033[1m'
DIM='\033[2m'
RST='\033[0m'

line() { printf '%s\n' "$*"; }
ok() { line "${GRN}[OK]${RST} $*"; }
warn() { line "${YLW}[WARNING]${RST} $*"; }
err() { line "${RED}[ERROR]${RST} $*"; }
hdr() { printf '\n%s━━ %s ━━%s\n' "$BLD" "$*" "$RST"; }

read_kv() {
  local f="$1" k="$2" def="${3:-}"
  [[ ! -f "$f" ]] && { echo "$def"; return; }
  local v
  v="$( (grep -E "^[[:space:]]*${k}=" "$f" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | sed 's/^"//;s/"$//')"
  [[ -n "$v" ]] && echo "$v" || echo "$def"
}

DB_NAME_ARQ="$(read_kv "$ENV_ARQ" DB_NAME arquantix_fresh)"

mask_url() {
  python3 - "$1" <<'PY'
import re, sys
u = (sys.argv[1] or "").strip()
if not u:
    print("")
else:
    print(re.sub(r"(postgresql://[^:]+:)[^@]+@", r"\1****@", u, count=1))
PY
}

# Affiche host, port, dbname — tab-separated (ligne 1 = champs)
parse_pg_url() {
  python3 - "$1" <<'PY'
import sys, urllib.parse as u
raw = sys.argv[1].strip()
if not raw:
    print("\t\t"); sys.exit(0)
p = u.urlparse(raw)
h = p.hostname or ""
port = p.port or 5432
path = (p.path or "").strip("/")
db = path.split("/")[0] if path else ""
print(f"{h}\t{port}\t{db}")
PY
}

extract_database_url_from_file() {
  local f="$1"
  [[ ! -f "$f" ]] && { echo ""; return; }
  local line
  line="$( (grep -E '^[[:space:]]*DATABASE_URL=' "$f" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' )"
  [[ -z "$line" ]] && { echo ""; return; }
  # Retirer guillemets englobants
  line="${line#\"}"
  line="${line%\"}"
  echo "$line"
}

printenv_api_container() {
  local cid
  cid="$(arquantix_cid_for_service arquantix-api)"
  [[ -z "$cid" ]] && { echo ""; return; }
  docker exec "$cid" printenv DATABASE_URL 2>/dev/null | tr -d '\r' || echo ""
}

printenv_web_container() {
  local cid
  cid="$(arquantix_cid_for_service arquantix-web)"
  [[ -z "$cid" ]] && { echo ""; return; }
  docker exec "$cid" printenv DATABASE_URL 2>/dev/null | tr -d '\r' || echo ""
}

# URL attendue pour Prisma / API sur l’hôte à partir de .env.arquantix (même logique que compose publié)
url_from_env_arquantix_host() {
  local u p h port name
  u="$(read_kv "$ENV_ARQ" DB_USER arquantix)"
  p="$(read_kv "$ENV_ARQ" DB_PASSWORD arquantix)"
  h="127.0.0.1"
  port="$(read_kv "$ENV_ARQ" DB_PORT 5443)"
  name="$(read_kv "$ENV_ARQ" DB_NAME arquantix_fresh)"
  echo "postgresql://${u}:${p}@${h}:${port}/${name}"
}

hdr "Arquantix — doctor DB (visibilité API · Alembic · Web/Prisma)"
line "REPO_ROOT=$REPO_ROOT"
line "${DIM}Aucune modification de base ; mots de passe masqués dans les URLs affichées.${RST}"

# --- API ---
hdr "1. API FastAPI + Alembic"
API_URL_CONTAINER="$(printenv_api_container)"
API_URL_FILE="$(extract_database_url_from_file "$API_ENV_LOCAL")"
[[ -z "$API_URL_FILE" ]] && API_URL_FILE="$(extract_database_url_from_file "$REPO_ROOT/services/arquantix/api/.env")"

line "${BLD}Alembic${RST} utilise la variable ${BLD}DATABASE_URL${RST} au démarrage du processus API (voir conteneur : ${DIM}CMD alembic upgrade head && uvicorn …${RST})."
line "Source de vérité code : ${DIM}services/arquantix/api/database.py${RST} — priorité \`DATABASE_URL\` env, sinon \`DB_*\` (dont défaut port 5443)."

if [[ -n "$API_URL_CONTAINER" ]]; then
  line ""
  line "${BLD}Runtime conteneur arquantix-api${RST} (effectif pour Alembic + API dans Docker) :"
  line "  URL : $(mask_url "$API_URL_CONTAINER")"
  _p="$(parse_pg_url "$API_URL_CONTAINER")"
  IFS=$'\t' read -r API_H API_P API_D <<<"$_p"
  line "  → host=$API_H  port=$API_P  database=$API_D"
  line "  ${DIM}Source : printenv DATABASE_URL dans le conteneur${RST}"
else
  warn "Conteneur arquantix-api absent — pas de printenv."
fi

line ""
if [[ -n "$API_URL_FILE" ]]; then
  line "${BLD}Fichier API (hors conteneur / ordre de chargement Python)${RST} :"
  line "  $(mask_url "$API_URL_FILE")"
  [[ -f "$API_ENV_LOCAL" ]] && line "  ${DIM}Lu depuis : services/arquantix/api/.env.local${RST}"
else
  line "${BLD}Pas de DATABASE_URL dans api/.env.local${RST} — si vous lancez uvicorn sur l’hôte, le code utilise \`database.py\` (défauts ou env shell)."
fi

# --- Web / Prisma ---
hdr "2. Web Next.js / Prisma"
WEB_URL_CONTAINER="$(printenv_web_container)"
WEB_URL_FILE="$(extract_database_url_from_file "$WEB_ENV_LOCAL")"
[[ -z "$WEB_URL_FILE" ]] && WEB_URL_FILE="$(extract_database_url_from_file "$REPO_ROOT/services/arquantix/web/.env")"
[[ -z "$WEB_URL_FILE" ]] && WEB_URL_FILE="$(extract_database_url_from_file "$ENV_ROOT")"

line "Prisma lit ${BLD}DATABASE_URL${RST} (${DIM}services/arquantix/web/prisma/schema.prisma${RST})."
line "Next charge aussi le ${BLD}.env à la racine du dépôt${RST} si présent (${DIM}next.config.js${RST})."

if [[ -n "$WEB_URL_CONTAINER" ]]; then
  line ""
  line "${BLD}Runtime conteneur arquantix-web${RST} :"
  line "  URL : $(mask_url "$WEB_URL_CONTAINER")"
  _w="$(parse_pg_url "$WEB_URL_CONTAINER")"
  IFS=$'\t' read -r W_H W_P W_D <<<"$_w"
  line "  → host=$W_H  port=$W_P  database=$W_D"
  line "  ${DIM}Source : printenv DATABASE_URL dans le conteneur${RST}"
else
  warn "Conteneur arquantix-web absent."
fi

line ""
if [[ -n "$WEB_URL_FILE" ]]; then
  line "${BLD}Fichier prioritaire côté hôte (typ. web/.env.local ou .env racine)${RST} :"
  line "  $(mask_url "$WEB_URL_FILE")"
  [[ -f "$WEB_ENV_LOCAL" ]] && line "  ${DIM}services/arquantix/web/.env.local présent${RST}"
  [[ -f "$ENV_ROOT" ]] && grep -q DATABASE_URL "$ENV_ROOT" 2>/dev/null && line "  ${DIM}.env racine contient DATABASE_URL (chargé par Next)${RST}"
else
  warn "Aucun DATABASE_URL trouvé dans web/.env.local ni web/.env ni .env racine — en dev, Prisma peut utiliser l’env shell uniquement."
fi

HOST_INFER="$(url_from_env_arquantix_host)"
line ""
line "${BLD}Inférence depuis .env.arquantix seul (hôte → Postgres publié)${RST} :"
line "  $(mask_url "$HOST_INFER")"
line "  ${DIM}Utile pour comparer quand Prisma est lancé depuis l’hôte avec alignement sur DB_PORT/DB_NAME.${RST}"

# --- Cohérence ---
hdr "3. Cohérence API vs Web (même cluster logique ?)"
COH_ISSUE=0
if [[ -n "$API_URL_CONTAINER" && -n "$WEB_URL_CONTAINER" ]]; then
  AH="${API_H:-}"
  AD="${API_D:-}"
  if [[ -n "${W_D:-}" ]]; then
    if [[ "$AD" == "$W_D" ]]; then
      ok "Même nom de base (${BLD}$AD${RST}) entre conteneurs API et Web."
      if [[ "$API_H" != "$W_H" ]]; then
        line "  ${DIM}Hôtes différents ($API_H vs $W_H) : inhabituel si les deux tournent dans le même compose — vérifier la config.${RST}"
      fi
    else
      err "Noms de base différents : API→${AD:-?}  Web→${W_D:-?}"
      COH_ISSUE=1
    fi
  fi
elif [[ -n "$API_URL_FILE" && -n "$WEB_URL_FILE" ]]; then
  IFS=$'\t' read -r _a _b ADB <<<"$(parse_pg_url "$API_URL_FILE")"
  IFS=$'\t' read -r _w _x WDB <<<"$(parse_pg_url "$WEB_URL_FILE")"
  if [[ "$ADB" == "$WDB" ]]; then
    ok "Même nom de base (${BLD}$ADB${RST}) entre api/.env.local et web (fichier)."
  else
    warn "Noms de base différents entre fichiers : API→$ADB  Web→$WDB — à corriger sauf intention documentée."
    COH_ISSUE=1
  fi
else
  line "${DIM}Pas assez d’informations (conteneurs arrêtés et/ou .env manquants) — lancer la stack ou compléter les .env.local.${RST}"
fi

if [[ "$COH_ISSUE" -eq 1 ]]; then
  warn "Scénario fréquent de panne : API OK (une base) et web KO (autre base ou schéma Prisma incomplet sur la base réellement utilisée par Next)."
fi

hdr "3b. Alignement DB_NAME (.env.arquantix vs Prisma / fichiers)"
if [[ -n "${WEB_URL_FILE:-}" ]]; then
  IFS=$'\t' read -r _ _ WDB_FILE <<<"$(parse_pg_url "$WEB_URL_FILE")"
  if [[ -n "${WDB_FILE:-}" && "$WDB_FILE" != "$DB_NAME_ARQ" ]]; then
    warn "DATABASE_URL dans le fichier web cible la base « $WDB_FILE » mais DB_NAME dans .env.arquantix est « $DB_NAME_ARQ » — risque d’écart volontaire ou d’erreur."
  elif [[ -n "${WDB_FILE:-}" ]]; then
    ok "Segment base du DATABASE_URL (fichier web) = DB_NAME (.env.arquantix) ($DB_NAME_ARQ)."
  fi
fi
if [[ -n "${API_URL_FILE:-}" ]]; then
  IFS=$'\t' read -r _ _ ADB_FILE <<<"$(parse_pg_url "$API_URL_FILE")"
  if [[ -n "${ADB_FILE:-}" && "$ADB_FILE" != "$DB_NAME_ARQ" ]]; then
    warn "DATABASE_URL dans api/.env.local cible « $ADB_FILE » mais DB_NAME dans .env.arquantix est « $DB_NAME_ARQ » — vérifier l’intention."
  fi
fi

# --- Tables Prisma (CMS) ---
hdr "4. Tables CMS Web (Prisma) — présence dans PostgreSQL"
DB_CID="$(arquantix_cid_for_service arquantix-db)"
DB_NAME_CHECK="$DB_NAME_ARQ"
DB_USER_CHECK="$(read_kv "$ENV_ARQ" DB_USER arquantix)"

PRISMA_CMS_TABLES=(pages page_i18n sections section_contents media menus menu_items)

table_exists() {
  local t="$1"
  if [[ -z "$DB_CID" ]]; then
    echo "skip"
    return
  fi
  local q="SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='${t}' LIMIT 1;"
  local out
  out="$(docker exec "$DB_CID" psql -U "$DB_USER_CHECK" -d "$DB_NAME_CHECK" -tAc "$q" 2>/dev/null | tr -d '[:space:]')"
  [[ "$out" == "1" ]] && echo "yes" || echo "no"
}

if [[ -z "$DB_CID" ]]; then
  warn "Conteneur arquantix-db introuvable — impossible de lister les tables (Docker arrêté ?)."
else
  line "Cluster : conteneur ${BLD}arquantix-db${RST}, base inspectée ${BLD}$DB_NAME_CHECK${RST} (= \`DB_NAME\` dans .env.arquantix)."
  if [[ -n "${W_D:-}" && "$W_D" != "$DB_NAME_CHECK" ]]; then
    warn "Le web (conteneur) pointe vers la base « $W_D » mais cette section teste « $DB_NAME_CHECK » — les résultats ci-dessous ne décrivent pas la base réellement utilisée par Next si l’écart est réel."
  fi
  line ""
  printf '%-22s  %s\n' "Table" "Statut"
  line "────────────────────────────────────────"
  for t in "${PRISMA_CMS_TABLES[@]}"; do
    ex="$(table_exists "$t")"
    if [[ "$ex" == "yes" ]]; then
      printf '%-22s  %s\n' "$t" "${GRN}OK — présente${RST}"
    elif [[ "$ex" == "no" ]]; then
      printf '%-22s  %s\n' "$t" "${YLW}WARNING — absente${RST}"
      [[ "$t" == "page_i18n" ]] && line "         ${DIM}→ Souvent : migration Prisma SQL non appliquée sur cette base (migrate deploy peut échouer P3005 si historique absent).${RST}"
    else
      printf '%-22s  %s\n' "$t" "(non vérifié)"
    fi
  done
fi

hdr "5. Rappel diagnostic « API OK, web KO »"
line "- L’API et Alembic peuvent être sains sur une base dont le schéma métier Prisma (tables CMS) est incomplet ou sur une autre base que celle lue par Next."
line "- Vérifier : ${BLD}make -f Makefile.arquantix local-db-doctor${RST} + section tables ci-dessus."
line "- Doc : ${DIM}docs/arquantix/LOCAL_DB_ALIGNMENT.md${RST}"

line ""
line "${BLD}Fin du doctor DB.${RST}"
