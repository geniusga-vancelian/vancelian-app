#!/usr/bin/env bash
# Sync homepage EN PUBLISHED + médias vancelian-home : local → prod (RDS + S3/R2).
#
# Usage :
#   bash scripts/arquantix-sync-homepage-en-to-prod.sh
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_ROOT="$REPO_ROOT/services/arquantix/web"
# shellcheck source=arquantix_compose_lib.sh
source "$REPO_ROOT/scripts/arquantix_compose_lib.sh"
arquantix_lib_set_root "$REPO_ROOT"

AWS_REGION="${AWS_REGION:-us-east-1}"
S3_BUCKET="${ARQUANTIX_DB_SYNC_BUCKET:-arquantix-media-prod}"
S3_PREFIX="${ARQUANTIX_DB_SYNC_PREFIX:-ops/cms-sync}"
ECS_CLUSTER="${ARQUANTIX_ECS_CLUSTER:-arquantix-cluster}"
TASK_DEF="${ARQUANTIX_API_TASK_DEF:-arquantix-api:20}"
CONTAINER_NAME="${ARQUANTIX_API_CONTAINER:-arquantix-api}"
ECS_SUBNET="${ARQUANTIX_ECS_SUBNET:-subnet-03581e86634f354dd}"
ECS_SG="${ARQUANTIX_ECS_SG:-sg-064dc832914f8e05f}"
MEDIA_DIR="$WEB_ROOT/public/cms/vancelian-home"

ENV_FILE="$REPO_ROOT/.env.arquantix"
DB_PORT="$( (grep -E '^[[:space:]]*DB_PORT=' "$ENV_FILE" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
DB_USER="$( (grep -E '^[[:space:]]*DB_USER=' "$ENV_FILE" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
DB_PASSWORD="$( (grep -E '^[[:space:]]*DB_PASSWORD=' "$ENV_FILE" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
DB_NAME="$( (grep -E '^[[:space:]]*DB_NAME=' "$ENV_FILE" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
[[ -z "$DB_PORT" ]] && DB_PORT="5443"
[[ -z "$DB_USER" ]] && DB_USER="arquantix"
[[ -z "$DB_PASSWORD" ]] && DB_PASSWORD="arquantix"
[[ -z "$DB_NAME" ]] && DB_NAME="arquantix_fresh"

TS="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="${HOME}/backups/homepage_en_sync_${TS}"
S3_JSON_KEY="${S3_PREFIX}/homepage_en_sync_${TS}.json"

echo "━━ 1/4 Export local (homepage EN PUBLISHED) ━━"
mkdir -p "$OUT_DIR"
(
  cd "$WEB_ROOT"
  DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@127.0.0.1:${DB_PORT}/${DB_NAME}" \
  HOMEPAGE_SYNC_OUT_DIR="$OUT_DIR" \
  npx tsx scripts/export-homepage-en-for-prod.ts
)

echo "━━ 2/4 Upload médias vancelian-home → S3 ━━"
if [[ ! -d "$MEDIA_DIR" ]]; then
  echo "❌ Répertoire médias absent : $MEDIA_DIR" >&2
  exit 1
fi
for f in "$MEDIA_DIR"/*; do
  [[ -f "$f" ]] || continue
  base="$(basename "$f")"
  aws s3 cp "$f" "s3://${S3_BUCKET}/cms/vancelian-home/${base}" --region "$AWS_REGION"
  echo "   ↑ cms/vancelian-home/${base}"
done

echo "━━ 3/4 Upload payload JSON ━━"
aws s3 cp "$OUT_DIR/homepage-en-sync.json" "s3://${S3_BUCKET}/${S3_JSON_KEY}" --region "$AWS_REGION"
PRESIGNED_JSON="$(aws s3 presign "s3://${S3_BUCKET}/${S3_JSON_KEY}" --expires-in 7200 --region "$AWS_REGION")"

echo "━━ 4/4 Apply sur RDS prod (ECS) ━━"
APPLY_B64="$(python3 -c "import base64; print(base64.b64encode(open('$REPO_ROOT/scripts/apply-homepage-en-sync.py','rb').read()).decode())")"
export CONTAINER_NAME PRESIGNED_JSON APPLY_B64
OVERRIDES="$(python3 - <<'PY'
import json, os
print(json.dumps({
  "containerOverrides": [{
    "name": os.environ["CONTAINER_NAME"],
    "command": ["sh", "-c", "echo \"$APPLY_B64\" | base64 -d > /tmp/apply.py && python3 /tmp/apply.py"],
    "environment": [
      {"name": "SYNC_JSON_URL", "value": os.environ["PRESIGNED_JSON"]},
      {"name": "APPLY_B64", "value": os.environ["APPLY_B64"]},
    ],
  }]
}))
PY
)"

TASK_ARN="$(aws ecs run-task \
  --region "$AWS_REGION" \
  --cluster "$ECS_CLUSTER" \
  --task-definition "$TASK_DEF" \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$ECS_SUBNET],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" \
  --overrides "$OVERRIDES" \
  --query 'tasks[0].taskArn' \
  --output text)"

echo "   Tâche : $TASK_ARN"
aws ecs wait tasks-stopped --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --tasks "$TASK_ARN"
EXIT_CODE="$(aws ecs describe-tasks --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --tasks "$TASK_ARN" \
  --query 'tasks[0].containers[0].exitCode' --output text)"
if [[ "$EXIT_CODE" != "0" ]]; then
  echo "❌ Sync homepage a échoué (exit=$EXIT_CODE)" >&2
  exit 1
fi

echo "✓ Homepage EN publiée en prod."
echo "  JSON : s3://${S3_BUCKET}/${S3_JSON_KEY}"
