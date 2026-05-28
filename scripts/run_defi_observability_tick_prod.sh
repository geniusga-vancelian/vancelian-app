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

verify_ecs_arquantix_api() {
  local aws_region="${AWS_REGION:-us-east-1}"
  local family="${ECS_TASKDEF_FAMILY:-arquantix-api}"
  python3 - <<'PY' "$aws_region" "$family"
import json
import subprocess
import sys

region, family = sys.argv[1], sys.argv[2]
td = json.loads(
    subprocess.check_output(
        [
            "aws", "ecs", "describe-task-definition",
            "--task-definition", family,
            "--region", region,
            "--query", "taskDefinition",
            "--output", "json",
        ],
        text=True,
    )
)
container = next(
    (c for c in td["containerDefinitions"] if c["name"] == "arquantix-api"),
    None,
)
if not container:
    print("ERREUR: conteneur arquantix-api introuvable dans la task definition.", file=sys.stderr)
    sys.exit(1)

env = {e["name"]: e.get("value", "") for e in (container.get("environment") or [])}
secrets = {s["name"] for s in (container.get("secrets") or [])}
errors = []

for mock in ("LIFI_SWAPS_MOCK", "BUNDLE_LIFI_SYNC_MOCK"):
    if env.get(mock, "").strip().lower() in ("1", "true", "yes", "on"):
        errors.append(f"{mock}=truthy sur la task ECS (interdit prod)")

if "DATABASE_URL" not in secrets and not env.get("DATABASE_URL"):
    errors.append("DATABASE_URL absent (secret ou env)")

has_rpc = bool(
    {"BASE_RPC_URL", "BASE_RPC_URL_PRIMARY"} & secrets
    or env.get("BASE_RPC_URL")
    or env.get("BASE_RPC_URL_PRIMARY")
)
if not has_rpc:
    errors.append("BASE_RPC_URL / BASE_RPC_URL_PRIMARY absent (secret ou env)")

indexer = env.get("ONCHAIN_INDEXER_BASE_ENABLED", "").strip().lower()
indexer_ok = indexer in ("1", "true", "yes", "on")
if indexer_ok:
    print("OK ONCHAIN_INDEXER_BASE_ENABLED=true sur la task ECS")
else:
    print(
        "AVERTISSEMENT: ONCHAIN_INDEXER_BASE_ENABLED absent ou false sur la task — "
        "override RunTask=true pour ce one-shot.",
        file=sys.stderr,
    )

if errors:
    for e in errors:
        print(f"ERREUR: {e}", file=sys.stderr)
    sys.exit(1)

print("OK ECS preflight: DATABASE_URL (secret), RPC Base (secret), mocks désactivés")
PY
}

