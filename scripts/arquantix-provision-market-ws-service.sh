#!/usr/bin/env bash
# Provisionne / met à jour le worker ECS Binance WebSocket (quotes live).
#
# Usage :
#   ./scripts/arquantix-provision-market-ws-service.sh
#   IMAGE_TAG=81d9a35ab ./scripts/arquantix-provision-market-ws-service.sh
#   DRY_RUN=1 ./scripts/arquantix-provision-market-ws-service.sh
#
# Prérequis : AWS CLI, droits ECS/Logs sur arquantix-cluster (us-east-1).
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
ECS_CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
API_SERVICE="${API_SERVICE:-arquantix-api}"
API_TASKDEF_FAMILY="${API_TASKDEF_FAMILY:-arquantix-api}"
MARKET_WS_SERVICE="${MARKET_WS_SERVICE:-arquantix-market-ws}"
MARKET_WS_TASKDEF_FAMILY="${MARKET_WS_TASKDEF_FAMILY:-arquantix-market-ws}"
MARKET_WS_CONTAINER="${MARKET_WS_CONTAINER:-arquantix-market-ws}"
ECR_REGISTRY="${ECR_REGISTRY:-411714852748.dkr.ecr.us-east-1.amazonaws.com}"
ECR_REPOSITORY="${ECR_REPOSITORY:-arquantix-api}"
LOG_GROUP="${LOG_GROUP:-/ecs/arquantix-market-ws}"
DRY_RUN="${DRY_RUN:-0}"
WAIT_STABLE="${WAIT_STABLE:-1}"

if [[ -z "${IMAGE_TAG:-}" ]]; then
  IMAGE_TAG=$(aws ecs describe-task-definition \
    --region "$AWS_REGION" \
    --task-definition "$API_TASKDEF_FAMILY" \
    --query 'taskDefinition.containerDefinitions[0].image' \
    --output text | sed -E 's/.*:([^:]+)$/\1/')
fi

echo "==> Binance market WS worker (ECS)"
echo "    cluster=$ECS_CLUSTER service=$MARKET_WS_SERVICE"
echo "    image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "[dry-run] Aucune modification AWS."
  exit 0
fi

if ! aws logs describe-log-groups --region "$AWS_REGION" --log-group-name-prefix "$LOG_GROUP" \
  --query "logGroups[?logGroupName=='$LOG_GROUP'].logGroupName" --output text | grep -q "$LOG_GROUP"; then
  echo "==> Création log group $LOG_GROUP"
  aws logs create-log-group --region "$AWS_REGION" --log-group-name "$LOG_GROUP" 2>/dev/null || true
fi

API_TD_JSON=$(aws ecs describe-task-definition \
  --region "$AWS_REGION" \
  --task-definition "$API_TASKDEF_FAMILY" \
  --query 'taskDefinition' \
  --output json)

NEW_TD_JSON=$(IMAGE_TAG="$IMAGE_TAG" \
  ECR_REGISTRY="$ECR_REGISTRY" \
  ECR_REPOSITORY="$ECR_REPOSITORY" \
  MARKET_WS_TASKDEF_FAMILY="$MARKET_WS_TASKDEF_FAMILY" \
  MARKET_WS_CONTAINER="$MARKET_WS_CONTAINER" \
  LOG_GROUP="$LOG_GROUP" \
  AWS_REGION="$AWS_REGION" \
  python3 - <<'PY' "$API_TD_JSON"
import json
import os
import sys

td = json.loads(sys.argv[1])
family = os.environ["MARKET_WS_TASKDEF_FAMILY"]
container_name = os.environ["MARKET_WS_CONTAINER"]
image = f"{os.environ['ECR_REGISTRY']}/{os.environ['ECR_REPOSITORY']}:{os.environ['IMAGE_TAG']}"
log_group = os.environ["LOG_GROUP"]
region = os.environ["AWS_REGION"]

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

td["family"] = family

api_container = td["containerDefinitions"][0]
env_list = api_container.get("environment") or []
env = {e["name"]: e["value"] for e in env_list}
env["MARKET_DATA_WS_WORKER"] = "1"
env["BINANCE_USE_VISION_ENDPOINTS"] = "true"
env["BINANCE_REST_BASE_URL"] = "https://data-api.binance.vision"
env["BINANCE_WS_BASE_URL"] = "wss://data-stream.binance.vision"
env.pop("PORT", None)

worker = {
    "name": container_name,
    "image": image,
    "essential": True,
    "cpu": 0,
    "command": ["sh", "-c", "exec python3 scripts/run_binance_ws_ingestion.py"],
    "environment": [{"name": k, "value": v} for k, v in sorted(env.items())],
    "secrets": api_container.get("secrets") or [],
    "mountPoints": [],
    "volumesFrom": [],
    "portMappings": [],
    "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
            "awslogs-group": log_group,
            "awslogs-region": region,
            "awslogs-stream-prefix": "ws",
        },
    },
    "healthCheck": {
        "command": [
            "CMD-SHELL",
            "pgrep -f run_binance_ws_ingestion.py >/dev/null || exit 1",
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 90,
    },
}

