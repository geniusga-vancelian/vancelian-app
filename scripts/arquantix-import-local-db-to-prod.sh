#!/usr/bin/env bash
# Importe la base PostgreSQL locale (Compose) vers RDS prod via S3 + tâche ECS one-shot.
# Prérequis : AWS CLI, Docker Compose local up, droits RDS/ECS/S3.
#
# Usage :
#   bash scripts/arquantix-import-local-db-to-prod.sh
#   bash scripts/arquantix-import-local-db-to-prod.sh --skip-dump   # réutilise le dernier dump local
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=arquantix_compose_lib.sh
source "$REPO_ROOT/scripts/arquantix_compose_lib.sh"
arquantix_lib_set_root "$REPO_ROOT"

SKIP_DUMP=0
if [[ "${1:-}" == "--skip-dump" ]]; then
  SKIP_DUMP=1
fi

AWS_REGION="${AWS_REGION:-us-east-1}"
S3_BUCKET="${ARQUANTIX_DB_SYNC_BUCKET:-arquantix-media-prod}"
S3_PREFIX="${ARQUANTIX_DB_SYNC_PREFIX:-ops/db-sync}"
ECS_CLUSTER="${ARQUANTIX_ECS_CLUSTER:-arquantix-cluster}"
TASK_DEF="${ARQUANTIX_API_TASK_DEF:-arquantix-api:17}"
CONTAINER_NAME="${ARQUANTIX_API_CONTAINER:-arquantix-api}"
ECS_SUBNET="${ARQUANTIX_ECS_SUBNET:-subnet-03581e86634f354dd}"
ECS_SG="${ARQUANTIX_ECS_SG:-sg-064dc832914f8e05f}"
RDS_ID="${ARQUANTIX_RDS_ID:-arquantix-db}"

TS="$(date +%Y%m%d-%H%M%S)"
DUMP_LOCAL="${HOME}/backups/arquantix_local_to_prod_${TS}.dump"
S3_KEY="${S3_PREFIX}/local_to_prod_${TS}.dump"
SNAPSHOT_ID="${RDS_ID}-pre-local-import-${TS}"

echo "━━ 1/6 Snapshot RDS prod (rollback AWS) ━━"
aws rds create-db-snapshot \
  --region "$AWS_REGION" \
  --db-instance-identifier "$RDS_ID" \
  --db-snapshot-identifier "$SNAPSHOT_ID" \
  --output text >/dev/null
echo "   Snapshot lancé : $SNAPSHOT_ID (restauration possible via RDS si besoin)"

echo "━━ 2/6 Dump base locale (pg_dump 15 → compatible RDS PG 15) ━━"
if [[ "$SKIP_DUMP" -eq 0 ]]; then
  ENV_FILE="$REPO_ROOT/.env.arquantix"
  DB_NAME="$( (grep -E '^[[:space:]]*DB_NAME=' "$ENV_FILE" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  DB_USER="$( (grep -E '^[[:space:]]*DB_USER=' "$ENV_FILE" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  DB_PASSWORD="$( (grep -E '^[[:space:]]*DB_PASSWORD=' "$ENV_FILE" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  DB_PORT="$( (grep -E '^[[:space:]]*DB_PORT=' "$ENV_FILE" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  [[ -z "$DB_NAME" ]] && DB_NAME="arquantix_fresh"
  [[ -z "$DB_USER" ]] && DB_USER="arquantix"
  [[ -z "$DB_PASSWORD" ]] && DB_PASSWORD="arquantix"
  [[ -z "$DB_PORT" ]] && DB_PORT="5443"
  PGPASSWORD="$DB_PASSWORD" docker run --rm \
    -e PGPASSWORD \
    --add-host=host.docker.internal:host-gateway \
    postgres:15-alpine \
    pg_dump -h host.docker.internal -p "$DB_PORT" -U "$DB_USER" -Fc --no-owner --no-acl -d "$DB_NAME" \
    >"$DUMP_LOCAL"
  echo "   Dump local (PG15 client) : $DUMP_LOCAL"
else
  LATEST="$(ls -t "${HOME}/backups"/arquantix_*.dump | head -1)"
  cp "$LATEST" "$DUMP_LOCAL"
  echo "   Dump réutilisé : $DUMP_LOCAL"
fi

echo "━━ 3/6 Upload S3 ━━"
aws s3 cp "$DUMP_LOCAL" "s3://${S3_BUCKET}/${S3_KEY}" --region "$AWS_REGION"
PRESIGNED_URL="$(aws s3 presign "s3://${S3_BUCKET}/${S3_KEY}" --expires-in 7200 --region "$AWS_REGION")"
echo "   s3://${S3_BUCKET}/${S3_KEY}"

echo "━━ 4/6 Réduction trafic prod (scale 0 API + Next) ━━"
aws ecs update-service --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --service arquantix-api --desired-count 0 >/dev/null
aws ecs update-service --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --service vancelian-next --desired-count 0 >/dev/null
echo "   Attente arrêt des tâches…"
aws ecs wait services-stable --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --services arquantix-api vancelian-next || true
sleep 15

echo "━━ 5/6 Restauration RDS via tâche ECS ━━"
PYTHON_SCRIPT='import os, subprocess, sys, urllib.request

url = os.environ["DUMP_PRESIGNED_URL"]
db = os.environ["DATABASE_URL"]
path = "/tmp/import.dump"
print("Downloading dump…", flush=True)
urllib.request.urlretrieve(url, path)
print("Terminating active sessions…", flush=True)
subprocess.check_call([
    "psql", db, "-v", "ON_ERROR_STOP=1", "-c",
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
    "WHERE datname = current_database() AND pid <> pg_backend_pid();",
])
print("pg_restore…", flush=True)
result = subprocess.run([
    "pg_restore", "--clean", "--if-exists", "--no-owner", "--no-acl",
    "-d", db, path,
], capture_output=True, text=True)
sys.stdout.write(result.stdout or "")
sys.stderr.write(result.stderr or "")
if result.returncode != 0:
    err = (result.stderr or "") + (result.stdout or "")
    if "transaction_timeout" in err and err.count("error:") <= 2:
        print("Restore OK (warning transaction_timeout ignoré)", flush=True)
    else:
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
else:
    print("Restore OK", flush=True)
'

export CONTAINER_NAME PRESIGNED_URL="$PRESIGNED_URL" PYTHON_SCRIPT
OVERRIDES="$(python3 - <<'PY'
import json, os
print(json.dumps({
  "containerOverrides": [{
    "name": os.environ["CONTAINER_NAME"],
    "command": ["python3", "-c", os.environ["PYTHON_SCRIPT"]],
    "environment": [
      {"name": "DUMP_PRESIGNED_URL", "value": os.environ["PRESIGNED_URL"]},
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
  echo "❌ pg_restore a échoué (exit=$EXIT_CODE). Voir logs CloudWatch /ecs/arquantix-api" >&2
  aws ecs update-service --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --service arquantix-api --desired-count 1 >/dev/null || true
  aws ecs update-service --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --service vancelian-next --desired-count 1 >/dev/null || true
  exit 1
fi
echo "   Restauration terminée."

echo "━━ 6/6 Remise en service ECS ━━"
aws ecs update-service --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --service arquantix-api --desired-count 1 >/dev/null
aws ecs update-service --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --service vancelian-next --desired-count 1 --force-new-deployment >/dev/null
aws ecs wait services-stable --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --services arquantix-api vancelian-next

echo "✓ Import local → prod terminé."
echo "  Snapshot RDS : $SNAPSHOT_ID"
echo "  Dump S3      : s3://${S3_BUCKET}/${S3_KEY}"