run_ecs_once() {
  local tick_mode="${1:-execute}"
  verify_ecs_arquantix_api

  local tick_args="--dry-run"
  if [[ "$tick_mode" == "execute" ]]; then
    tick_args="--no-dry-run --max-duration-seconds ${MAX_DURATION}"
  fi

  local cmd="cd /app && python3 -m scripts.defi_observability_tick ${tick_args}"
  echo "==> ECS one-shot arquantix-api (${tick_args})"

  AWS_REGION="${AWS_REGION:-us-east-1}"
  ECS_CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
  ECS_SERVICE="${ECS_SERVICE:-arquantix-api}"
  CONTAINER_NAME="${ECS_CONTAINER_NAME:-arquantix-api}"

  TASK_DEF=$(aws ecs describe-services \
    --cluster "$ECS_CLUSTER" \
    --services "$ECS_SERVICE" \
    --region "$AWS_REGION" \
    --query 'services[0].taskDefinition' \
    --output text)

  NET=$(aws ecs describe-services \
    --cluster "$ECS_CLUSTER" \
    --services "$ECS_SERVICE" \
    --region "$AWS_REGION" \
    --query 'services[0].networkConfiguration.awsvpcConfiguration' \
    --output json)

  SUBNET=$(echo "$NET" | python3 -c "import json,sys; print(json.load(sys.stdin)['subnets'][0])")
  SG=$(echo "$NET" | python3 -c "import json,sys; print(json.load(sys.stdin)['securityGroups'][0])")
  PUBLIC_IP=$(echo "$NET" | python3 -c "import json,sys; print(json.load(sys.stdin).get('assignPublicIp','ENABLED'))")

  OVERRIDES=$(CMD="$cmd" CONTAINER_NAME="$CONTAINER_NAME" python3 - <<'PY'
import json, os
print(json.dumps({
  "containerOverrides": [{
    "name": os.environ["CONTAINER_NAME"],
    "command": ["sh", "-c", os.environ["CMD"]],
    "environment": [
      {"name": "ONCHAIN_INDEXER_BASE_ENABLED", "value": "true"},
    ],
  }]
}))
PY
)

  echo "  task definition : $TASK_DEF"
  echo "  override env    : ONCHAIN_INDEXER_BASE_ENABLED=true"
  echo "  command         : $cmd"

  TASK_ARN=$(aws ecs run-task \
    --region "$AWS_REGION" \
    --cluster "$ECS_CLUSTER" \
    --task-definition "$TASK_DEF" \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET],securityGroups=[$SG],assignPublicIp=$PUBLIC_IP}" \
    --overrides "$OVERRIDES" \
    --query 'tasks[0].taskArn' \
    --output text)

  if [[ -z "$TASK_ARN" || "$TASK_ARN" == "None" ]]; then
    echo "ERREUR: RunTask n'a pas démarré." >&2
    exit 1
  fi

  echo "  task ARN : $TASK_ARN"
  echo "  logs     : /ecs/$ECS_SERVICE (CloudWatch)"
  aws ecs wait tasks-stopped --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --tasks "$TASK_ARN"

  EXIT_CODE=$(aws ecs describe-tasks \
    --region "$AWS_REGION" \
    --cluster "$ECS_CLUSTER" \
    --tasks "$TASK_ARN" \
    --query 'tasks[0].containers[0].exitCode' \
    --output text)

  STOP_REASON=$(aws ecs describe-tasks \
    --region "$AWS_REGION" \
    --cluster "$ECS_CLUSTER" \
    --tasks "$TASK_ARN" \
    --query 'tasks[0].stoppedReason' \
    --output text)

  STREAM=$(aws ecs describe-tasks \
    --region "$AWS_REGION" \
    --cluster "$ECS_CLUSTER" \
    --tasks "$TASK_ARN" \
    --query 'tasks[0].containers[0].logStreamName' \
    --output text 2>/dev/null || true)

  if [[ -n "$STREAM" && "$STREAM" != "None" ]]; then
    sleep 3
    echo "==> Dernières lignes CloudWatch"
    aws logs get-log-events \
      --log-group-name "/ecs/$ECS_SERVICE" \
      --log-stream-name "$STREAM" \
      --limit 40 \
      --query 'events[*].message' \
      --output text 2>/dev/null || true
  fi

  case "$EXIT_CODE" in
    0 | 2)
      echo "OK tick ECS exit=$EXIT_CODE ($STOP_REASON) — 2=degraded acceptable"
      ;;
    *)
      echo "ERREUR: tick ECS exit=$EXIT_CODE ($STOP_REASON)" >&2
      exit 1
      ;;
  esac
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
    --ecs-dry-run)
      MODE="ecs-dry-run"
      ;;
    -h | --help)
      sed -n '2,14p' "$0"
      exit 0
      ;;
    *)
      echo "Option inconnue: $arg (utilisez --execute, --ecs-once ou --ecs-dry-run)" >&2
      exit 1
      ;;
  esac
done

case "$MODE" in
  dry-run)
    load_env_file "$ROOT_DIR/.env.arquantix"
    PREFLIGHT_INDEXER=0
    run_local_tick --dry-run
    ;;
  execute)
    load_env_file "$ROOT_DIR/.env.arquantix"
    PREFLIGHT_INDEXER=1
    run_local_tick --no-dry-run --max-duration-seconds "$MAX_DURATION"
    ;;
  ecs-dry-run)
    run_ecs_once dry-run
    ;;
  ecs-once)
    run_ecs_once execute
    ;;
esac
