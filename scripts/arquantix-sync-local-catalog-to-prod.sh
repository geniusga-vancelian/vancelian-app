#!/usr/bin/env bash
# Sync sélective local → RDS prod : instruments, bundles crypto (PE), offres exclusives (Vault Builder).
# Ne remplace pas la homepage ni les autres pages CMS.
#
# Usage :
#   bash scripts/arquantix-sync-local-catalog-to-prod.sh
#   bash scripts/arquantix-sync-local-catalog-to-prod.sh --dry-run
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=arquantix_compose_lib.sh
source "$REPO_ROOT/scripts/arquantix_compose_lib.sh"
arquantix_lib_set_root "$REPO_ROOT"

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
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

ENV_FILE="$REPO_ROOT/.env.arquantix"
DB_NAME="$( (grep -E '^[[:space:]]*DB_NAME=' "$ENV_FILE" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
DB_USER="$( (grep -E '^[[:space:]]*DB_USER=' "$ENV_FILE" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
DB_PASSWORD="$( (grep -E '^[[:space:]]*DB_PASSWORD=' "$ENV_FILE" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
DB_PORT="$( (grep -E '^[[:space:]]*DB_PORT=' "$ENV_FILE" || true) | head -1 | cut -d= -f2- | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
[[ -z "$DB_NAME" ]] && DB_NAME="arquantix_fresh"
[[ -z "$DB_USER" ]] && DB_USER="arquantix"
[[ -z "$DB_PASSWORD" ]] && DB_PASSWORD="arquantix"
[[ -z "$DB_PORT" ]] && DB_PORT="5443"

TS="$(date +%Y%m%d-%H%M%S)"
WORKDIR="${HOME}/backups/arquantix_catalog_sync_${TS}"
PRE_SQL="${WORKDIR}/pre_sync.sql"
CORE_DUMP="${WORKDIR}/core_sync.dump"
CMS_DUMP="${WORKDIR}/cms_sync.dump"
VAULT_DUMP="${WORKDIR}/vault_sync.dump"
S3_CORE_KEY="${S3_PREFIX}/catalog_sync_${TS}_core.dump"
S3_CMS_KEY="${S3_PREFIX}/catalog_sync_${TS}_cms.dump"
S3_PRE_KEY="${S3_PREFIX}/catalog_sync_${TS}_pre.sql"
S3_VAULT_KEY="${S3_PREFIX}/catalog_sync_${TS}_vault.dump"
SNAPSHOT_ID="${RDS_ID}-pre-catalog-sync-${TS}"

mkdir -p "$WORKDIR"

CORE_TABLES=(
  market_data_instruments
  market_data_latest_quotes
  pe_assets
  pe_instruments
  pe_product_definitions
  pe_portfolio_templates
  pe_template_allocations
  portfolio_product_configs
  bundles
  bundle_allocations
  investment_categories
  investment_types
)

CMS_TABLES=(
  projects
  project_i18n
  project_media
  packaged_products
)

pg_local() {
  PGPASSWORD="$DB_PASSWORD" docker run --rm -i \
    -e PGPASSWORD \
    --add-host=host.docker.internal:host-gateway \
    postgres:15-alpine \
    psql -h host.docker.internal -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" "$@"
}

pg_dump_local() {
  local out="$1"
  shift
  local args=()
  for t in "$@"; do args+=(-t "public.${t}"); done
  PGPASSWORD="$DB_PASSWORD" docker run --rm \
    -e PGPASSWORD \
    --add-host=host.docker.internal:host-gateway \
    -v "${WORKDIR}:/work" \
    postgres:15-alpine \
    pg_dump -h host.docker.internal -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
      --data-only --no-owner --no-acl -Fc -f "/work/$(basename "$out")" \
      "${args[@]}"
}

echo "━━ 1/7 Snapshot RDS prod ━━"
if [[ "$DRY_RUN" -eq 0 ]]; then
  aws rds create-db-snapshot \
    --region "$AWS_REGION" \
    --db-instance-identifier "$RDS_ID" \
    --db-snapshot-identifier "$SNAPSHOT_ID" \
    --output text >/dev/null
  echo "   Snapshot : $SNAPSHOT_ID"
