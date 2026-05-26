#!/usr/bin/env bash
# Attache BASE_RPC_URL* à la task ECS arquantix-api (réconciliation Privy wallet).
#
# Usage :
#   ./scripts/arquantix-sync-privy-wallet-rpc.sh
#
# Lit BASE_RPC_URL depuis .env.arquantix si absent de l'environnement.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECS_CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
ECS_SERVICE="${ECS_SERVICE:-arquantix-api}"
ECS_TASKDEF_FAMILY="${ECS_TASKDEF_FAMILY:-arquantix-api}"
ECS_CONTAINER_NAME="${ECS_CONTAINER_NAME:-arquantix-api}"

SECRET_BASE_RPC_PRIMARY_NAME="${BASE_RPC_URL_PRIMARY_SECRET_NAME:-arquantix/prod/base-rpc-url-primary}"
SECRET_BASE_RPC_FALLBACK_NAME="${BASE_RPC_URL_FALLBACK_SECRET_NAME:-arquantix/prod/base-rpc-url-fallback}"

load_env_file() {
  local file=$1
  [[ -f "$file" ]] || return 0
  set -a
  # shellcheck disable=SC1090
  source "$file"
  set +a
}

secret_arn() {
  aws secretsmanager describe-secret --secret-id "$1" --region "$AWS_REGION" --query 'ARN' --output text
}

upsert_secret() {
  local name=$1
  local value=$2
  if [[ -z "$value" ]]; then
    echo "  skip $name (valeur vide)"
    return 0
  fi
  if aws secretsmanager describe-secret --secret-id "$name" --region "$AWS_REGION" >/dev/null 2>&1; then
    aws secretsmanager put-secret-value --secret-id "$name" --secret-string "$value" --region "$AWS_REGION" >/dev/null
    echo "  updated $name"
  else
    aws secretsmanager create-secret \
      --name "$name" \
      --description "Base mainnet RPC for arquantix-api Privy reconciliation" \
      --secret-string "$value" \
      --region "$AWS_REGION" >/dev/null
    echo "  created $name"
  fi
}

load_env_file "$ROOT_DIR/.env.arquantix"

BASE_RPC_URL_PRIMARY="${BASE_RPC_URL_PRIMARY:-${BASE_RPC_URL:-}}"
BASE_RPC_URL_FALLBACK="${BASE_RPC_URL_FALLBACK:-https://mainnet.base.org}"

if [[ -z "${BASE_RPC_URL_PRIMARY:-}" ]]; then
  echo "BASE_RPC_URL ou BASE_RPC_URL_PRIMARY requis (env ou .env.arquantix)." >&2
  exit 1
fi

echo "==> Secrets Manager (region=$AWS_REGION)"
upsert_secret "$SECRET_BASE_RPC_PRIMARY_NAME" "$BASE_RPC_URL_PRIMARY"
upsert_secret "$SECRET_BASE_RPC_FALLBACK_NAME" "$BASE_RPC_URL_FALLBACK"

BASE_RPC_PRIMARY_ARN=$(secret_arn "$SECRET_BASE_RPC_PRIMARY_NAME")
BASE_RPC_FALLBACK_ARN=$(secret_arn "$SECRET_BASE_RPC_FALLBACK_NAME")

echo ""
echo "==> Mise à jour task definition ECS ($ECS_TASKDEF_FAMILY)"
TD_JSON=$(aws ecs describe-task-definition --task-definition "$ECS_TASKDEF_FAMILY" --region "$AWS_REGION" --query 'taskDefinition' --output json)

NEW_TD_JSON=$(python3 - <<'PY' "$TD_JSON" "$BASE_RPC_PRIMARY_ARN" "$BASE_RPC_FALLBACK_ARN"
import json
import sys

td = json.loads(sys.argv[1])
primary_arn = sys.argv[2]
fallback_arn = sys.argv[3]
container_name = "arquantix-api"

for c in td["containerDefinitions"]:
    if c["name"] != container_name:
        continue
    secrets = {s["name"]: s for s in c.get("secrets") or []}
    for name, arn in (
        ("BASE_RPC_URL", primary_arn),
        ("BASE_RPC_URL_PRIMARY", primary_arn),
        ("BASE_RPC_URL_FALLBACK", fallback_arn),
    ):
        secrets[name] = {"name": name, "valueFrom": arn}
    c["secrets"] = list(secrets.values())
    break

for key in (
    "taskDefinitionArn",
    "revision",
    "status",
    "requiresAttributes",
    "compatibilities",
    "registeredAt",
    "registeredBy",
):
    td.pop(key, None)
print(json.dumps(td))
PY
)

NEW_ARN=$(aws ecs register-task-definition --region "$AWS_REGION" --cli-input-json "$NEW_TD_JSON" --query 'taskDefinition.taskDefinitionArn' --output text)
echo "  registered: $NEW_ARN"

aws ecs update-service \
  --region "$AWS_REGION" \
  --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" \
  --task-definition "$NEW_ARN" \
  --force-new-deployment >/dev/null

echo "  service $ECS_SERVICE updated (force-new-deployment)"
echo ""
echo "Done. BASE_RPC_URL* attaché à arquantix-api."
