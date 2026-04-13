#!/usr/bin/env bash
# Diagnostic local Arquantix — lecture seule (aucun arrêt, aucune écriture, aucune migration).
# Usage (depuis la racine du dépôt) : bash scripts/arquantix_local_doctor.sh
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env.arquantix"

# shellcheck source=arquantix_compose_lib.sh
source "$SCRIPT_DIR/arquantix_compose_lib.sh"
arquantix_lib_set_root "$REPO_ROOT"

red() { printf '\033[1;31m%s\033[0m\n' "$*"; }
grn() { printf '\033[1;32m%s\033[0m\n' "$*"; }
ylw() { printf '\033[1;33m%s\033[0m\n' "$*"; }
hdr() { printf '\n━━ %s ━━\n' "$*"; }

hdr "Arquantix — doctor local (read-only)"
echo "REPO_ROOT=$REPO_ROOT"
echo "Projet Compose attendu (.env.arquantix) : $(arquantix_expected_compose_project)"
echo "Fichier compose attendu : $(arquantix_compose_file)"
echo "Projet recovery (ARQUANTIX_RECOVERY_PROJECT) : $(arquantix_recovery_compose_project)"
echo "COMPOSE_PROJECT_NAME (shell courant, peut être vide) : ${COMPOSE_PROJECT_NAME:-<non exporté>}"

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  _leg="$(docker ps -q --filter "label=com.docker.compose.project=arquantix" 2>/dev/null | head -1)"
  if [[ -n "${_leg:-}" ]]; then
    ylw "Conteneurs encore présents sous le namespace historique « arquantix » (souvent cassé côté Docker Desktop)."
    ylw "  La stack par défaut du repo est « $(arquantix_expected_compose_project) » — éviter de mélanger les deux (voir LOCAL_ENV_RUNBOOK)."
  fi
fi

# --- .env.arquantix (sans « source » : grep / cut uniquement) ---
hdr "Variables critiques (.env.arquantix)"
if [[ ! -f "$ENV_FILE" ]]; then
  red "Fichier absent : $ENV_FILE"
else
  while IFS= read -r line; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line//[[:space:]]/}" ]] && continue
    case "$line" in
      COMPOSE_PROJECT_NAME=*|ARQUANTIX_COMPOSE_FILE=*|DB_NAME=*|DB_PORT=*|DB_USER=*|API_PORT=*|WEB_PORT=*|BACKEND_URL=*|BACKEND_API_URL=*|BACKEND_INTERNAL_URL=*|NEXT_PUBLIC_*)
        printf '  %s\n' "$line"
        ;;
    esac
  done <"$ENV_FILE"
  _dbn="$( (grep -E '^[[:space:]]*DB_NAME=' "$ENV_FILE" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  ylw "  Rappel : le nom dans DB_NAME doit être le même segment de base que dans tous les DATABASE_URL (API, web, .env racine)."
  [[ -n "${_dbn:-}" ]] && echo "  DB_NAME lu : ${_dbn}"
fi

hdr "Fichiers satellite (cibles DB)"
for f in "$REPO_ROOT/.env" "$REPO_ROOT/services/arquantix/api/.env.local" "$REPO_ROOT/services/arquantix/web/.env.local"; do
  if [[ -f "$f" ]]; then
    _u="$( (grep -E '^[[:space:]]*DATABASE_URL=' "$f" || true) | head -1 | cut -d= -f2- | tr -d '\r\"' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    if [[ -n "${_u:-}" ]]; then
      echo "  $f"
      echo "    DATABASE_URL=${_u}"
    else
      echo "  présent (pas de DATABASE_URL en première ligne grep) : $f"
    fi
  else
    ylw "  Absent : $f"
  fi
done

hdr "Volumes Docker attendus (noms fixes)"
for vol in arquantix_arquantix-db-data arquantix_arquantix-redis-data; do
  if docker volume inspect "$vol" >/dev/null 2>&1; then
    grn "  volume présent : $vol"
  else
    ylw "  volume absent (sera créé au premier « compose up » si besoin) : $vol"
  fi
done

hdr "Alignement projet Compose (officiel vs runtime)"
EXPECTED_CP="$(arquantix_expected_compose_project)"
echo "  Projet Compose attendu (.env.arquantix) : ${EXPECTED_CP:-arquantixrecovery}"

COMPOSE_VERDICT="OK"
COMPOSE_NOTE=""

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  COMPOSE_VERDICT="WARNING"
  COMPOSE_NOTE="Docker indisponible — impossible de vérifier les labels."