td["containerDefinitions"] = [worker]
print(json.dumps(td))
PY
)

TMP_TD=$(mktemp)
trap 'rm -f "$TMP_TD"' EXIT
echo "$NEW_TD_JSON" > "$TMP_TD"
NEW_TASK_ARN=$(aws ecs register-task-definition \
  --region "$AWS_REGION" \
  --cli-input-json "file://$TMP_TD" \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)
echo "==> Task definition enregistrée : $NEW_TASK_ARN"

NET_JSON=$(aws ecs describe-services \
  --region "$AWS_REGION" \
  --cluster "$ECS_CLUSTER" \
  --services "$API_SERVICE" \
  --query 'services[0].networkConfiguration' \
  --output json)

SERVICE_STATUS=$(aws ecs describe-services \
  --region "$AWS_REGION" \
  --cluster "$ECS_CLUSTER" \
  --services "$MARKET_WS_SERVICE" \
  --query 'services[0].status' \
  --output text 2>/dev/null || echo "MISSING")

if [[ "$SERVICE_STATUS" == "MISSING" || "$SERVICE_STATUS" == "None" || -z "$SERVICE_STATUS" ]]; then
  echo "==> Création service ECS $MARKET_WS_SERVICE"
  aws ecs create-service \
    --region "$AWS_REGION" \
    --cluster "$ECS_CLUSTER" \
    --service-name "$MARKET_WS_SERVICE" \
    --task-definition "$NEW_TASK_ARN" \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "$NET_JSON" \
    --deployment-configuration "minimumHealthyPercent=0,maximumPercent=100" \
    --enable-ecs-managed-tags \
    --propagate-tags SERVICE \
    --output json \
    --query 'service.{serviceName:serviceName,taskDefinition:taskDefinition,desiredCount:desiredCount}'
else
  echo "==> Mise à jour service ECS $MARKET_WS_SERVICE"
  aws ecs update-service \
    --region "$AWS_REGION" \
    --cluster "$ECS_CLUSTER" \
    --service "$MARKET_WS_SERVICE" \
    --task-definition "$NEW_TASK_ARN" \
    --desired-count 1 \
    --force-new-deployment \
    --output json \
    --query 'service.{serviceName:serviceName,taskDefinition:taskDefinition,desiredCount:desiredCount,runningCount:runningCount}'
fi

if [[ "$WAIT_STABLE" == "1" ]]; then
  echo "==> Attente stabilisation (max 10 min)…"
  aws ecs wait services-stable \
    --region "$AWS_REGION" \
    --cluster "$ECS_CLUSTER" \
    --services "$MARKET_WS_SERVICE"
fi

echo ""
echo "OK — worker $MARKET_WS_SERVICE déployé."
echo "  Logs : $LOG_GROUP (CloudWatch)"
echo "  Vérif : ./scripts/arquantix-verify-market-quotes-prod.sh"