else
  echo "   [dry-run] Snapshot : $SNAPSHOT_ID"
fi

echo "━━ 2/7 Export SQL pré-sync (purge ciblée prod) ━━"
cat >"$PRE_SQL" <<'EOSQL'
BEGIN;
SET session_replication_role = replica;

DELETE FROM lending_pool_products
WHERE packaged_product_id IN (
  SELECT id FROM packaged_products WHERE product_type = 'EXCLUSIVE_OFFER'
);

DELETE FROM section_contents
WHERE section_id IN (
  SELECT s.id
  FROM sections s
  JOIN pages p ON p.id = s.page_id
  WHERE p.template = 'vault_builder'
);

DELETE FROM sections
WHERE page_id IN (SELECT id FROM pages WHERE template = 'vault_builder');

DELETE FROM page_i18n
WHERE page_id IN (SELECT id FROM pages WHERE template = 'vault_builder');

DELETE FROM packaged_products;
DELETE FROM project_media;

DELETE FROM media
WHERE id IN (
  SELECT cover_media_id FROM projects WHERE cover_media_id IS NOT NULL
  UNION
  SELECT hero_media_id FROM projects WHERE hero_media_id IS NOT NULL
  UNION
  SELECT media_id FROM project_media
);

DELETE FROM project_i18n;
DELETE FROM projects;
DELETE FROM pages WHERE template = 'vault_builder';

DELETE FROM bundle_allocations;
DELETE FROM bundles;
DELETE FROM pe_template_allocations;
DELETE FROM pe_portfolio_templates;
DELETE FROM pe_product_definitions;
DELETE FROM pe_instruments;
DELETE FROM pe_assets;
DELETE FROM portfolio_product_configs;

DELETE FROM market_data_latest_quotes;
DELETE FROM market_data_instruments;

DELETE FROM investment_types;
DELETE FROM investment_categories;

COMMIT;
EOSQL

echo "━━ 3/7 Dump local (data-only) ━━"
pg_dump_local "$CORE_DUMP" "${CORE_TABLES[@]}"
pg_dump_local "$CMS_DUMP" "${CMS_TABLES[@]}"

docker exec -i arquantixrecovery-arquantix-db-1 psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'EOSQL'
DROP TABLE IF EXISTS _sync_pages, _sync_page_i18n, _sync_sections, _sync_section_contents, _sync_media;
CREATE TABLE _sync_pages AS SELECT * FROM pages WHERE template = 'vault_builder';
CREATE TABLE _sync_page_i18n AS SELECT * FROM page_i18n WHERE page_id IN (SELECT id FROM _sync_pages);
CREATE TABLE _sync_sections AS SELECT * FROM sections WHERE page_id IN (SELECT id FROM _sync_pages);
CREATE TABLE _sync_section_contents AS
  SELECT sc.* FROM section_contents sc
  JOIN _sync_sections s ON s.id = sc.section_id;
CREATE TABLE _sync_media AS SELECT * FROM media WHERE id IN (
  SELECT cover_media_id FROM projects WHERE cover_media_id IS NOT NULL
  UNION SELECT hero_media_id FROM projects WHERE hero_media_id IS NOT NULL
  UNION SELECT media_id FROM project_media
);
EOSQL

pg_dump_local "$VAULT_DUMP" _sync_pages _sync_page_i18n _sync_sections _sync_section_contents _sync_media

docker exec -i arquantixrecovery-arquantix-db-1 psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'EOSQL'
DROP TABLE IF EXISTS _sync_pages, _sync_page_i18n, _sync_sections, _sync_section_contents, _sync_media;
EOSQL