else
  API_CP=""
  _api_cid="$(arquantix_cid_for_service arquantix-api)"
  if [[ -n "$_api_cid" ]]; then
    API_CP="$(arquantix_inspect_api_compose_project)"
    echo "  Label com.docker.compose.project (service arquantix-api) : ${API_CP:-<vide>}"
    if [[ -n "$API_CP" && -n "$EXPECTED_CP" && "$API_CP" != "$EXPECTED_CP" ]]; then
      COMPOSE_VERDICT="CRITICAL"
      COMPOSE_NOTE="Le conteneur API appartient au projet « ${API_CP} » alors que .env.arquantix attend « ${EXPECTED_CP} » — make / scripts officiels ne pilotent pas cette stack."
    fi
  else
    COMPOSE_VERDICT="WARNING"
    COMPOSE_NOTE="Conteneur arquantix-api absent — stack arrêtée ou pas encore créée."
  fi

  RUNNING_ALT=0
  RUNNING_COUNT=0
  while IFS= read -r prow; do
    [[ -z "$prow" ]] && continue
    _name="$(printf '%s' "$prow" | cut -f1)"
    _stat="$(printf '%s' "$prow" | cut -f2)"
    printf '  compose ls : %s | %s\n' "$_name" "$_stat"
    if [[ "$_stat" == *"running("* ]]; then
      RUNNING_COUNT=$((RUNNING_COUNT + 1))
      if [[ -n "$EXPECTED_CP" && "$_name" != "$EXPECTED_CP" ]]; then
        RUNNING_ALT=1
      fi
    fi
  done < <(arquantix_compose_ls_rows_for_arquantix_file)

  if [[ "$RUNNING_COUNT" -gt 1 ]]; then
    COMPOSE_VERDICT="CRITICAL"
    COMPOSE_NOTE="${COMPOSE_NOTE:+${COMPOSE_NOTE} }Plusieurs projets Compose listés comme « running » pour les fichiers arquantix.yml / arquantix-recovery.yml — état anormal."
  fi
  if [[ "$RUNNING_ALT" -eq 1 && "$COMPOSE_VERDICT" != "CRITICAL" ]]; then
    COMPOSE_VERDICT="WARNING"
    COMPOSE_NOTE="${COMPOSE_NOTE:+${COMPOSE_NOTE} }Un projet autre que « ${EXPECTED_CP} » apparaît en running — vérifier les ports et docker compose ls."
  fi

  if [[ "$COMPOSE_VERDICT" == "OK" ]] && [[ -n "$(arquantix_cid_for_service arquantix-api)" ]]; then
    [[ -n "$API_CP" && -n "$EXPECTED_CP" && "$API_CP" == "$EXPECTED_CP" ]] || true
    if [[ -n "$API_CP" && -n "$EXPECTED_CP" && "$API_CP" == "$EXPECTED_CP" ]]; then
      COMPOSE_NOTE="Projet officiel aligné sur le conteneur arquantix-api."
    fi
  fi
fi

case "$COMPOSE_VERDICT" in
  OK) grn "  Verdict Compose : OK — ${COMPOSE_NOTE:-alignement attendu.}" ;;
  WARNING) ylw "  Verdict Compose : WARNING — ${COMPOSE_NOTE:-voir détails ci-dessus.}" ;;
  CRITICAL) red "  Verdict Compose : CRITICAL — ${COMPOSE_NOTE:-divergence projet Docker.}" ;;
esac
echo "  (Procédure : docs/arquantix/LOCAL_ENV_RUNBOOK.md — section projet officiel vs conteneurs actifs.)"

hdr "Projet Compose (docker compose ls)"
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  docker compose ls -a 2>/dev/null | head -20 || true
else
  ylw "Docker non disponible — impossible de lister les projets."
fi

hdr "Conteneurs du projet officiel (labels Compose)"
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  docker ps -a --filter "label=com.docker.compose.project=${EXPECTED_CP:-arquantixrecovery}" --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || true
else
  ylw "Docker non disponible."
fi

hdr "Base ciblée dans les conteneurs (si en cours d’exécution)"
if [[ -n "$(arquantix_cid_for_service arquantix-api)" ]] && arquantix_compose_exec arquantix-api printenv DATABASE_URL >/dev/null 2>&1; then
  u="$(arquantix_compose_exec arquantix-api printenv DATABASE_URL 2>/dev/null | tr -d '\r')"
  echo "  arquantix-api DATABASE_URL=$u"
  _ru="$(arquantix_compose_exec arquantix-api printenv REDIS_URL 2>/dev/null | tr -d '\r' || true)"
  [[ -n "$_ru" ]] && echo "  arquantix-api REDIS_URL=$_ru"
elif [[ -n "$(arquantix_cid_for_service_recovery arquantix-api)" ]] && arquantix_compose_exec_recovery arquantix-api printenv DATABASE_URL >/dev/null 2>&1; then
  u="$(arquantix_compose_exec_recovery arquantix-api printenv DATABASE_URL 2>/dev/null | tr -d '\r')"
  ylw "  (recovery) arquantix-api DATABASE_URL=$u"
else
  ylw "  arquantix-api absent ou injoignable — ignorer si la stack est arrêtée."
fi

