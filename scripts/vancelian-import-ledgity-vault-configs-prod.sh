#!/usr/bin/env bash
# Importe portal_morpho_vault_configs Ledgity (lyUSDC, lyEURC) + defi_vault_registry en prod via ECS RunTask.
# Utilise le client Prisma natif (integration_mode ledgity_vault) — migrations requises avant import.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SEED_FILE="${SEED_FILE:-$ROOT_DIR/services/arquantix/web/scripts/data/ledgity-vault-configs.seed.json}"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECS_CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
ECS_SERVICE="${ECS_SERVICE:-vancelian-next}"
CONTAINER_NAME="${CONTAINER_NAME:-vancelian-next}"

if [[ ! -f "$SEED_FILE" ]]; then
  echo "ERREUR: seed introuvable: $SEED_FILE" >&2
  exit 1
fi

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
    "command": ["sh", "-c", "cd /app && npx tsx scripts/seed-ledgity-vaults.ts"],
  }]
}))
PY
)

echo "==> Import Ledgity vault configs + registry (prod ECS, Prisma natif)"
echo "  seed : $SEED_FILE (bundled in image at /app/scripts/data/)"
echo "  task : $TASK_DEF"

TASK_ARN=$(aws ecs run-task \
  --region "$AWS_REGION" \
  --cluster "$ECS_CLUSTER" \
  --task-definition "$TASK_DEF" \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET],securityGroups=[$SG],assignPublicIp=$PUBLIC_IP}" \
  --overrides "$OVERRIDES" \
  --query 'tasks[0].taskArn' \
  --output text)

echo "  run  : $TASK_ARN"
for _ in $(seq 1 60); do
  STATUS=$(aws ecs describe-tasks --cluster "$ECS_CLUSTER" --tasks "$TASK_ARN" --region "$AWS_REGION" --query 'tasks[0].lastStatus' --output text)
  if [[ "$STATUS" == "STOPPED" ]]; then
    EXIT=$(aws ecs describe-tasks --cluster "$ECS_CLUSTER" --tasks "$TASK_ARN" --region "$AWS_REGION" --query 'tasks[0].containers[0].exitCode' --output text)
    echo "  exit : $EXIT"
    [[ "$EXIT" == "0" ]] || exit 1
    break
  fi
  sleep 5
done

MSG=$(aws logs filter-log-events \
  --log-group-name /ecs/vancelian-next \
  --region "$AWS_REGION" \
  --start-time $(($(date +%s) * 1000 - 300000)) \
  --filter-pattern 'ledgity:seed-vaults' \
  --limit 5 \
  --query 'events[-1].message' \
  --output text 2>/dev/null || true)
echo "  result: $MSG"

echo ""
echo "Terminé — lyUSDC + lyEURC synchronisés en prod (portal_morpho_vault_configs + defi_vault_registry)."