echo "   core_sync.dump  : $(wc -c < "$CORE_DUMP" | tr -d ' ') bytes"
echo "   cms_sync.dump   : $(wc -c < "$CMS_DUMP" | tr -d ' ') bytes"
echo "   vault_sync.dump : $(wc -c < "$VAULT_DUMP" | tr -d ' ') bytes"
pg_local -t -A -c "
SELECT 'instruments', count(*) FROM market_data_instruments
UNION ALL SELECT 'pe_product_definitions', count(*) FROM pe_product_definitions
UNION ALL SELECT 'packaged_products', count(*) FROM packaged_products
UNION ALL SELECT 'projects', count(*) FROM projects
UNION ALL SELECT 'vault_pages', count(*) FROM pages WHERE template='vault_builder';
"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "✓ Dry-run terminé. Fichiers dans $WORKDIR"
  exit 0
fi

echo "━━ 4/7 Upload S3 ━━"
aws s3 cp "$CORE_DUMP" "s3://${S3_BUCKET}/${S3_CORE_KEY}" --region "$AWS_REGION"
aws s3 cp "$CMS_DUMP" "s3://${S3_BUCKET}/${S3_CMS_KEY}" --region "$AWS_REGION"
aws s3 cp "$PRE_SQL" "s3://${S3_BUCKET}/${S3_PRE_KEY}" --region "$AWS_REGION"
aws s3 cp "$VAULT_DUMP" "s3://${S3_BUCKET}/${S3_VAULT_KEY}" --region "$AWS_REGION"
PRESIGNED_CORE="$(aws s3 presign "s3://${S3_BUCKET}/${S3_CORE_KEY}" --expires-in 7200 --region "$AWS_REGION")"
PRESIGNED_CMS="$(aws s3 presign "s3://${S3_BUCKET}/${S3_CMS_KEY}" --expires-in 7200 --region "$AWS_REGION")"
PRESIGNED_PRE="$(aws s3 presign "s3://${S3_BUCKET}/${S3_PRE_KEY}" --expires-in 7200 --region "$AWS_REGION")"
PRESIGNED_VAULT="$(aws s3 presign "s3://${S3_BUCKET}/${S3_VAULT_KEY}" --expires-in 7200 --region "$AWS_REGION")"

echo "━━ 5/7 Pause trafic API ━━"
aws ecs update-service --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --service arquantix-api --desired-count 0 >/dev/null || true
sleep 10

echo "━━ 6/7 Apply sur RDS via ECS one-shot ━━"
PYTHON_SCRIPT='import os, subprocess, sys, urllib.request

def download(url, path):
    print(f"Downloading {path}…", flush=True)
    urllib.request.urlretrieve(url, path)

def pg_restore_data(path, label):
    print(f"pg_restore {label}…", flush=True)
    result = subprocess.run([
        "pg_restore", "--data-only", "--no-owner", "--no-acl", "-d",
        os.environ["DATABASE_URL"], path,
    ], capture_output=True, text=True)
    out = (result.stdout or "") + (result.stderr or "")
    sys.stdout.write(out)
    if result.returncode != 0:
        fatal = []
        for line in out.splitlines():
            low = line.lower()
            if "error:" not in low:
                continue
            if "transaction_timeout" in low:
                continue
            if "permission denied" in low and "trigger" in low:
                continue
            fatal.append(line)
        if fatal:
            raise RuntimeError(f"pg_restore {label} failed:\n" + "\n".join(fatal))
        print(f"pg_restore {label} completed with ignorable warnings", flush=True)

db = os.environ["DATABASE_URL"]
download(os.environ["PRE_URL"], "/tmp/pre.sql")
download(os.environ["VAULT_URL"], "/tmp/vault.dump")
download(os.environ["CORE_URL"], "/tmp/core.dump")
download(os.environ["CMS_URL"], "/tmp/cms.dump")

print("Pre-sync DELETE…", flush=True)
subprocess.check_call(["psql", db, "-v", "ON_ERROR_STOP=1", "-f", "/tmp/pre.sql"])

