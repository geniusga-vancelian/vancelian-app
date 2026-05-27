#!/usr/bin/env bash
# Job one-shot ECS Fargate (même secrets / réseau que le service cible).
#
# Usage :
#   ./scripts/arquantix-ecs-run-job.sh vancelian-next vancelian-next 'cd /app && npx tsx scripts/seed-crypto-base-bundles-portfolio-config.ts'
#   ./scripts/arquantix-ecs-run-job.sh arquantix-api arquantix-api 'cd /app && python3 scripts/sync_base_allowed_instruments.py'
#
set -euo pipefail

ECS_SERVICE="${1:-}"
CONTAINER_NAME="${2:-}"
CMD="${3:-}"

if [[ -z "$ECS_SERVICE" || -z "$CONTAINER_NAME" || -z "$CMD" ]]; then
  echo "Usage: $0 <ecs-service> <container-name> '<shell command>'" >&2
  exit 1
fi

AWS_REGION="${AWS_REGION:-us-east-1}"
ECS_CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"

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

OVERRIDES=$(CMD="$CMD" CONTAINER_NAME="$CONTAINER_NAME" python3 - <<'PY'
import json, os
print(json.dumps({
  "containerOverrides": [{
    "name": os.environ["CONTAINER_NAME"],
    "command": ["sh", "-c", os.environ["CMD"]],
  }]
}))
PY
)

echo "==> RunTask $ECS_SERVICE"
echo "  task definition : $TASK_DEF"
echo "  command         : $CMD"

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

if [[ "$EXIT_CODE" != "0" ]]; then
  echo "ERREUR: $ECS_SERVICE exit=$EXIT_CODE ($STOP_REASON)" >&2
  exit 1
fi

echo "OK $ECS_SERVICE (exit 0)"
