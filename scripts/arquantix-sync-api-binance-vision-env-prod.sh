#!/usr/bin/env bash
# Active les endpoints Binance « vision » sur arquantix-api (REST fallback + cohérence prod US).
#
# Usage : ./scripts/arquantix-sync-api-binance-vision-env-prod.sh
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
ECS_CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
ECS_SERVICE="${ECS_SERVICE:-arquantix-api}"
ECS_TASKDEF_FAMILY="${ECS_TASKDEF_FAMILY:-arquantix-api}"
DRY_RUN="${DRY_RUN:-0}"

echo "==> Binance vision endpoints sur $ECS_TASKDEF_FAMILY"

TD_JSON=$(aws ecs describe-task-definition \
  --region "$AWS_REGION" \
  --task-definition "$ECS_TASKDEF_FAMILY" \
  --query 'taskDefinition' \
  --output json)

NEW_TD_JSON=$(python3 - <<'PY' "$TD_JSON"
import json
import sys

td = json.loads(sys.argv[1])
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
env["BINANCE_USE_VISION_ENDPOINTS"] = "true"
env["BINANCE_REST_BASE_URL"] = "https://data-api.binance.vision"
env["BINANCE_WS_BASE_URL"] = "wss://data-stream.binance.vision"
container["environment"] = [{"name": k, "value": v} for k, v in sorted(env.items())]
print(json.dumps(td))
PY
)

if [[ "$DRY_RUN" == "1" ]]; then
  echo "$NEW_TD_JSON" | python3 -c "import json,sys; c=json.load(sys.stdin)['containerDefinitions'][0]; [print(e) for e in c['environment'] if 'BINANCE' in e['name']]"
  exit 0
fi

TMP_TD=$(mktemp)
trap 'rm -f "$TMP_TD"' EXIT
echo "$NEW_TD_JSON" > "$TMP_TD"
NEW_TASK_ARN=$(aws ecs register-task-definition \
  --region "$AWS_REGION" \
  --cli-input-json "file://$TMP_TD" \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)
echo "  registered $NEW_TASK_ARN"

aws ecs update-service \
  --region "$AWS_REGION" \
  --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" \
  --task-definition "$NEW_TASK_ARN" \
  --force-new-deployment \
  --output text \
  --query 'service.serviceName'

echo "==> Attente stabilisation API…"
aws ecs wait services-stable --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE"
echo "OK — $ECS_SERVICE utilise data-api.binance.vision / data-stream.binance.vision"
