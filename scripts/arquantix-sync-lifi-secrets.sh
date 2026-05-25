#!/usr/bin/env bash
# Crée ou met à jour les secrets LI.FI API dans AWS Secrets Manager (us-east-1)
# et attache LIFI_* à la task ECS arquantix-api (backend app.vancelian.finance).
#
# Usage (recommandé) :
#   LIFI_API_KEY=... \
#   LIFI_INTEGRATOR_ID=vancelian.finance \
#   LIFI_INTEGRATION_URL=https://app.vancelian.finance/ \
#   LIFI_FEE_BPS=25 \
#   LIFI_RPM_LIMIT=100 \
#   SWAP_FEE_BPS=0 \
#   LIFI_SWAPS_MOCK=0 \
#   SWAP_V1_SAME_CHAIN_ONLY=1 \
#   SWAP_V1_PILOT_CHAINS=base,ethereum \
#   LIFI_SWAPS_ENABLED=1 \
#   ./scripts/arquantix-sync-lifi-secrets.sh
#
# Ou sans args : lit LIFI_* depuis .env.arquantix (repo root) si présent.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Overrides CLI à conserver si .env.arquantix est chargé ensuite.
_CLI_LIFI_SWAPS_MOCK="${LIFI_SWAPS_MOCK:-}"
_CLI_SWAP_FEE_BPS="${SWAP_FEE_BPS:-}"
_CLI_SWAP_V1_SAME_CHAIN_ONLY="${SWAP_V1_SAME_CHAIN_ONLY:-}"
_CLI_SWAP_V1_PILOT_CHAINS="${SWAP_V1_PILOT_CHAINS:-}"
_CLI_LIFI_SWAPS_ENABLED="${LIFI_SWAPS_ENABLED:-}"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECS_CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
ECS_SERVICE="${ECS_SERVICE:-arquantix-api}"
ECS_TASKDEF_FAMILY="${ECS_TASKDEF_FAMILY:-arquantix-api}"
ECS_CONTAINER_NAME="${ECS_CONTAINER_NAME:-arquantix-api}"

SECRET_API_KEY_NAME="${LIFI_API_KEY_SECRET_NAME:-arquantix/prod/lifi-api-key}"

DEFAULT_LIFI_INTEGRATOR_ID="vancelian.finance"
DEFAULT_LIFI_INTEGRATION_URL="https://app.vancelian.finance/"
DEFAULT_LIFI_FEE_BPS="25"
DEFAULT_LIFI_RPM_LIMIT="100"
DEFAULT_SWAP_FEE_BPS="0"
DEFAULT_LIFI_SWAPS_MOCK="0"
DEFAULT_SWAP_V1_SAME_CHAIN_ONLY="1"
DEFAULT_SWAP_V1_PILOT_CHAINS="base,ethereum"
DEFAULT_LIFI_SWAPS_ENABLED="1"

load_env_file() {
  local file=$1
  [[ -f "$file" ]] || return 0
  # shellcheck disable=SC1090
  set -a
  source "$file"
  set +a
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
      --description "LI.FI API key for arquantix-api ECS (vancelian.finance integrator)" \
      --secret-string "$value" \
      --region "$AWS_REGION" >/dev/null
    echo "  created $name"
  fi
}

if [[ -z "${LIFI_API_KEY:-}" ]]; then
  load_env_file "$ROOT_DIR/.env.arquantix"
fi

[[ -n "$_CLI_LIFI_SWAPS_MOCK" ]] && LIFI_SWAPS_MOCK="$_CLI_LIFI_SWAPS_MOCK"
[[ -n "$_CLI_SWAP_FEE_BPS" ]] && SWAP_FEE_BPS="$_CLI_SWAP_FEE_BPS"
[[ -n "$_CLI_SWAP_V1_SAME_CHAIN_ONLY" ]] && SWAP_V1_SAME_CHAIN_ONLY="$_CLI_SWAP_V1_SAME_CHAIN_ONLY"
[[ -n "$_CLI_SWAP_V1_PILOT_CHAINS" ]] && SWAP_V1_PILOT_CHAINS="$_CLI_SWAP_V1_PILOT_CHAINS"
[[ -n "$_CLI_LIFI_SWAPS_ENABLED" ]] && LIFI_SWAPS_ENABLED="$_CLI_LIFI_SWAPS_ENABLED"

LIFI_INTEGRATOR_ID="${LIFI_INTEGRATOR_ID:-$DEFAULT_LIFI_INTEGRATOR_ID}"
LIFI_INTEGRATION_URL="${LIFI_INTEGRATION_URL:-$DEFAULT_LIFI_INTEGRATION_URL}"
LIFI_FEE_BPS="${LIFI_FEE_BPS:-$DEFAULT_LIFI_FEE_BPS}"
LIFI_RPM_LIMIT="${LIFI_RPM_LIMIT:-$DEFAULT_LIFI_RPM_LIMIT}"
SWAP_FEE_BPS="${SWAP_FEE_BPS:-$DEFAULT_SWAP_FEE_BPS}"
LIFI_SWAPS_MOCK="${LIFI_SWAPS_MOCK:-$DEFAULT_LIFI_SWAPS_MOCK}"
SWAP_V1_SAME_CHAIN_ONLY="${SWAP_V1_SAME_CHAIN_ONLY:-$DEFAULT_SWAP_V1_SAME_CHAIN_ONLY}"
SWAP_V1_PILOT_CHAINS="${SWAP_V1_PILOT_CHAINS:-$DEFAULT_SWAP_V1_PILOT_CHAINS}"
LIFI_SWAPS_ENABLED="${LIFI_SWAPS_ENABLED:-$DEFAULT_LIFI_SWAPS_ENABLED}"

