#!/usr/bin/env bash
# EventBridge Scheduler — tick defi_observability toutes les 10 minutes (arquantix-api).
#
# Usage :
#   ./scripts/arquantix-defi-observability-eventbridge-setup.sh
#
# Prérequis :
#   Rôle IAM DEFI_ECS_SCHEDULER_ROLE_ARN avec ecs:RunTask + iam:PassRole
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT="${AWS_ACCOUNT:-411714852748}"
ECS_CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
ECS_SERVICE="${ECS_SERVICE:-arquantix-api}"
CONTAINER_NAME="${CONTAINER_NAME:-arquantix-api}"
SCHEDULER_ROLE_ARN="${DEFI_ECS_SCHEDULER_ROLE_ARN:-arn:aws:iam::${AWS_ACCOUNT}:role/arquantix-defi-ecs-scheduler}"
SCHEDULE_NAME="${DEFI_OBSERVABILITY_SCHEDULE_NAME:-arquantix-defi-observability-tick}"
TICK_CMD='cd /app && python3 -m scripts.defi_observability_tick --no-dry-run --max-duration-seconds 480'

TASK_DEF=$(aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE" \
  --region "$AWS_REGION" --query 'services[0].taskDefinition' --output text)
NET=$(aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE" \
  --region "$AWS_REGION" --query 'services[0].networkConfiguration.awsvpcConfiguration' --output json)
SUBNETS=$(echo "$NET" | python3 -c "import json,sys; print(','.join(json.load(sys.stdin)['subnets']))")
SGS=$(echo "$NET" | python3 -c "import json,sys; print(','.join(json.load(sys.stdin)['securityGroups']))")
PUBLIC_IP=$(echo "$NET" | python3 -c "import json,sys; print(json.load(sys.stdin).get('assignPublicIp','ENABLED'))")

EXEC_ROLE=$(aws ecs describe-task-definition --task-definition "$TASK_DEF" --region "$AWS_REGION" \
  --query 'taskDefinition.executionRoleArn' --output text)
TASK_ROLE=$(aws ecs describe-task-definition --task-definition "$TASK_DEF" --region "$AWS_REGION" \
  --query 'taskDefinition.taskRoleArn' --output text)

echo "==> EventBridge Scheduler — defi_observability_tick (rate 10 min)"
echo "  cluster : $ECS_CLUSTER"
echo "  service : $ECS_SERVICE"
echo "  task def: $TASK_DEF"
echo "  scheduler role: $SCHEDULER_ROLE_ARN"

TARGET_JSON=$(TICK_CMD="$TICK_CMD" CONTAINER_NAME="$CONTAINER_NAME" \
  AWS_REGION="$AWS_REGION" AWS_ACCOUNT="$AWS_ACCOUNT" ECS_CLUSTER="$ECS_CLUSTER" \
  TASK_DEF="$TASK_DEF" SCHEDULER_ROLE_ARN="$SCHEDULER_ROLE_ARN" \
  SUBNETS="$SUBNETS" SGS="$SGS" PUBLIC_IP="$PUBLIC_IP" \
  python3 - <<'PY'
import json, os

subnets = os.environ["SUBNETS"].split(",")
sgs = os.environ["SGS"].split(",")
target_input = {
    "containerOverrides": [{
        "name": os.environ["CONTAINER_NAME"],
        "command": ["sh", "-c", os.environ["TICK_CMD"]],
        "environment": [
            {"name": "ONCHAIN_INDEXER_BASE_ENABLED", "value": "true"},
        ],
    }],
}
print(json.dumps({
    "Arn": f"arn:aws:ecs:{os.environ['AWS_REGION']}:{os.environ['AWS_ACCOUNT']}:cluster/{os.environ['ECS_CLUSTER']}",
    "RoleArn": os.environ["SCHEDULER_ROLE_ARN"],
    "EcsParameters": {
        "TaskDefinitionArn": os.environ["TASK_DEF"],
        "LaunchType": "FARGATE",
        "NetworkConfiguration": {
            "awsvpcConfiguration": {
                "Subnets": subnets,
                "SecurityGroups": sgs,
                "AssignPublicIp": os.environ["PUBLIC_IP"],
            }
        },
        "TaskCount": 1,
    },
    "Input": json.dumps(target_input),
}))
PY
)

if aws scheduler get-schedule --name "$SCHEDULE_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
  aws scheduler update-schedule \
    --name "$SCHEDULE_NAME" \
    --schedule-expression "rate(10 minutes)" \
    --schedule-expression-timezone "UTC" \
    --flexible-time-window '{"Mode":"OFF"}' \
    --state ENABLED \
    --target "$TARGET_JSON" \
    --region "$AWS_REGION"
  echo "OK updated $SCHEDULE_NAME"
else
  aws scheduler create-schedule \
    --name "$SCHEDULE_NAME" \
    --schedule-expression "rate(10 minutes)" \
    --schedule-expression-timezone "UTC" \
    --flexible-time-window '{"Mode":"OFF"}' \
    --state ENABLED \
    --target "$TARGET_JSON" \
    --region "$AWS_REGION"
  echo "OK created $SCHEDULE_NAME"
fi

aws scheduler get-schedule --name "$SCHEDULE_NAME" --region "$AWS_REGION" \
  --query '{Name:Name,State:State,Schedule:ScheduleExpression}' --output table

echo ""
echo "Rôle IAM scheduler (à créer une fois si absent) :"
echo "  Trust: scheduler.amazonaws.com + events.amazonaws.com"
echo "  Permissions: ecs:RunTask sur cluster/${ECS_CLUSTER}"
echo "  iam:PassRole sur:"
echo "    ${EXEC_ROLE}"
echo "    ${TASK_ROLE}"
