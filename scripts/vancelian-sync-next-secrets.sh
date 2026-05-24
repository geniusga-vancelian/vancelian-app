#!/usr/bin/env bash
# Met à jour la task ECS vancelian-next (app.vancelian.finance + console.vancelian.finance).
#
# Usage :
#   ./scripts/vancelian-sync-next-secrets.sh
#
# Env optionnel :
#   PRIVY_WEB_CLIENT_ID=...          # client web Privy (Allowed origins app.*)
#   NEXT_PUBLIC_PRIVY_WEB_CLIENT_ID=...
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECS_CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
ECS_SERVICE="${ECS_SERVICE:-vancelian-next}"
ECS_TASKDEF_FAMILY="${ECS_TASKDEF_FAMILY:-vancelian-next}"

SECRET_PRIVY_APP_ID_NAME="${PRIVY_APP_ID_SECRET_NAME:-arquantix/prod/privy-app-id}"
SECRET_PRIVY_WEB_CLIENT_NAME="${PRIVY_WEB_CLIENT_ID_SECRET_NAME:-arquantix/prod/privy-web-client-id}"

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
    return 0
  fi
  if aws secretsmanager describe-secret --secret-id "$name" --region "$AWS_REGION" >/dev/null 2>&1; then
    aws secretsmanager put-secret-value --secret-id "$name" --secret-string "$value" --region "$AWS_REGION" >/dev/null
    echo "  updated $name"
  else
    aws secretsmanager create-secret \
      --name "$name" \
      --description "Privy web client ID for vancelian-next (app.vancelian.finance)" \
      --secret-string "$value" \
      --region "$AWS_REGION" >/dev/null
    echo "  created $name"
  fi
}

load_env_file "$ROOT_DIR/.env.arquantix"

PRIVY_APP_ID="${PRIVY_APP_ID:-$(aws secretsmanager get-secret-value --secret-id "$SECRET_PRIVY_APP_ID_NAME" --region "$AWS_REGION" --query SecretString --output text 2>/dev/null || true)}"
PRIVY_WEB_CLIENT_ID="${NEXT_PUBLIC_PRIVY_WEB_CLIENT_ID:-${PRIVY_WEB_CLIENT_ID:-}}"

if [[ -z "$PRIVY_APP_ID" ]]; then
  echo "PRIVY_APP_ID requis (env, .env.arquantix ou Secrets Manager)." >&2
  exit 1
fi

echo "==> Secrets Manager (region=$AWS_REGION)"
upsert_secret "$SECRET_PRIVY_APP_ID_NAME" "$PRIVY_APP_ID"
if [[ -n "$PRIVY_WEB_CLIENT_ID" ]]; then
  upsert_secret "$SECRET_PRIVY_WEB_CLIENT_NAME" "$PRIVY_WEB_CLIENT_ID"
else
  echo "  skip $SECRET_PRIVY_WEB_CLIENT_NAME (PRIVY_WEB_CLIENT_ID vide — optionnel si appId seul suffit)"
fi

PRIVY_APP_ID_ARN=$(aws secretsmanager describe-secret --secret-id "$SECRET_PRIVY_APP_ID_NAME" --region "$AWS_REGION" --query 'ARN' --output text)
PRIVY_WEB_CLIENT_ARN=""
if [[ -n "$PRIVY_WEB_CLIENT_ID" ]] && aws secretsmanager describe-secret --secret-id "$SECRET_PRIVY_WEB_CLIENT_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
  PRIVY_WEB_CLIENT_ARN=$(aws secretsmanager describe-secret --secret-id "$SECRET_PRIVY_WEB_CLIENT_NAME" --region "$AWS_REGION" --query 'ARN' --output text)
fi

echo ""
echo "==> Mise à jour task definition ECS ($ECS_TASKDEF_FAMILY)"
TD_JSON=$(aws ecs describe-task-definition --task-definition "$ECS_TASKDEF_FAMILY" --region "$AWS_REGION" --query 'taskDefinition' --output json)

NEW_TD_JSON=$(python3 - <<'PY' "$TD_JSON" "$PRIVY_APP_ID_ARN" "$PRIVY_APP_ID" "$PRIVY_WEB_CLIENT_ARN" "$PRIVY_WEB_CLIENT_ID"
import json
import sys

td = json.loads(sys.argv[1])
privy_app_arn = sys.argv[2]
privy_app_id = sys.argv[3]
privy_web_client_arn = sys.argv[4]
privy_web_client_id = sys.argv[5]

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
        "NEXT_PUBLIC_PRIVY_APP_ID": privy_app_id,
        "NEXT_PUBLIC_API_URL": env.get("NEXT_PUBLIC_API_URL", "https://api.arquantix.com"),
        "NEXT_PUBLIC_BACKEND_URL": env.get("NEXT_PUBLIC_BACKEND_URL", "https://api.arquantix.com"),
        "NEXT_PUBLIC_SITE_URL": env.get("NEXT_PUBLIC_SITE_URL", "https://vancelian.finance"),
    }
)
if privy_web_client_id:
    env["NEXT_PUBLIC_PRIVY_WEB_CLIENT_ID"] = privy_web_client_id
    env["PRIVY_WEB_CLIENT_ID"] = privy_web_client_id
container["environment"] = [{"name": k, "value": v} for k, v in sorted(env.items())]

secrets = [item for item in container.get("secrets", []) if item.get("name") not in {"PRIVY_APP_ID", "PRIVY_WEB_CLIENT_ID"}]
secrets.append({"name": "PRIVY_APP_ID", "valueFrom": privy_app_arn})
if privy_web_client_arn:
    secrets.append({"name": "PRIVY_WEB_CLIENT_ID", "valueFrom": privy_web_client_arn})
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
echo "  NEXT_PUBLIC_PRIVY_APP_ID=$PRIVY_APP_ID"
echo "  NEXT_PUBLIC_API_URL=https://api.arquantix.com"
echo "  NEXT_PUBLIC_BACKEND_URL=https://api.arquantix.com"
echo "  NEXT_PUBLIC_SITE_URL=https://vancelian.finance"
if [[ -n "$PRIVY_WEB_CLIENT_ID" ]]; then
  echo "  NEXT_PUBLIC_PRIVY_WEB_CLIENT_ID=$PRIVY_WEB_CLIENT_ID"
fi
echo ""
echo "Secret ECS (secrets[]) :"
echo "  PRIVY_APP_ID -> $PRIVY_APP_ID_ARN"
if [[ -n "$PRIVY_WEB_CLIENT_ARN" ]]; then
  echo "  PRIVY_WEB_CLIENT_ID -> $PRIVY_WEB_CLIENT_ARN"
fi
echo ""
echo "Note : le bundle client Privy (NEXT_PUBLIC_*) est figé au build Docker."
echo "Pour un client Privy à jour côté navigateur, relancer le workflow vancelian-next-deploy"
echo "avec le secret GitHub VANCELIAN_PRIVY_APP_ID=$PRIVY_APP_ID"
