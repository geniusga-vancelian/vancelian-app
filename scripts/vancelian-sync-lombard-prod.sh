#!/usr/bin/env bash
# Active Lombard V1 (Borrow cbBTC/cbETH → USDC) sur ECS vancelian-next.
#
# Usage :
#   ./scripts/vancelian-sync-lombard-prod.sh
#   LOMBARD_V1_BETA_ALLOWED_WALLETS=0xabc...,0xdef... ./scripts/vancelian-sync-lombard-prod.sh
#   DRY_RUN=1 ./scripts/vancelian-sync-lombard-prod.sh
#
# Prérequis : code Lombard déployé sur main (workflow vancelian-next-deploy).
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
ECS_CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
ECS_SERVICE="${ECS_SERVICE:-vancelian-next}"
ECS_TASKDEF_FAMILY="${ECS_TASKDEF_FAMILY:-vancelian-next}"
DRY_RUN="${DRY_RUN:-0}"

LOMBARD_V1_ENABLED="${LOMBARD_V1_ENABLED:-true}"
LOMBARD_V1_BETA_ENABLED="${LOMBARD_V1_BETA_ENABLED:-true}"
LOMBARD_V1_BETA_LIMITS_ENABLED="${LOMBARD_V1_BETA_LIMITS_ENABLED:-true}"
LOMBARD_V1_BETA_MAX_BORROW_USDC_PER_WALLET="${LOMBARD_V1_BETA_MAX_BORROW_USDC_PER_WALLET:-25000}"
LOMBARD_V1_BETA_MAX_TOTAL_BORROW_USDC_GLOBAL="${LOMBARD_V1_BETA_MAX_TOTAL_BORROW_USDC_GLOBAL:-250000}"
LOMBARD_V1_RECONCILIATION_TOLERANCE_BPS="${LOMBARD_V1_RECONCILIATION_TOLERANCE_BPS:-200}"
LOMBARD_V1_MOCK_ENABLED="${LOMBARD_V1_MOCK_ENABLED:-false}"

if [[ "$LOMBARD_V1_MOCK_ENABLED" == "true" ]]; then
  echo "ERREUR: LOMBARD_V1_MOCK_ENABLED=true interdit en prod." >&2
  exit 1
fi

echo "==> Mise à jour task definition ECS ($ECS_TASKDEF_FAMILY) — Lombard V1"
TD_JSON=$(aws ecs describe-task-definition --task-definition "$ECS_TASKDEF_FAMILY" --region "$AWS_REGION" --query 'taskDefinition' --output json)

NEW_TD_JSON=$(python3 - <<'PY' \
  "$TD_JSON" \
  "$LOMBARD_V1_ENABLED" \
  "$LOMBARD_V1_BETA_ENABLED" \
  "$LOMBARD_V1_BETA_LIMITS_ENABLED" \
  "${LOMBARD_V1_BETA_ALLOWED_WALLETS:-}" \
  "$LOMBARD_V1_BETA_MAX_BORROW_USDC_PER_WALLET" \
  "$LOMBARD_V1_BETA_MAX_TOTAL_BORROW_USDC_GLOBAL" \
  "$LOMBARD_V1_RECONCILIATION_TOLERANCE_BPS" \
  "$LOMBARD_V1_MOCK_ENABLED"
import json
import sys

td = json.loads(sys.argv[1])
lombard_env = {
    "LOMBARD_V1_ENABLED": sys.argv[2],
    "LOMBARD_V1_BETA_ENABLED": sys.argv[3],
    "LOMBARD_V1_BETA_LIMITS_ENABLED": sys.argv[4],
    "LOMBARD_V1_BETA_MAX_BORROW_USDC_PER_WALLET": sys.argv[6],
    "LOMBARD_V1_BETA_MAX_TOTAL_BORROW_USDC_GLOBAL": sys.argv[7],
    "LOMBARD_V1_RECONCILIATION_TOLERANCE_BPS": sys.argv[8],
    "LOMBARD_V1_MOCK_ENABLED": sys.argv[9],
}
allowed = sys.argv[5].strip()
if allowed:
    lombard_env["LOMBARD_V1_BETA_ALLOWED_WALLETS"] = allowed

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
env.update(lombard_env)
container["environment"] = [{"name": k, "value": v} for k, v in sorted(env.items()) if v != ""]

print(json.dumps(td, indent=2))
PY
)

if [[ "$DRY_RUN" == "1" ]]; then
  echo "$NEW_TD_JSON" | python3 -c "import json,sys; td=json.load(sys.stdin); c=td['containerDefinitions'][0]; [print(f\"  {e['name']}={e['value']}\") for e in c.get('environment',[]) if e['name'].startswith('LOMBARD_')]"
  echo "[dry-run] Aucune modification ECS effectuée."
  exit 0
fi

TMP_TD=$(mktemp)
echo "$NEW_TD_JSON" > "$TMP_TD"
NEW_TASK_ARN=$(aws ecs register-task-definition --region "$AWS_REGION" --cli-input-json "file://$TMP_TD" --query 'taskDefinition.taskDefinitionArn' --output text)
rm -f "$TMP_TD"
echo "  registered $NEW_TASK_ARN"

echo "==> Rolling deployment ECS ($ECS_CLUSTER / $ECS_SERVICE)"
aws ecs update-service \
  --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" \
  --task-definition "$NEW_TASK_ARN" \
  --force-new-deployment \
  --region "$AWS_REGION" \
  --query 'service.{serviceName:serviceName,taskDefinition:taskDefinition}' \
  --output json

echo "==> Attente stabilisation (max 15 min)…"
aws ecs wait services-stable --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE" --region "$AWS_REGION"

echo ""
echo "OK Lombard V1 activé sur $ECS_SERVICE"
echo "  LOMBARD_V1_ENABLED=$LOMBARD_V1_ENABLED"
echo "  LOMBARD_V1_BETA_ENABLED=$LOMBARD_V1_BETA_ENABLED"
echo "  caps wallet/global = $LOMBARD_V1_BETA_MAX_BORROW_USDC_PER_WALLET / $LOMBARD_V1_BETA_MAX_TOTAL_BORROW_USDC_GLOBAL USDC"
if [[ -n "${LOMBARD_V1_BETA_ALLOWED_WALLETS:-}" ]]; then
  echo "  allowlist = $LOMBARD_V1_BETA_ALLOWED_WALLETS"
else
  echo "  allowlist = ouverte (tous wallets, caps beta actifs)"
fi
