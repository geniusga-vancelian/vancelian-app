#!/usr/bin/env bash
# Réconciliation prod — settlement PE manquant + clôture RUNNING stale (Kings).
#
# Dry-run par défaut (lecture seule, pas de commit) :
#   ./scripts/arquantix-ecs-bundle-kings-v3-settlement-reconcile.sh
#
# Exécution (GO CTO requis) :
#   BUNDLE_KINGS_SETTLEMENT_RECONCILE_CONFIRM=1 ./scripts/arquantix-ecs-bundle-kings-v3-settlement-reconcile.sh
#
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAYLOAD="${ROOT_DIR}/scripts/arquantix-ecs-bundle-kings-v3-settlement-reconcile.payload.b64"
ECS_SERVICE="arquantix-api"
CONTAINER_NAME="arquantix-api"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECS_CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
S3_BUCKET="${ARQUANTIX_ECS_PAYLOAD_BUCKET:-arquantix-media-prod}"

if [[ ! -f "$PAYLOAD" ]]; then
  "$ROOT_DIR/scripts/build-bundle-kings-v3-settlement-reconcile-payload.sh"
fi

MODE="dry_run"
if [[ "${BUNDLE_KINGS_SETTLEMENT_RECONCILE_CONFIRM:-}" == "1" ]]; then
  MODE="execute"
  echo "==> MODE EXECUTE (BUNDLE_KINGS_SETTLEMENT_RECONCILE_CONFIRM=1)"
else
  echo "==> MODE DRY-RUN (pas de mutation — set BUNDLE_KINGS_SETTLEMENT_RECONCILE_CONFIRM=1 pour exécuter)"
fi

PAYLOAD_SHA=$(shasum -a 256 "$PAYLOAD" | awk '{print $1}')
S3_KEY="ops/ecs-payloads/bundle-kings-v3-settlement-reconcile/${PAYLOAD_SHA}.payload.b64"
aws s3 cp "$PAYLOAD" "s3://${S3_BUCKET}/${S3_KEY}" --region "$AWS_REGION" --only-show-errors
PAYLOAD_URL=$(aws s3 presign "s3://${S3_BUCKET}/${S3_KEY}" --expires-in 3600 --region "$AWS_REGION")

TASK_DEF=$(aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE" \
  --region "$AWS_REGION" --query 'services[0].taskDefinition' --output text)
NET=$(aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE" \
  --region "$AWS_REGION" --query 'services[0].networkConfiguration.awsvpcConfiguration' --output json)
SUBNET=$(echo "$NET" | python3 -c "import json,sys; print(json.load(sys.stdin)['subnets'][0])")
SG=$(echo "$NET" | python3 -c "import json,sys; print(json.load(sys.stdin)['securityGroups'][0])")
PUBLIC_IP=$(echo "$NET" | python3 -c "import json,sys; print(json.load(sys.stdin).get('assignPublicIp','ENABLED'))")

OVERRIDES=$(BUNDLE_KINGS_RECONCILE_PAYLOAD_URL="$PAYLOAD_URL" \
  BUNDLE_KINGS_SETTLEMENT_RECONCILE_CONFIRM="${BUNDLE_KINGS_SETTLEMENT_RECONCILE_CONFIRM:-}" \
  CONTAINER_NAME="$CONTAINER_NAME" \
  python3 - <<'PY'
import json, os
env = [
    {"name": "BUNDLE_KINGS_RECONCILE_PAYLOAD_URL", "value": os.environ["BUNDLE_KINGS_RECONCILE_PAYLOAD_URL"]},
]
if os.environ.get("BUNDLE_KINGS_SETTLEMENT_RECONCILE_CONFIRM"):
    env.append({"name": "BUNDLE_KINGS_SETTLEMENT_RECONCILE_CONFIRM", "value": os.environ["BUNDLE_KINGS_SETTLEMENT_RECONCILE_CONFIRM"]})
bootstrap = (
    "import os,urllib.request,zlib,base64; "
    "u=os.environ['BUNDLE_KINGS_RECONCILE_PAYLOAD_URL']; "
    "b64=urllib.request.urlopen(u, timeout=120).read(); "
    "exec(zlib.decompress(base64.b64decode(b64)))"
)
cmd = "cd /app && python3 -c " + json.dumps(bootstrap)
print(json.dumps({"containerOverrides": [{
    "name": os.environ["CONTAINER_NAME"],
    "command": ["sh", "-c", cmd],
    "environment": env,
}]}))
PY
)

echo "==> Kings V3 settlement reconcile ($MODE)"
echo "  task definition : $TASK_DEF"

TASK_ARN=$(aws ecs run-task --region "$AWS_REGION" --cluster "$ECS_CLUSTER" \
  --task-definition "$TASK_DEF" --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET],securityGroups=[$SG],assignPublicIp=$PUBLIC_IP}" \
  --overrides "$OVERRIDES" --query 'tasks[0].taskArn' --output text)

if [[ -z "$TASK_ARN" || "$TASK_ARN" == "None" ]]; then
  echo "ERREUR: RunTask n'a pas démarré." >&2
  exit 1
fi

TASK_ID="${TASK_ARN##*/}"
echo "  task ARN        : $TASK_ARN"
aws ecs wait tasks-stopped --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --tasks "$TASK_ARN"
EXIT_CODE=$(aws ecs describe-tasks --region "$AWS_REGION" --cluster "$ECS_CLUSTER" \
  --tasks "$TASK_ARN" --query 'tasks[0].containers[0].exitCode' --output text)

LOG_STREAM=$(aws logs describe-log-streams \
  --region "$AWS_REGION" \
  --log-group-name "/ecs/$ECS_SERVICE" \
  --log-stream-name-prefix "api/$CONTAINER_NAME/$TASK_ID" \
  --query 'logStreams[0].logStreamName' \
  --output text 2>/dev/null || true)

if [[ -n "$LOG_STREAM" && "$LOG_STREAM" != "None" ]]; then
  echo "==> CloudWatch output"
  aws logs get-log-events \
    --region "$AWS_REGION" \
    --log-group-name "/ecs/$ECS_SERVICE" \
    --log-stream-name "$LOG_STREAM" \
    --limit 300 \
    --query 'events[*].message' \
    --output text
fi

echo "==> exit code: $EXIT_CODE"
[[ "$EXIT_CODE" == "0" ]] || { echo "ERREUR exit=$EXIT_CODE" >&2; exit 1; }
echo "OK kings settlement reconcile ($MODE)"
