#!/usr/bin/env bash
# Wrapper ops — tick observabilité DeFi (prod-safe).
#
# Usage (depuis la racine du repo) :
#   ./scripts/run_defi_observability_tick_prod.sh              # dry-run (défaut)
#   ./scripts/run_defi_observability_tick_prod.sh --execute    # --no-dry-run + max-duration 480s
#   ./scripts/run_defi_observability_tick_prod.sh --ecs-once   # RunTask ECS arquantix-api (one-shot)
#
# Doc : docs/arquantix/DEFI_OBSERVABILITY_OPS_GO_LIVE.md
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/services/arquantix/api"
MAX_DURATION="${DEFI_TICK_MAX_DURATION_SECONDS:-480}"

load_env_file() {
  local file=$1
  [[ -f "$file" ]] || return 0
  set -a
  # shellcheck disable=SC1090
  source "$file"
  set +a
}

_truthy() {
  case "$(echo "${1:-}" | tr '[:upper:]' '[:lower:]')" in
    1 | true | yes | on) return 0 ;;
    *) return 1 ;;
  esac
}

_resolve_base_rpc() {
  if [[ -n "${BASE_RPC_URL:-}" ]]; then
    echo "$BASE_RPC_URL"
    return 0
  fi
  if [[ -n "${BASE_RPC_URL_PRIMARY:-}" ]]; then
    echo "$BASE_RPC_URL_PRIMARY"
    return 0
  fi
  if [[ -n "${NEXT_PUBLIC_BASE_RPC_URL:-}" ]]; then
    echo "$NEXT_PUBLIC_BASE_RPC_URL"
    return 0
  fi
  return 1
}

preflight() {
  local require_indexer=$1
  local errors=0

  if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "ERREUR: DATABASE_URL manquant (export ou .env.arquantix)." >&2
    errors=$((errors + 1))
  fi

  if _truthy "${LIFI_SWAPS_MOCK:-}"; then
    echo "ERREUR: LIFI_SWAPS_MOCK interdit en prod." >&2
    errors=$((errors + 1))
  fi
  if _truthy "${BUNDLE_LIFI_SYNC_MOCK:-}"; then
    echo "ERREUR: BUNDLE_LIFI_SYNC_MOCK interdit en prod." >&2
    errors=$((errors + 1))
  fi

  if [[ "$require_indexer" == "1" ]]; then
    if ! _truthy "${ONCHAIN_INDEXER_BASE_ENABLED:-false}"; then
      echo "ERREUR: ONCHAIN_INDEXER_BASE_ENABLED doit être true pour --execute / --ecs-once." >&2
      errors=$((errors + 1))
    fi
    if ! _resolve_base_rpc >/dev/null; then
      echo "ERREUR: RPC Base manquant (BASE_RPC_URL, BASE_RPC_URL_PRIMARY ou NEXT_PUBLIC_BASE_RPC_URL)." >&2
      errors=$((errors + 1))
    fi
  fi

  if [[ "$errors" -gt 0 ]]; then
    exit 1
  fi
}

run_local_tick() {
  local extra_args=("$@")
  preflight "${PREFLIGHT_INDEXER:-0}"
  cd "$API_DIR"
  echo "==> Tick observabilité DeFi (${extra_args[*]:-dry-run})"
  python3 -m scripts.defi_observability_tick "${extra_args[@]}"
}

run_ecs_once() {
  preflight 1
  local cmd="cd /app && python3 -m scripts.defi_observability_tick --no-dry-run --max-duration-seconds ${MAX_DURATION}"
  echo "==> ECS one-shot arquantix-api"
  exec "$ROOT_DIR/scripts/arquantix-ecs-run-job.sh" arquantix-api arquantix-api "$cmd"
}

MODE="dry-run"
for arg in "$@"; do
  case "$arg" in
    --execute)
      MODE="execute"
      ;;
    --ecs-once)
      MODE="ecs-once"
      ;;
    -h | --help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *)
      echo "Option inconnue: $arg (utilisez --execute ou --ecs-once)" >&2
      exit 1
      ;;
  esac
done

load_env_file "$ROOT_DIR/.env.arquantix"

case "$MODE" in
  dry-run)
    PREFLIGHT_INDEXER=0
    run_local_tick --dry-run
    ;;
  execute)
    PREFLIGHT_INDEXER=1
    run_local_tick --no-dry-run --max-duration-seconds "$MAX_DURATION"
    ;;
  ecs-once)
    run_ecs_once
    ;;
esac
