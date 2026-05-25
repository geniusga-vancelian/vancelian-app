#!/usr/bin/env bash
# Importe portal_morpho_vault_configs en prod via ECS RunTask.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SEED_FILE="${SEED_FILE:-$ROOT_DIR/services/arquantix/web/scripts/data/morpho-vault-configs.seed.json}"
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

TMP_OVERRIDES=$(mktemp)
SEED_FILE="$SEED_FILE" CONTAINER_NAME="$CONTAINER_NAME" python3 - <<'PY' > "$TMP_OVERRIDES"
import json
import os

configs = json.load(open(os.environ["SEED_FILE"]))
node_script = r'''
const { PrismaClient } = require("@prisma/client");
const { randomUUID } = require("crypto");
const items = JSON.parse(process.env.MORPHO_CONFIGS_JSON);
const prisma = new PrismaClient();
(async () => {
  let upserted = 0;
  for (const item of items) {
    const vaultAddress = item.vaultAddress.trim().toLowerCase();
    await prisma.portalMorphoVaultConfig.upsert({
      where: { vaultAddress },
      create: {
        id: randomUUID(),
        vaultAddress,
        chainId: item.chainId ?? 8453,
        integrationMode: item.integrationMode,
        privyVaultId: item.privyVaultId ?? null,
        label: item.label ?? null,
        description: item.description ?? null,
        curator: item.curator ?? null,
        sortOrder: item.sortOrder ?? 999,
        isPublished: item.isPublished ?? false,
      },
      update: {
        chainId: item.chainId ?? 8453,
        integrationMode: item.integrationMode,
        privyVaultId: item.privyVaultId ?? null,
        label: item.label ?? null,
        description: item.description ?? null,
        curator: item.curator ?? null,
        sortOrder: item.sortOrder ?? 999,
        isPublished: item.isPublished ?? false,
      },
    });
    upserted += 1;
  }
  const rows = await prisma.portalMorphoVaultConfig.findMany({ orderBy: { sortOrder: "asc" } });
  console.log(JSON.stringify({
    upserted,
    count: rows.length,
    vaults: rows.map((r) => ({ label: r.label, mode: r.integrationMode, published: r.isPublished })),
  }));
  await prisma.$disconnect();
})().catch(async (error) => {
  console.error(error);
  process.exit(1);
});
'''
print(json.dumps({
  "containerOverrides": [{
    "name": os.environ["CONTAINER_NAME"],
    "command": ["node", "-e", node_script],
    "environment": [{"name": "MORPHO_CONFIGS_JSON", "value": json.dumps(configs)}],
  }]
}))
PY

echo "==> Import Morpho vault configs (prod ECS)"
echo "  seed : $SEED_FILE"
echo "  task : $TASK_DEF"

TASK_ARN=$(aws ecs run-task \
  --region "$AWS_REGION" \
  --cluster "$ECS_CLUSTER" \
  --task-definition "$TASK_DEF" \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET],securityGroups=[$SG],assignPublicIp=$PUBLIC_IP}" \
  --overrides "file://$TMP_OVERRIDES" \
  --query 'tasks[0].taskArn' \
  --output text)
rm -f "$TMP_OVERRIDES"

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
  --filter-pattern 'upserted' \
  --limit 5 \
  --query 'events[-1].message' \
  --output text 2>/dev/null || true)
echo "  result: $MSG"

echo ""
echo "==> sync-registry"
"$ROOT_DIR/scripts/vancelian-morpho-ecs-run-job.sh" sync-registry

echo "Terminé."
