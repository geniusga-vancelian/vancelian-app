#!/usr/bin/env bash
# Partagé : alignement projet Compose officiel (.env.arquantix) vs runtime Docker.
# Usage (depuis la racine du dépôt) :
#   source scripts/arquantix_compose_lib.sh
#   arquantix_lib_set_root "$REPO_ROOT"
# shellcheck shell=bash
set -u

ARQUANTIX_LIB_ROOT=""

arquantix_lib_set_root() {
  ARQUANTIX_LIB_ROOT="$1"
}

arquantix_expected_compose_project() {
  local f="${ARQUANTIX_LIB_ROOT}/.env.arquantix"
  [[ -f "$f" ]] || { echo "arquantixrecovery"; return 0; }
  local v
  v="$( (grep -E '^[[:space:]]*COMPOSE_PROJECT_NAME=' "$f" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  if [[ -z "$v" ]]; then
    echo "arquantixrecovery"
  else
    echo "$v"
  fi
}

# Fichier compose « officiel » lu depuis .env.arquantix (défaut : recovery, stable si namespace arquantix cassé).
arquantix_compose_file() {
  local f="${ARQUANTIX_LIB_ROOT}/.env.arquantix"
  local v
  [[ -f "$f" ]] || { echo "docker-compose.arquantix-recovery.yml"; return 0; }
  v="$( (grep -E '^[[:space:]]*ARQUANTIX_COMPOSE_FILE=' "$f" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  if [[ -z "$v" ]]; then
    echo "docker-compose.arquantix-recovery.yml"
  else
    echo "$v"
  fi
}

# CID d’un service pour le projet Compose attendu (.env.arquantix), ou vide.
arquantix_cid_for_service() {
  local svc="${1:-}"
  [[ -z "$svc" ]] && { echo ""; return 0; }
  if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    echo ""
    return 0
  fi
  local proj
  proj="$(arquantix_expected_compose_project)"
  docker ps -q \
    --filter "label=com.docker.compose.project=${proj}" \
    --filter "label=com.docker.compose.service=${svc}" 2>/dev/null | head -1
}

# Label com.docker.compose.project sur un conteneur API du projet attendu (vide si absent).
arquantix_inspect_api_compose_project() {
  if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    echo ""
    return 0
  fi
  local cid
  cid="$(arquantix_cid_for_service arquantix-api)"
  [[ -z "$cid" ]] && { echo ""; return 0; }
  docker inspect "$cid" --format '{{index .Config.Labels "com.docker.compose.project"}}' 2>/dev/null || echo ""
}

# exec non interactif sur un service du compose officiel (depuis ARQUANTIX_LIB_ROOT).
arquantix_compose_exec() {
  local svc="$1"
  shift
  local cf
  cf="$(arquantix_compose_file)"
  (cd "$ARQUANTIX_LIB_ROOT" && docker compose --project-name "$(arquantix_expected_compose_project)" \
    --env-file .env.arquantix -f "$cf" exec -T "$svc" "$@")
}

# Projet Compose recovery (fallback) — aligné sur Makefile.arquantix (variable d’environnement optionnelle).
arquantix_recovery_compose_project() {
  echo "${ARQUANTIX_RECOVERY_PROJECT:-arquantixrecovery}"
}

# CID d’un service pour le projet recovery (docker-compose.arquantix-recovery.yml).
arquantix_cid_for_service_recovery() {
  local svc="${1:-}"
  [[ -z "$svc" ]] && { echo ""; return 0; }
  if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    echo ""
    return 0
  fi
  local proj
  proj="$(arquantix_recovery_compose_project)"
  docker ps -q \
    --filter "label=com.docker.compose.project=${proj}" \
    --filter "label=com.docker.compose.service=${svc}" 2>/dev/null | head -1
}

# exec sur la stack recovery — si projet recovery = projet attendu (.env), délègue au compose unique.
arquantix_compose_exec_recovery() {
  local svc="$1"
  shift
  local proj
  proj="$(arquantix_recovery_compose_project)"
  if [[ "$proj" == "$(arquantix_expected_compose_project)" ]]; then
    arquantix_compose_exec "$svc" "$@"
    return
  fi
  (cd "$ARQUANTIX_LIB_ROOT" && docker compose --project-name "$proj" \
    --env-file .env.arquantix -f docker-compose.arquantix-recovery.yml exec -T "$svc" "$@")
}

arquantix_api_container_running() {
  command -v docker >/dev/null 2>&1 || return 1
  docker info >/dev/null 2>&1 || return 1
  local proj
  proj="$(arquantix_expected_compose_project)"
  [[ -n "$(docker ps -q --filter "label=com.docker.compose.project=${proj}" --filter "label=com.docker.compose.service=arquantix-api" 2>/dev/null)" ]]
}

# Lignes docker compose ls -a pour les fichiers Arquantix (principal ou recovery).
arquantix_compose_ls_rows_for_arquantix_file() {
  command -v docker >/dev/null 2>&1 || return 0
  docker info >/dev/null 2>&1 || return 0
  local fmt tab
  tab="$(printf '\t')"
  fmt="{{.Name}}${tab}{{.Status}}${tab}{{.ConfigFiles}}"
  docker compose ls -a --format "$fmt" 2>/dev/null | while IFS= read -r line; do
    [[ "$line" == *"docker-compose.arquantix.yml"* ]] || [[ "$line" == *"docker-compose.arquantix-recovery.yml"* ]] || continue
    printf '%s\n' "$line"
  done
}
