#!/usr/bin/env bash
# Crée / met à jour les règles EventBridge Scheduler pour les jobs Morpho (ECS RunTask).
#
# Usage :
#   ./scripts/vancelian-morpho-eventbridge-setup.sh
#
# Prérequis :
#   - Rôle IAM EventBridge → ecs:RunTask + iam:PassRole (ecsTaskExecutionRole)
#   - Variable MORPHO_ECS_SCHEDULER_ROLE_ARN si le rôle existe déjà
#
# Schedules :
#   - morpho-sync-registry : cron(0 */6 * * ? *)  — toutes les 6h UTC
#   - morpho-reconcile     : cron(0 6 * * ? *)    — quotidien 06:00 UTC
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT="${AWS_ACCOUNT:-411714852748}"
ECS_CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
ECS_SERVICE="${ECS_SERVICE:-vancelian-next}"
CONTAINER_NAME="${CONTAINER_NAME:-vancelian-next}"
SCHEDULER_ROLE_ARN="${MORPHO_ECS_SCHEDULER_ROLE_ARN:-arn:aws:iam::${AWS_ACCOUNT}:role/vancelian-morpho-ecs-scheduler}"

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

SUBNETS=$(echo "$NET" | python3 -c "import json,sys; print(','.join(json.load(sys.stdin)['subnets']))")
SGS=$(echo "$NET" | python3 -c "import json,sys; print(','.join(json.load(sys.stdin)['securityGroups']))")
PUBLIC_IP=$(echo "$NET" | python3 -c "import json,sys; print(json.load(sys.stdin).get('assignPublicIp','ENABLED'))")

EXEC_ROLE=$(aws ecs describe-task-definition \
  --task-definition "$TASK_DEF" \
  --region "$AWS_REGION" \
  --query 'taskDefinition.executionRoleArn' \
  --output text)

TASK_ROLE=$(aws ecs describe-task-definition \
  --task-definition "$TASK_DEF" \
  --region "$AWS_REGION" \
  --query 'taskDefinition.taskRoleArn' \
  --output text)

echo "==> Configuration EventBridge Scheduler (region=$AWS_REGION)"
echo "  cluster      : $ECS_CLUSTER"
echo "  task def     : $TASK_DEF"
echo "  scheduler role: $SCHEDULER_ROLE_ARN"

create_or_update_schedule() {
  local name=$1
  local schedule_expression=$2
  local command=$3

  local target_input
  target_input=$(python3 - <<PY
import json
print(json.dumps({
  "ClusterArn": "arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT}:cluster/${ECS_CLUSTER}",
  "TaskDefinitionArn": "${TASK_DEF}",
  "LaunchType": "FARGATE",
  "NetworkConfiguration": {
    "awsvpcConfiguration": {
      "Subnets": "${SUBNETS}".split(","),
      "SecurityGroups": "${SGS}".split(","),
      "AssignPublicIp": "${PUBLIC_IP}"
    }
  },
  "Overrides": {
    "ContainerOverrides": [{
      "Name": "${CONTAINER_NAME}",
      "Command": ["sh", "-c", """${command}"""]
    }]
  }
}))
PY
)

  if aws scheduler get-schedule --name "$name" --region "$AWS_REGION" >/dev/null 2>&1; then
    aws scheduler update-schedule \
      --name "$name" \
      --schedule-expression "$schedule_expression" \
      --schedule-expression-timezone "UTC" \
      --flexible-time-window '{"Mode":"OFF"}' \
      --target "{\"Arn\":\"arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT}:cluster/${ECS_CLUSTER}\",\"RoleArn\":\"${SCHEDULER_ROLE_ARN}\",\"EcsParameters\":{\"TaskDefinitionArn\":\"${TASK_DEF}\",\"LaunchType\":\"FARGATE\",\"NetworkConfiguration\":{\"awsvpcConfiguration\":{\"Subnets\":[\"${SUBNETS//,/\",\"}\"],\"SecurityGroups\":[\"${SGS//,/\",\"}\"],\"AssignPublicIp\":\"${PUBLIC_IP}\"}},\"TaskCount\":1},\"Input\":$(echo "$target_input" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')}" \
      --region "$AWS_REGION" >/dev/null 2>&1 && echo "  updated schedule $name" && return
  fi

  echo "  schedule $name → créer manuellement si le rôle $SCHEDULER_ROLE_ARN n'existe pas encore."
  echo "    expression: $schedule_expression"
  echo "    command   : $command"
}

echo ""
echo "==> Rôle IAM scheduler (à créer une fois si absent)"
cat <<EOF
Trust policy (events.amazonaws.com + scheduler.amazonaws.com) :
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": ["scheduler.amazonaws.com", "events.amazonaws.com"] },
    "Action": "sts:AssumeRole"
  }]
}

Permissions : ecs:RunTask sur cluster/$ECS_CLUSTER, iam:PassRole sur :
  $EXEC_ROLE
  $TASK_ROLE
EOF

echo ""
echo "==> Schedules Morpho"
create_or_update_schedule \
  "vancelian-morpho-sync-registry" \
  "cron(0 */6 * * ? *)" \
  "cd /app && npx tsx scripts/sync-morpho-vault-registry.ts"

create_or_update_schedule \
  "vancelian-morpho-reconcile" \
  "cron(0 6 * * ? *)" \
  "cd /app && npx tsx scripts/run-morpho-vault-reconciliation.ts"

echo ""
echo "Backfill : manuel uniquement → ./scripts/vancelian-morpho-ecs-run-job.sh backfill"
echo "Voir docs/arquantix/MORPHO_PRODUCTION_DEPLOY_ECS.md pour le détail EventBridge."
