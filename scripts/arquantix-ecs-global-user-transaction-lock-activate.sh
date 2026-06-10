#!/usr/bin/env bash
# Active la file transactionnelle globale user (swap LI.FI + bundle) pour TOUS les clients.
#
# Flag : GLOBAL_USER_TRANSACTION_LOCK_ENABLED=true
# Prérequis : code financial_transaction_global_lock + lifi_swap_global_lock déployé.
#
# Usage :
#   ./scripts/arquantix-ecs-global-user-transaction-lock-activate.sh
#   ./scripts/arquantix-ecs-global-user-transaction-lock-activate.sh arquantix-api:180
#
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
ECS_CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
ECS_SERVICE="${ECS_SERVICE:-arquantix-api}"
FLAG_NAME="GLOBAL_USER_TRANSACTION_LOCK_ENABLED"

if [[ -n "${1:-}" ]]; then
  BASE_TD="$1"
else
  BASE_TD=$(aws ecs describe-services \
    --region "$AWS_REGION" \
    --cluster "$ECS_CLUSTER" \
    --services "$ECS_SERVICE" \
    --query 'services[0].taskDefinition' \
    --output text)
  BASE_TD="${BASE_TD##*/}"
fi

echo "==> Baseline TD: $BASE_TD"

TD_JSON=$(aws ecs describe-task-definition \
  --region "$AWS_REGION" \
  --task-definition "$BASE_TD" \
  --query 'taskDefinition' \
  --output json)

NEW_TD_JSON=$(python3 - <<'PY' "$TD_JSON" "$FLAG_NAME"
import json, sys
td = json.loads(sys.argv[1])
flag = sys.argv[2]
for key in (
    "taskDefinitionArn", "revision", "status", "requiresAttributes",
    "compatibilities", "registeredAt", "registeredBy", "deregisteredAt",
):
    td.pop(key, None)
container = next(c for c in td["containerDefinitions"] if c["name"] == "arquantix-api")
env = {item["name"]: item["value"] for item in container.get("environment", [])}
env[flag] = "true"
container["environment"] = [{"name": k, "value": v} for k, v in sorted(env.items())]
print(json.dumps(td))
PY
)

NEW_ARN=$(aws ecs register-task-definition \
  --region "$AWS_REGION" \
  --cli-input-json "$NEW_TD_JSON" \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)

echo "==> Registered: $NEW_ARN"
echo "    $FLAG_NAME=true (tous les clients)"

aws ecs update-service \
  --region "$AWS_REGION" \
  --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" \
  --task-definition "$NEW_ARN" \
  --force-new-deployment \
  --query 'service.{taskDefinition:taskDefinition,desiredCount:desiredCount}' \
  --output json

echo "==> Waiting services-stable..."
aws ecs wait services-stable --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE"

REV=$(echo "$NEW_ARN" | awk -F: '{print $NF}')
echo "OK arquantix-api:$REV — file globale user ON pour tous les clients"
echo "Verify:"
echo "  LEGACY_GLOBAL_LOCK_VERIFY_MODE=post_activation \\"
echo "    ./scripts/arquantix-ecs-legacy-global-lock-activation-verify.sh"
