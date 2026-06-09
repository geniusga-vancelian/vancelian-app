#!/usr/bin/env bash
# Clôture contrôlée legacy batch 295804e8 (Two Crypto Kings).
#
# Dry-run par défaut :
#   ./scripts/arquantix-ecs-bundle-legacy-batch-295804e8-close-controlled.sh
#
# Exécution (GO CTO requis) :
#   BUNDLE_LEGACY_BATCH_CLOSE_CONFIRM=1 ./scripts/arquantix-ecs-bundle-legacy-batch-295804e8-close-controlled.sh
#
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAYLOAD="${ROOT_DIR}/scripts/arquantix-ecs-bundle-legacy-batch-295804e8-close-controlled.payload.b64"
ECS_SERVICE="arquantix-api"
CONTAINER_NAME="arquantix-api"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECS_CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
S3_BUCKET="${ARQUANTIX_ECS_PAYLOAD_BUCKET:-arquantix-media-prod}"
BATCH_PREFIX="${BUNDLE_LEGACY_CLOSE_BATCH_PREFIX:-295804e8}"

if [[ ! -f "$PAYLOAD" ]]; then
  "$ROOT_DIR/scripts/build-bundle-legacy-batch-295804e8-close-controlled-payload.sh"
fi

MODE="dry_run"
if [[ "${BUNDLE_LEGACY_BATCH_CLOSE_CONFIRM:-}" == "1" ]]; then
  MODE="execute"
  echo "==> MODE EXECUTE (BUNDLE_LEGACY_BATCH_CLOSE_CONFIRM=1)"
else
  echo "==> MODE DRY-RUN (pas de mutation)"
fi

PAYLOAD_SHA=$(shasum -a 256 "$PAYLOAD" | awk '{print $1}')
S3_KEY="ops/ecs-payloads/bundle-legacy-batch-close/${PAYLOAD_SHA}.payload.b64"
aws s3 cp "$PAYLOAD" "s3://${S3_BUCKET}/${S3_KEY}" --region "$AWS_REGION" --only-show-errors
PAYLOAD_URL=$(aws s3 presign "s3://${S3_BUCKET}/${S3_KEY}" --expires-in 3600 --region "$AWS_REGION")

TASK_DEF=$(aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE" \
  --region "$AWS_REGION" --query 'services[0].taskDefinition' --output text)
NET=$(aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE" \
  --region "$AWS_REGION" --query 'services[0].networkConfiguration.awsvpcConfiguration' --output json)
SUBNET=$(echo "$NET" | python3 -c "import json,sys; print(json.load(sys.stdin)['subnets'][0])")
SG=$(echo "$NET" | python3 -c "import json,sys; print(json.load(sys.stdin)['securityGroups'][0])")
PUBLIC_IP=$(echo "$NET" | python3 -c "import json,sys; print(json.load(sys.stdin).get('assignPublicIp','ENABLED'))")

OVERRIDES=$(BUNDLE_LEGACY_CLOSE_PAYLOAD_URL="$PAYLOAD_URL" \
  BUNDLE_LEGACY_CLOSE_BATCH_PREFIX="$BATCH_PREFIX" \
  BUNDLE_LEGACY_BATCH_CLOSE_CONFIRM="${BUNDLE_LEGACY_BATCH_CLOSE_CONFIRM:-}" \
  CONTAINER_NAME="$CONTAINER_NAME" \
  python3 - <<'PY'
import json, os
env = [
    {"name": "BUNDLE_LEGACY_CLOSE_PAYLOAD_URL", "value": os.environ["BUNDLE_LEGACY_CLOSE_PAYLOAD_URL"]},
    {"name": "BUNDLE_LEGACY_CLOSE_BATCH_PREFIX", "value": os.environ.get("BUNDLE_LEGACY_CLOSE_BATCH_PREFIX", "295804e8")},
]
if os.environ.get("BUNDLE_LEGACY_BATCH_CLOSE_CONFIRM"):
    env.append({"name": "BUNDLE_LEGACY_BATCH_CLOSE_CONFIRM", "value": os.environ["BUNDLE_LEGACY_BATCH_CLOSE_CONFIRM"]})
bootstrap = (
    "import os,urllib.request,zlib,base64; "
    "u=os.environ['BUNDLE_LEGACY_CLOSE_PAYLOAD_URL']; "
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

TASK_ARN=$(aws ecs run-task --region "$AWS_REGION" --cluster "$ECS_CLUSTER" \
  --task-definition "$TASK_DEF" --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET],securityGroups=[$SG],assignPublicIp=$PUBLIC_IP}" \
  --overrides "$OVERRIDES" --query 'tasks[0].taskArn' --output text)
TASK_ID="${TASK_ARN##*/}"
aws ecs wait tasks-stopped --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --tasks "$TASK_ARN"
EXIT_CODE=$(aws ecs describe-tasks --region "$AWS_REGION" --cluster "$ECS_CLUSTER" \
  --tasks "$TASK_ARN" --query 'tasks[0].containers[0].exitCode' --output text)

aws logs get-log-events --log-group-name "/ecs/${ECS_SERVICE}" \
  --log-stream-name "api/${ECS_SERVICE}/${TASK_ID}" --region "$AWS_REGION" \
  --query 'events[*].message' --output text 2>/dev/null \
  | python3 -c "import sys,re,json; t=sys.stdin.read(); m=re.search(r'\{.*\"phase\"\s*:\s*\"bundle_legacy_batch_close_controlled\".*\}', t, re.S); print(json.dumps(json.loads(m.group()), indent=2) if m else 'JSON_NOT_FOUND\n'+t[-4000:])" \
  || true

[[ "$EXIT_CODE" == "0" ]] || { echo "ERREUR exit=$EXIT_CODE" >&2; exit 1; }
echo "OK legacy batch close ($MODE)"
