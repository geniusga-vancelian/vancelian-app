#!/usr/bin/env bash
# PR3 — Activer enqueue-and-wait sur arquantix-api.
# Ajoute LIFI_ENQUEUE_AND_WAIT_ENABLED=true en préservant image + env + secrets.
# Base : task def actuellement déployée par le service (auto-détectée).
# Prérequis (déjà ON en prod) : LIFI_AUTHORITATIVE_EXECUTION_ENABLED=true + GLOBAL_USER_TRANSACTION_LOCK_ENABLED=true.
# Rollback : arquantix-ecs-pr3-enqueue-wait-rollback.sh
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
ECS_CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
ECS_SERVICE="${ECS_SERVICE:-arquantix-api}"
FLAG_VALUE="${FLAG_VALUE:-true}"

CURRENT_TD=$(aws ecs describe-services --region "$AWS_REGION" --cluster "$ECS_CLUSTER" \
  --services "$ECS_SERVICE" --query 'services[0].taskDefinition' --output text)
echo "==> Base TD (live): $CURRENT_TD  | LIFI_ENQUEUE_AND_WAIT_ENABLED=$FLAG_VALUE"

TD_JSON=$(aws ecs describe-task-definition --region "$AWS_REGION" \
  --task-definition "$CURRENT_TD" --query 'taskDefinition' --output json)

NEW_TD_JSON=$(FLAG_VALUE="$FLAG_VALUE" python3 - "$TD_JSON" <<'PY'
import json, os, sys
td = json.loads(sys.argv[1])
for key in (
    "taskDefinitionArn", "revision", "status", "requiresAttributes",
    "compatibilities", "registeredAt", "registeredBy", "deregisteredAt",
):
    td.pop(key, None)
container = td["containerDefinitions"][0]
env = {item["name"]: item["value"] for item in container.get("environment", [])}
env["LIFI_ENQUEUE_AND_WAIT_ENABLED"] = os.environ["FLAG_VALUE"]
container["environment"] = [{"name": k, "value": v} for k, v in sorted(env.items())]
print(json.dumps(td))
PY
)

NEW_ARN=$(aws ecs register-task-definition --region "$AWS_REGION" \
  --cli-input-json "$NEW_TD_JSON" \
  --query 'taskDefinition.taskDefinitionArn' --output text)
echo "==> Registered: $NEW_ARN"

aws ecs update-service --region "$AWS_REGION" --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" --task-definition "$NEW_ARN" --force-new-deployment \
  --query 'service.{taskDefinition:taskDefinition,desiredCount:desiredCount}' --output json

echo "==> Waiting services-stable..."
aws ecs wait services-stable --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE"
REV=$(echo "$NEW_ARN" | awk -F: '{print $NF}')
echo "OK arquantix-api:$REV LIFI_ENQUEUE_AND_WAIT_ENABLED=$FLAG_VALUE"