if [[ -z "${LIFI_API_KEY:-}" ]]; then
  echo "LIFI_API_KEY requis (env ou .env.arquantix)." >&2
  exit 1
fi

echo "==> Secrets Manager (region=$AWS_REGION)"
upsert_secret "$SECRET_API_KEY_NAME" "$LIFI_API_KEY"

LIFI_API_KEY_ARN=$(aws secretsmanager describe-secret --secret-id "$SECRET_API_KEY_NAME" --region "$AWS_REGION" --query 'ARN' --output text)
echo ""
echo "LIFI_API_KEY ARN: $LIFI_API_KEY_ARN"

echo ""
echo "==> Mise à jour task definition ECS ($ECS_TASKDEF_FAMILY)"
TD_JSON=$(aws ecs describe-task-definition --task-definition "$ECS_TASKDEF_FAMILY" --region "$AWS_REGION" --query 'taskDefinition' --output json)

NEW_TD_JSON=$(python3 - <<'PY' "$TD_JSON" "$LIFI_API_KEY_ARN" "$LIFI_INTEGRATOR_ID" "$LIFI_INTEGRATION_URL" "$LIFI_FEE_BPS" "$LIFI_RPM_LIMIT" "$SWAP_FEE_BPS" "$LIFI_SWAPS_MOCK" "$SWAP_V1_SAME_CHAIN_ONLY" "$SWAP_V1_PILOT_CHAINS" "$LIFI_SWAPS_ENABLED"
import json
import sys

td = json.loads(sys.argv[1])
api_key_arn = sys.argv[2]
integrator_id = sys.argv[3]
integration_url = sys.argv[4]
fee_bps = sys.argv[5]
rpm_limit = sys.argv[6]
swap_fee_bps = sys.argv[7]
swaps_mock = sys.argv[8]
same_chain_only = sys.argv[9]
pilot_chains = sys.argv[10]
swaps_enabled = sys.argv[11]

for key in (
    "taskDefinitionArn",
    "revision",
    "status",
    "requiresAttributes",
    "compatibilities",
    "registeredAt",
    "registeredBy",
    "deregisteredAt",
):
    td.pop(key, None)

container = td["containerDefinitions"][0]
env = {item["name"]: item["value"] for item in container.get("environment", [])}
env.update(
    {
        "LIFI_INTEGRATOR_ID": integrator_id,
        "LIFI_INTEGRATION_URL": integration_url,
        "LIFI_FEE_BPS": fee_bps,
        "LIFI_RPM_LIMIT": rpm_limit,
        "SWAP_FEE_BPS": swap_fee_bps,
        "LIFI_SWAPS_MOCK": swaps_mock,
        "SWAP_V1_SAME_CHAIN_ONLY": same_chain_only,
        "SWAP_V1_PILOT_CHAINS": pilot_chains,
        "LIFI_SWAPS_ENABLED": swaps_enabled,
    }
)
container["environment"] = [{"name": k, "value": v} for k, v in sorted(env.items())]

secrets = [item for item in container.get("secrets", []) if item.get("name") != "LIFI_API_KEY"]
secrets.append({"name": "LIFI_API_KEY", "valueFrom": api_key_arn})
container["secrets"] = secrets

print(json.dumps(td))
PY
)

NEW_TASK_ARN=$(aws ecs register-task-definition --region "$AWS_REGION" --cli-input-json "$NEW_TD_JSON" --query 'taskDefinition.taskDefinitionArn' --output text)
echo "  registered $NEW_TASK_ARN"

echo ""
echo "==> Redéploiement ECS ($ECS_CLUSTER / $ECS_SERVICE)"
aws ecs update-service \
  --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" \
  --task-definition "$NEW_TASK_ARN" \
  --force-new-deployment \
  --region "$AWS_REGION" \
  --query 'service.{serviceName:serviceName,taskDefinition:taskDefinition,desiredCount:desiredCount}' \
  --output json

echo ""
echo "Variables plain ECS (environment[]) :"
echo "  LIFI_INTEGRATOR_ID=$LIFI_INTEGRATOR_ID"
echo "  LIFI_INTEGRATION_URL=$LIFI_INTEGRATION_URL"
echo "  LIFI_FEE_BPS=$LIFI_FEE_BPS"
echo "  LIFI_RPM_LIMIT=$LIFI_RPM_LIMIT"
echo "  SWAP_FEE_BPS=$SWAP_FEE_BPS"
echo "  LIFI_SWAPS_MOCK=$LIFI_SWAPS_MOCK"
echo "  SWAP_V1_SAME_CHAIN_ONLY=$SWAP_V1_SAME_CHAIN_ONLY"
echo "  SWAP_V1_PILOT_CHAINS=$SWAP_V1_PILOT_CHAINS"
echo "  LIFI_SWAPS_ENABLED=$LIFI_SWAPS_ENABLED"
echo ""
echo "Secret ECS (secrets[]) :"
echo "  LIFI_API_KEY -> $LIFI_API_KEY_ARN"
echo ""
echo "Attendre la stabilité du service :"
echo "  aws ecs wait services-stable --cluster $ECS_CLUSTER --services $ECS_SERVICE --region $AWS_REGION"