print("Create temp vault tables…", flush=True)
create_temp = """
DROP TABLE IF EXISTS _sync_pages, _sync_page_i18n, _sync_sections, _sync_section_contents, _sync_media;
CREATE TABLE _sync_pages (LIKE pages INCLUDING ALL);
CREATE TABLE _sync_page_i18n (LIKE page_i18n INCLUDING ALL);
CREATE TABLE _sync_sections (LIKE sections INCLUDING ALL);
CREATE TABLE _sync_section_contents (LIKE section_contents INCLUDING ALL);
CREATE TABLE _sync_media (LIKE media INCLUDING ALL);
"""
subprocess.check_call(["psql", db, "-v", "ON_ERROR_STOP=1", "-c", create_temp])

pg_restore_data("/tmp/vault.dump", "vault")

print("Remap vault temp tables → prod tables…", flush=True)
remap_sql = """
BEGIN;
SET session_replication_role = replica;
INSERT INTO media SELECT * FROM _sync_media ON CONFLICT (id) DO NOTHING;
INSERT INTO pages SELECT * FROM _sync_pages ON CONFLICT (id) DO UPDATE SET
  slug = EXCLUDED.slug, template = EXCLUDED.template, url_path = EXCLUDED.url_path,
  title = EXCLUDED.title, description = EXCLUDED.description, updated_at = EXCLUDED.updated_at;
INSERT INTO page_i18n SELECT * FROM _sync_page_i18n
  ON CONFLICT (page_id, locale) DO UPDATE SET
  title = EXCLUDED.title, description = EXCLUDED.description,
  og_title = EXCLUDED.og_title, og_description = EXCLUDED.og_description;
INSERT INTO sections SELECT * FROM _sync_sections ON CONFLICT (id) DO UPDATE SET
  page_id = EXCLUDED.page_id, key = EXCLUDED.key, \"order\" = EXCLUDED.\"order\";
INSERT INTO section_contents SELECT * FROM _sync_section_contents
  ON CONFLICT (section_id, locale, status) DO UPDATE SET
  data = EXCLUDED.data, updated_at = EXCLUDED.updated_at;
DROP TABLE IF EXISTS _sync_pages, _sync_page_i18n, _sync_sections, _sync_section_contents, _sync_media;
COMMIT;
"""
subprocess.check_call(["psql", db, "-v", "ON_ERROR_STOP=1", "-c", remap_sql])

pg_restore_data("/tmp/core.dump", "core")
pg_restore_data("/tmp/cms.dump", "cms")
print("Catalog sync OK", flush=True)
'

export CONTAINER_NAME PRESIGNED_CORE PRESIGNED_CMS PRESIGNED_PRE PRESIGNED_VAULT PYTHON_SCRIPT
OVERRIDES="$(python3 - <<'PY'
import json, os
print(json.dumps({
  "containerOverrides": [{
    "name": os.environ["CONTAINER_NAME"],
    "command": ["python3", "-c", os.environ["PYTHON_SCRIPT"]],
    "environment": [
      {"name": "CORE_URL", "value": os.environ["PRESIGNED_CORE"]},
      {"name": "CMS_URL", "value": os.environ["PRESIGNED_CMS"]},
      {"name": "PRE_URL", "value": os.environ["PRESIGNED_PRE"]},
      {"name": "VAULT_URL", "value": os.environ["PRESIGNED_VAULT"]},
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
  echo "❌ Sync catalog a échoué (exit=$EXIT_CODE). Logs : /ecs/arquantix-api" >&2
  aws ecs update-service --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --service arquantix-api --desired-count 1 >/dev/null || true
  exit 1
fi

echo "━━ 7/7 Remise en service API ━━"
aws ecs update-service --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --service arquantix-api --desired-count 1 --force-new-deployment >/dev/null
aws ecs wait services-stable --region "$AWS_REGION" --cluster "$ECS_CLUSTER" --services arquantix-api || true

echo "✓ Sync catalog local → prod terminé."
echo "  Snapshot : $SNAPSHOT_ID"
echo "  Dumps S3 : s3://${S3_BUCKET}/${S3_PREFIX}/catalog_sync_${TS}_*.dump"
