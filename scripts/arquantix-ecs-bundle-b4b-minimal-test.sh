#!/usr/bin/env bash
# Test contrôlé prod B4b — parent FROZEN → bridge → fresh swap → settle → LEDGER_SETTLED.
#
# Usage :
#   ./scripts/arquantix-ecs-bundle-b4b-minimal-test.sh baseline
#   BUNDLE_B4B_TEST_CONFIRM=1 PORTFOLIO_ID=<uuid> AMOUNT_USDC=1 \
#     ./scripts/arquantix-ecs-bundle-b4b-minimal-test.sh create_frozen_parent
#   BUNDLE_B4B_TEST_CONFIRM=1 PARENT_INTENT_ID=<uuid> \
#     ./scripts/arquantix-ecs-bundle-b4b-minimal-test.sh run_b4b_bridge
#   BUNDLE_B4B_TEST_CONFIRM=1 PARENT_INTENT_ID=<uuid> \
#     ./scripts/arquantix-ecs-bundle-b4b-minimal-test.sh execute_fresh_swap
#   PARENT_INTENT_ID=<uuid> \
#     ./scripts/arquantix-ecs-bundle-b4b-minimal-test.sh audit
#   BUNDLE_B4B_TEST_CONFIRM=1 PARENT_INTENT_ID=<uuid> \
#     ./scripts/arquantix-ecs-bundle-b4b-minimal-test.sh rollback_or_cleanup
#
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAYLOAD="${ROOT_DIR}/scripts/arquantix-ecs-bundle-b4b-minimal-test.payload.b64"
MODE="${1:-}"
ECS_SERVICE="arquantix-api"
CONTAINER_NAME="arquantix-api"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECS_CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
S3_BUCKET="${ARQUANTIX_ECS_PAYLOAD_BUCKET:-arquantix-media-prod}"

if [[ -z "$MODE" ]]; then
  echo "Usage: $0 <baseline|create_frozen_parent|run_b4b_bridge|execute_fresh_swap|audit|rollback_or_cleanup>" >&2
  exit 1
fi
shift || true

[[ -f "$PAYLOAD" ]] || { echo "Payload manquant: $PAYLOAD" >&2; exit 1; }

PAYLOAD_SHA=$(shasum -a 256 "$PAYLOAD" | awk '{print $1}')
S3_KEY="ops/ecs-payloads/bundle-b4b-minimal-test/${PAYLOAD_SHA}.payload.b64"

echo "==> Upload payload S3 s3://${S3_BUCKET}/${S3_KEY}"
aws s3 cp "$PAYLOAD" "s3://${S3_BUCKET}/${S3_KEY}" --region "$AWS_REGION" --only-show-errors
PAYLOAD_URL=$(aws s3 presign "s3://${S3_BUCKET}/${S3_KEY}" --expires-in 3600 --region "$AWS_REGION")

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

EXECUTE_MOCK="${BUNDLE_B4B_EXECUTE_MOCK:-}"
if [[ "$MODE" == "execute_fresh_swap" ]]; then
  EXECUTE_MOCK="${EXECUTE_MOCK:-1}"
fi

OVERRIDES=$(BUNDLE_B4B_TEST_MODE="$MODE" \
  BUNDLE_B4B_TEST_CONFIRM="${BUNDLE_B4B_TEST_CONFIRM:-}" \
  BUNDLE_B4B_EXECUTE_MOCK="$EXECUTE_MOCK" \
  TEST_RUN_ID="${TEST_RUN_ID:-}" \
  PORTFOLIO_ID="${PORTFOLIO_ID:-}" \
  AMOUNT_USDC="${AMOUNT_USDC:-}" \
  PARENT_INTENT_ID="${PARENT_INTENT_ID:-}" \
  BUNDLE_B4B_PAYLOAD_URL="$PAYLOAD_URL" \
  CONTAINER_NAME="$CONTAINER_NAME" \
  python3 - <<'PY'
import json, os

env = [{"name": "BUNDLE_B4B_PAYLOAD_URL", "value": os.environ["BUNDLE_B4B_PAYLOAD_URL"]}]
for key in (
    "BUNDLE_B4B_TEST_MODE",
    "BUNDLE_B4B_TEST_CONFIRM",
    "LIFI_SWAPS_MOCK",
    "TEST_RUN_ID",
    "PORTFOLIO_ID",
    "AMOUNT_USDC",
    "PARENT_INTENT_ID",
):
    val = os.environ.get(key, "")
    if val:
        env.append({"name": key, "value": val})

if os.environ.get("BUNDLE_B4B_EXECUTE_MOCK", "").strip() in {"1", "true", "yes", "on"}:
    env.append({"name": "LIFI_SWAPS_MOCK", "value": "1"})

bootstrap = (
    "import os,urllib.request,zlib,base64; "
    "u=os.environ['BUNDLE_B4B_PAYLOAD_URL']; "
    "b64=urllib.request.urlopen(u, timeout=60).read(); "
    "exec(zlib.decompress(base64.b64decode(b64)))"
)
cmd = "cd /app && python3 -c " + json.dumps(bootstrap)
print(json.dumps({
    "containerOverrides": [{
        "name": os.environ["CONTAINER_NAME"],
        "command": ["sh", "-c", cmd],
        "environment": env,
    }]
}))
PY
)

echo "==> B4b minimal controlled test mode=$MODE"
echo "  task definition : $TASK_DEF"
echo "  payload s3      : s3://${S3_BUCKET}/${S3_KEY}"

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

TASK_ID="${TASK_ARN##*/}"
echo "  task ARN        : $TASK_ARN"
echo "  logs            : /ecs/$ECS_SERVICE (stream api/$ECS_SERVICE/$TASK_ID)"

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

echo "==> Fetch CloudWatch JSON"
aws logs get-log-events \
  --log-group-name "/ecs/${ECS_SERVICE}" \
  --log-stream-name "api/${ECS_SERVICE}/${TASK_ID}" \
  --region "$AWS_REGION" \
  --query 'events[*].message' \
  --output text 2>/dev/null \
  | python3 -c "import sys,re,json; t=sys.stdin.read(); m=re.search(r'\{.*\"phase\"\s*:\s*\"bundle_b4b_minimal_controlled_test\".*\}', t, re.S); print(json.dumps(json.loads(m.group()), indent=2) if m else 'JSON_NOT_FOUND\n'+t[-2000:])" \
  || true

if [[ "$EXIT_CODE" != "0" ]]; then
  echo "ERREUR: $ECS_SERVICE exit=$EXIT_CODE ($STOP_REASON)" >&2
  exit 1
fi

echo "OK $ECS_SERVICE (exit 0)"
