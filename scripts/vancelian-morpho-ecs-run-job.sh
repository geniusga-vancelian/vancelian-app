#!/usr/bin/env bash
# Exécute un job Morpho one-shot via ECS RunTask (même image / secrets que vancelian-next).
#
# Usage :
#   ./scripts/vancelian-morpho-ecs-run-job.sh sync-registry
#   ./scripts/vancelian-morpho-ecs-run-job.sh reconcile
#   ./scripts/vancelian-morpho-ecs-run-job.sh backfill
#   ./scripts/vancelian-morpho-ecs-run-job.sh migrate
#
# Le conteneur utilise la task definition courante du service vancelian-next.
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
ECS_CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
ECS_SERVICE="${ECS_SERVICE:-vancelian-next}"
CONTAINER_NAME="${CONTAINER_NAME:-vancelian-next}"

JOB="${1:-}"
if [[ -z "$JOB" ]]; then
  echo "Usage: $0 {sync-registry|reconcile|backfill|migrate|import-configs}" >&2
  exit 1
fi

case "$JOB" in
  sync-registry)
    CMD='cd /app && npx tsx scripts/sync-morpho-vault-registry.ts'
    ;;
  reconcile)
    CMD='cd /app && npx tsx scripts/run-morpho-vault-reconciliation.ts'
    ;;
  backfill)
    CMD='cd /app && npx tsx scripts/backfill-morpho-vault-positions.ts'
    ;;
  migrate)
    CMD='cd /app && npx prisma migrate deploy'
    ;;
  import-configs)
    CMD='cd /app && npx tsx scripts/sync-morpho-vault-configs.ts import scripts/data/morpho-vault-configs.seed.json'
    ;;
  *)
    echo "Job inconnu: $JOB" >&2
    exit 1
    ;;
esac

echo "==> Résolution task definition ($ECS_SERVICE)"
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

OVERRIDES=$(python3 - <<PY
import json
print(json.dumps({
  "containerOverrides": [{
    "name": "$CONTAINER_NAME",
    "command": ["sh", "-c", """$CMD"""],
  }]
}))
PY
)

echo "==> RunTask morpho:$JOB"
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
  echo "ERREUR: job morpho:$JOB exit=$EXIT_CODE ($STOP_REASON)" >&2
  exit 1
fi

echo "OK morpho:$JOB (exit 0)"