if [[ -n "$(arquantix_cid_for_service arquantix-web)" ]]; then
  _b1="$(arquantix_compose_exec arquantix-web printenv BACKEND_API_URL 2>/dev/null | tr -d '\r' || true)"
  _b2="$(arquantix_compose_exec arquantix-web printenv BACKEND_URL 2>/dev/null | tr -d '\r' || true)"
  [[ -n "$_b1" ]] && echo "  arquantix-web BACKEND_API_URL=$_b1"
  [[ -n "$_b2" ]] && echo "  arquantix-web BACKEND_URL=$_b2"
elif [[ -n "$(arquantix_cid_for_service_recovery arquantix-web)" ]]; then
  _b1="$(arquantix_compose_exec_recovery arquantix-web printenv BACKEND_API_URL 2>/dev/null | tr -d '\r' || true)"
  _b2="$(arquantix_compose_exec_recovery arquantix-web printenv BACKEND_URL 2>/dev/null | tr -d '\r' || true)"
  ylw "  (recovery) arquantix-web BACKEND_API_URL=${_b1:-?} BACKEND_URL=${_b2:-?}"
fi

hdr "Cohérence env (script check_env_consistency)"
bash "$REPO_ROOT/scripts/check_env_consistency.sh" || true

hdr "API HTTP (optionnel)"
API_PORT_VAL=8000
if [[ -f "$ENV_FILE" ]]; then
  _ap="$( (grep -E '^[[:space:]]*API_PORT=' "$ENV_FILE" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -n "${_ap:-}" ]] && API_PORT_VAL="$_ap"
fi
raw="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 --max-time 5 "http://127.0.0.1:${API_PORT_VAL}/health" 2>/dev/null || true)"
raw="$(printf '%s' "$raw" | tr -cd '0-9')"
printf -v code '%.3s' "${raw}000"
if [[ "$code" == "200" ]]; then
  grn "  GET http://127.0.0.1:${API_PORT_VAL}/health → 200"
else
  ylw "  GET http://127.0.0.1:${API_PORT_VAL}/health → ${code:-timeout} (stack arrêtée ou port différent)"
fi

hdr "Alembic (API dans le conteneur, si disponible)"
if [[ -n "$(arquantix_cid_for_service arquantix-api)" ]] && arquantix_compose_exec arquantix-api alembic current >/dev/null 2>&1; then
  arquantix_compose_exec arquantix-api alembic current 2>/dev/null | sed 's/^/  /' || true
else
  ylw "  « alembic current » indisponible (conteneur arrêté ou commande absente)."
fi

hdr "Redis (service arquantix-redis)"
if [[ -n "$(arquantix_cid_for_service arquantix-redis)" ]]; then
  if arquantix_compose_exec arquantix-redis redis-cli ping 2>/dev/null | grep -qx PONG; then
    grn "  redis-cli ping → PONG"
  else
    ylw "  redis-cli ping : pas de PONG"
  fi
else
  ylw "  arquantix-redis absent — stack arrêtée."
fi

hdr "Volume Postgres monté sur arquantix-db"
_db_cid="$(arquantix_cid_for_service arquantix-db)"
if [[ -n "$_db_cid" ]]; then
  _mnt="$(docker inspect "$_db_cid" --format '{{range .Mounts}}{{println .Name .Destination}}{{end}}' 2>/dev/null | grep -F '/var/lib/postgresql/data' || true)"
  if echo "$_mnt" | grep -q 'arquantix_arquantix-db-data'; then
    grn "  Mount attendu : arquantix_arquantix-db-data → …/postgresql/data"
  else
    echo "  Mounts (extrait) :"
    echo "$_mnt" | sed 's/^/    /'
    ylw "  Vérifier manuellement : le volume principal doit être arquantix_arquantix-db-data"
  fi
else
  ylw "  arquantix-db absent — impossible d’inspecter les mounts."
fi

hdr "Tables métier (base DB_NAME depuis .env.arquantix)"
_dbn="${_dbn:-}"
if [[ -z "$_dbn" && -f "$ENV_FILE" ]]; then
  _dbn="$( (grep -E '^[[:space:]]*DB_NAME=' "$ENV_FILE" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
fi
if [[ -n "$(arquantix_cid_for_service arquantix-db)" && -n "$_dbn" ]]; then
  _tc="$(arquantix_compose_exec arquantix-db psql -U arquantix -d "$_dbn" -tAc 'SELECT count(*) FROM information_schema.tables WHERE table_schema='"'"'public'"'"';' 2>/dev/null | tr -d '[:space:]' || echo "")"
  if [[ -n "$_tc" ]] && [[ "$_tc" =~ ^[0-9]+$ ]]; then
    grn "  public.tables (approx.) : ${_tc} (base ${_dbn})"
  else
    ylw "  Impossible de compter les tables sur ${_dbn}"
  fi
else
  ylw "  DB ou DB_NAME indisponible."
fi

hdr "Fin"
echo "Documentation : docs/arquantix/LOCAL_ENV_RUNBOOK.md | recovery & backups : docs/LOCAL_DOCKER_RECOVERY.md"
echo ""
