#!/usr/bin/env bash
# Branche les secrets / env Morpho USDC Volt sur ECS vancelian-next (app + console).
#
# Usage (recommandé — valeurs sensibles via env, jamais commitées) :
#   BASE_RPC_URL_PRIMARY='https://base-mainnet.g.alchemy.com/v2/...' \
#   BASE_RPC_URL_FALLBACK='https://mainnet.base.org' \
#   MORPHO_USDC_BETA_PERSON_IDS='uuid1,uuid2' \
#   MORPHO_USDC_BETA_EMAILS='beta@example.com' \
#   ./scripts/vancelian-sync-morpho-prod.sh
#
# Dry-run (affiche le diff sans register / deploy) :
#   DRY_RUN=1 ./scripts/vancelian-sync-morpho-prod.sh
#
# Activer la beta (allowlist obligatoire) :
#   MORPHO_USDC_BETA_ENABLED=true MORPHO_USDC_BETA_PERSON_IDS=... ./scripts/vancelian-sync-morpho-prod.sh
#
# Prérequis : AWS CLI configuré (us-east-1), droits ECS + Secrets Manager.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECS_CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
ECS_SERVICE="${ECS_SERVICE:-vancelian-next}"
ECS_TASKDEF_FAMILY="${ECS_TASKDEF_FAMILY:-vancelian-next}"
DRY_RUN="${DRY_RUN:-0}"

SECRET_BASE_RPC_PRIMARY_NAME="${BASE_RPC_URL_PRIMARY_SECRET_NAME:-arquantix/prod/base-rpc-url-primary}"
SECRET_BASE_RPC_FALLBACK_NAME="${BASE_RPC_URL_FALLBACK_SECRET_NAME:-arquantix/prod/base-rpc-url-fallback}"
SECRET_PRIVY_APP_SECRET_NAME="${PRIVY_APP_SECRET_SECRET_NAME:-arquantix/prod/privy-app-secret}"

load_env_file() {
  local file=$1
  [[ -f "$file" ]] || return 0
  set -a
  # shellcheck disable=SC1090
  source "$file"
  set +a
}

upsert_secret() {
  local name=$1
  local value=$2
  local description=$3
  if [[ -z "$value" ]]; then
    return 0
  fi
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "  [dry-run] upsert secret $name"
    return 0
  fi
  if aws secretsmanager describe-secret --secret-id "$name" --region "$AWS_REGION" >/dev/null 2>&1; then
    aws secretsmanager put-secret-value --secret-id "$name" --secret-string "$value" --region "$AWS_REGION" >/dev/null
    echo "  updated $name"
  else
    aws secretsmanager create-secret \
      --name "$name" \
      --description "$description" \
      --secret-string "$value" \
      --region "$AWS_REGION" >/dev/null
    echo "  created $name"
  fi
}

secret_arn() {
  aws secretsmanager describe-secret --secret-id "$1" --region "$AWS_REGION" --query 'ARN' --output text 2>/dev/null || true
}

load_env_file "$ROOT_DIR/.env.arquantix"

# Fichier local optionnel (hors git) : ~/.config/vancelian/base-rpc-url-primary
LOCAL_RPC_FILE="${BASE_RPC_URL_PRIMARY_FILE:-$HOME/.config/vancelian/base-rpc-url-primary}"
if [[ -z "${BASE_RPC_URL_PRIMARY:-}" && -f "$LOCAL_RPC_FILE" ]]; then
  BASE_RPC_URL_PRIMARY="$(tr -d '\n\r' < "$LOCAL_RPC_FILE")"
  echo "  loaded BASE_RPC_URL_PRIMARY from $LOCAL_RPC_FILE"
fi

BASE_RPC_URL_PRIMARY="${BASE_RPC_URL_PRIMARY:-${BASE_RPC_URL:-}}"
BASE_RPC_URL_FALLBACK="${BASE_RPC_URL_FALLBACK:-https://mainnet.base.org}"

CURRENT_TD_ARN=$(aws ecs describe-services \
  --cluster "$ECS_CLUSTER" \
  --services "$ECS_SERVICE" \
  --region "$AWS_REGION" \
  --query 'services[0].taskDefinition' \
  --output text)
echo "  task definition courante : $CURRENT_TD_ARN"

CURRENT_MORPHO_ENV_JSON=$(aws ecs describe-task-definition \
  --task-definition "$CURRENT_TD_ARN" \
  --region "$AWS_REGION" \
  --query 'taskDefinition.containerDefinitions[0].environment' \
  --output json 2>/dev/null || echo '[]')

read_current_morpho_env() {
  python3 - <<'PY' "$CURRENT_MORPHO_ENV_JSON" "$1"
import json
import sys
items = json.loads(sys.argv[1])
name = sys.argv[2]
for item in items:
    if item.get("name") == name:
        print(item.get("value", ""))
        break
PY
}

inherit_morpho_env_if_unset() {
  local name=$1
  local current
  current=$(read_current_morpho_env "$name")
  if [[ -z "${!name:-}" && -n "$current" ]]; then
    printf -v "$name" '%s' "$current"
    echo "  hérité $name depuis la task definition courante"
  fi
}

CURRENT_RPC_SECRET_NAMES=$(aws ecs describe-task-definition \
  --task-definition "$CURRENT_TD_ARN" \
  --region "$AWS_REGION" \
  --query 'taskDefinition.containerDefinitions[0].secrets[*].name' \
  --output text 2>/dev/null || true)
CURRENT_HAS_RPC=false
if echo "$CURRENT_RPC_SECRET_NAMES" | grep -qE '(^|[[:space:]])BASE_RPC_URL_PRIMARY($|[[:space:]])'; then
  CURRENT_HAS_RPC=true
  echo "  RPC primary déjà branché sur la task definition courante"
fi

echo ""
echo "==> Secrets Manager (region=$AWS_REGION)"
if [[ -n "${BASE_RPC_URL_PRIMARY:-}" ]]; then
  upsert_secret "$SECRET_BASE_RPC_PRIMARY_NAME" "$BASE_RPC_URL_PRIMARY" "Base mainnet RPC primary (Alchemy/QuickNode)"
else
  echo "  skip $SECRET_BASE_RPC_PRIMARY_NAME (BASE_RPC_URL_PRIMARY non fourni)"
fi
if [[ -n "${BASE_RPC_URL_FALLBACK:-}" ]]; then
  upsert_secret "$SECRET_BASE_RPC_FALLBACK_NAME" "$BASE_RPC_URL_FALLBACK" "Base mainnet RPC fallback"
else
  echo "  skip $SECRET_BASE_RPC_FALLBACK_NAME (BASE_RPC_URL_FALLBACK vide)"
fi

BASE_RPC_PRIMARY_ARN=$(secret_arn "$SECRET_BASE_RPC_PRIMARY_NAME")
BASE_RPC_FALLBACK_ARN=$(secret_arn "$SECRET_BASE_RPC_FALLBACK_NAME")
PRIVY_APP_SECRET_ARN=$(secret_arn "$SECRET_PRIVY_APP_SECRET_NAME")
if [[ -z "$PRIVY_APP_SECRET_ARN" ]]; then
  echo "ERREUR: secret $SECRET_PRIVY_APP_SECRET_NAME introuvable. Exécuter arquantix-sync-privy-secrets.sh d'abord." >&2
  exit 1
fi

# Env Morpho — noms alignés sur morphoUsdcBetaConfig.ts / morphoReconciliationConfig.ts
# Flags beta hérités de la TD courante si non fournis (évite d’écraser prod par erreur).
for _morpho_flag in \
  MORPHO_USDC_BETA_ENABLED \
  MORPHO_USDC_DEPOSITS_DISABLED \
  MORPHO_USDC_WITHDRAWS_DISABLED \
  MORPHO_USDC_BETA_ALLOW_ALL_USERS \
  MORPHO_USDC_BETA_PERSON_IDS \
  MORPHO_USDC_BETA_EMAILS \
  MORPHO_USDC_BETA_PROFILE_TAG \
  MORPHO_USDC_BETA_INCLUDE_ADMINS; do
  inherit_morpho_env_if_unset "$_morpho_flag"
done

MORPHO_USDC_BETA_ENABLED="${MORPHO_USDC_BETA_ENABLED:-false}"
MORPHO_USDC_DEPOSITS_DISABLED="${MORPHO_USDC_DEPOSITS_DISABLED:-false}"
MORPHO_USDC_WITHDRAWS_DISABLED="${MORPHO_USDC_WITHDRAWS_DISABLED:-false}"
MORPHO_USDC_BETA_ALLOW_ALL_USERS="${MORPHO_USDC_BETA_ALLOW_ALL_USERS:-false}"
MORPHO_USDC_BETA_PERSON_IDS="${MORPHO_USDC_BETA_PERSON_IDS:-}"
MORPHO_USDC_BETA_EMAILS="${MORPHO_USDC_BETA_EMAILS:-}"
MORPHO_USDC_BETA_PROFILE_TAG="${MORPHO_USDC_BETA_PROFILE_TAG:-}"
MORPHO_USDC_BETA_INCLUDE_ADMINS="${MORPHO_USDC_BETA_INCLUDE_ADMINS:-false}"
MORPHO_USDC_BETA_MIN_DEPOSIT_USDC="${MORPHO_USDC_BETA_MIN_DEPOSIT_USDC:-0}"
MORPHO_USDC_BETA_MAX_DEPOSIT_USDC="${MORPHO_USDC_BETA_MAX_DEPOSIT_USDC:-0}"
MORPHO_USDC_BETA_MAX_USER_EXPOSURE_USDC="${MORPHO_USDC_BETA_MAX_USER_EXPOSURE_USDC:-0}"
MORPHO_USDC_BETA_MAX_GLOBAL_EXPOSURE_USDC="${MORPHO_USDC_BETA_MAX_GLOBAL_EXPOSURE_USDC:-0}"
MORPHO_USDC_MIN_DEPOSIT_RAW="${MORPHO_USDC_MIN_DEPOSIT_RAW:-0}"
MORPHO_USDC_MAX_DEPOSIT_RAW="${MORPHO_USDC_MAX_DEPOSIT_RAW:-0}"
MORPHO_USDC_MAX_USER_EXPOSURE_RAW="${MORPHO_USDC_MAX_USER_EXPOSURE_RAW:-0}"
MORPHO_USDC_MAX_GLOBAL_EXPOSURE_RAW="${MORPHO_USDC_MAX_GLOBAL_EXPOSURE_RAW:-0}"
MORPHO_RECONCILIATION_TOLERANCE_RAW="${MORPHO_RECONCILIATION_TOLERANCE_RAW:-10}"
MORPHO_ALERT_MISMATCH_TOLERANCE_RAW="${MORPHO_ALERT_MISMATCH_TOLERANCE_RAW:-1000000}"
MORPHO_PENDING_ALERT_MINUTES="${MORPHO_PENDING_ALERT_MINUTES:-15}"
# Production — sandbox/mock toujours désactivés sur vancelian-next (ignore .env local).
MORPHO_LOCAL_SANDBOX_ENABLED="false"
EXTERNAL_WALLET_LOCAL_MOCK_ENABLED="false"
LIFI_LOCAL_SANDBOX_ENABLED="false"
LIFI_SWAPS_MOCK="false"
APP_BASE_URL="${APP_BASE_URL:-https://app.vancelian.finance}"
ADMIN_BASE_URL="${ADMIN_BASE_URL:-https://console.vancelian.finance}"
NEXTAUTH_URL="${NEXTAUTH_URL:-https://app.vancelian.finance}"

if [[ "$MORPHO_USDC_BETA_ENABLED" == "true" && "$MORPHO_USDC_BETA_ALLOW_ALL_USERS" != "true" && -z "$MORPHO_USDC_BETA_PERSON_IDS" && -z "$MORPHO_USDC_BETA_EMAILS" && -z "$MORPHO_USDC_BETA_PROFILE_TAG" && "$MORPHO_USDC_BETA_INCLUDE_ADMINS" != "true" ]]; then
  echo "ERREUR: MORPHO_USDC_BETA_ENABLED=true sans allowlist ni MORPHO_USDC_BETA_ALLOW_ALL_USERS=true." >&2
  exit 1
fi

if [[ "$MORPHO_USDC_BETA_ENABLED" == "true" && "$CURRENT_HAS_RPC" != "true" && -z "$BASE_RPC_PRIMARY_ARN" && -z "${BASE_RPC_URL_PRIMARY:-}" && "${MORPHO_SYNC_SKIP_RPC_CHECK:-}" != "true" ]]; then
  echo "ERREUR: beta activée sans BASE_RPC_URL_PRIMARY (Alchemy/QuickNode requis)." >&2
  echo "  Contournement temporaire (déconseillé prod) : MORPHO_SYNC_SKIP_RPC_CHECK=true" >&2
  exit 1
fi
if [[ "$MORPHO_USDC_BETA_ENABLED" == "true" && "$CURRENT_HAS_RPC" != "true" && -z "$BASE_RPC_PRIMARY_ARN" && -z "${BASE_RPC_URL_PRIMARY:-}" && "${MORPHO_SYNC_SKIP_RPC_CHECK:-}" == "true" ]]; then
  echo "  ATTENTION: beta activée sans RPC production — rate limit public Base probable." >&2
fi

echo ""
echo "==> Mise à jour task definition ECS ($ECS_TASKDEF_FAMILY)"
TD_JSON=$(aws ecs describe-task-definition --task-definition "$ECS_TASKDEF_FAMILY" --region "$AWS_REGION" --query 'taskDefinition' --output json)

NEW_TD_JSON=$(python3 - <<'PY' \
  "$TD_JSON" \
  "$BASE_RPC_PRIMARY_ARN" \
  "$BASE_RPC_FALLBACK_ARN" \
  "$PRIVY_APP_SECRET_ARN" \
  "$BASE_RPC_URL_PRIMARY" \
  "$MORPHO_USDC_BETA_ENABLED" \
  "$MORPHO_USDC_DEPOSITS_DISABLED" \
  "$MORPHO_USDC_WITHDRAWS_DISABLED" \
  "$MORPHO_USDC_BETA_ALLOW_ALL_USERS" \
  "$MORPHO_USDC_BETA_PERSON_IDS" \
  "$MORPHO_USDC_BETA_EMAILS" \
  "$MORPHO_USDC_BETA_PROFILE_TAG" \
  "$MORPHO_USDC_BETA_INCLUDE_ADMINS" \
  "$MORPHO_USDC_BETA_MIN_DEPOSIT_USDC" \
  "$MORPHO_USDC_BETA_MAX_DEPOSIT_USDC" \
  "$MORPHO_USDC_BETA_MAX_USER_EXPOSURE_USDC" \
  "$MORPHO_USDC_BETA_MAX_GLOBAL_EXPOSURE_USDC" \
  "$MORPHO_USDC_MIN_DEPOSIT_RAW" \
  "$MORPHO_USDC_MAX_DEPOSIT_RAW" \
  "$MORPHO_USDC_MAX_USER_EXPOSURE_RAW" \
  "$MORPHO_USDC_MAX_GLOBAL_EXPOSURE_RAW" \
  "$MORPHO_RECONCILIATION_TOLERANCE_RAW" \
  "$MORPHO_ALERT_MISMATCH_TOLERANCE_RAW" \
  "$MORPHO_PENDING_ALERT_MINUTES" \
  "$MORPHO_LOCAL_SANDBOX_ENABLED" \
  "$EXTERNAL_WALLET_LOCAL_MOCK_ENABLED" \
  "$LIFI_LOCAL_SANDBOX_ENABLED" \
  "$LIFI_SWAPS_MOCK" \
  "$APP_BASE_URL" \
  "$ADMIN_BASE_URL" \
  "$NEXTAUTH_URL"
import json
import sys

td = json.loads(sys.argv[1])
base_rpc_primary_arn = sys.argv[2]
base_rpc_fallback_arn = sys.argv[3]
privy_secret_arn = sys.argv[4]
base_rpc_primary_plain = sys.argv[5]
morpho_env = {
    "MORPHO_USDC_BETA_ENABLED": sys.argv[6],
    "MORPHO_USDC_DEPOSITS_DISABLED": sys.argv[7],
    "MORPHO_USDC_WITHDRAWS_DISABLED": sys.argv[8],
    "MORPHO_USDC_BETA_ALLOW_ALL_USERS": sys.argv[9],
    "MORPHO_USDC_BETA_PERSON_IDS": sys.argv[10],
    "MORPHO_USDC_BETA_EMAILS": sys.argv[11],
    "MORPHO_USDC_BETA_PROFILE_TAG": sys.argv[12],
    "MORPHO_USDC_BETA_INCLUDE_ADMINS": sys.argv[13],
    "MORPHO_USDC_BETA_MIN_DEPOSIT_USDC": sys.argv[14],
    "MORPHO_USDC_BETA_MAX_DEPOSIT_USDC": sys.argv[15],
    "MORPHO_USDC_BETA_MAX_USER_EXPOSURE_USDC": sys.argv[16],
    "MORPHO_USDC_BETA_MAX_GLOBAL_EXPOSURE_USDC": sys.argv[17],
    "MORPHO_USDC_MIN_DEPOSIT_RAW": sys.argv[18],
    "MORPHO_USDC_MAX_DEPOSIT_RAW": sys.argv[19],
    "MORPHO_USDC_MAX_USER_EXPOSURE_RAW": sys.argv[20],
    "MORPHO_USDC_MAX_GLOBAL_EXPOSURE_RAW": sys.argv[21],
    "MORPHO_RECONCILIATION_TOLERANCE_RAW": sys.argv[22],
    "MORPHO_ALERT_MISMATCH_TOLERANCE_RAW": sys.argv[23],
    "MORPHO_PENDING_ALERT_MINUTES": sys.argv[24],
    "MORPHO_LOCAL_SANDBOX_ENABLED": sys.argv[25],
    "EXTERNAL_WALLET_LOCAL_MOCK_ENABLED": sys.argv[26],
    "LIFI_LOCAL_SANDBOX_ENABLED": sys.argv[27],
    "LIFI_SWAPS_MOCK": sys.argv[28],
    "APP_BASE_URL": sys.argv[29],
    "ADMIN_BASE_URL": sys.argv[30],
    "NEXTAUTH_URL": sys.argv[31],
    "NEXT_PUBLIC_BASE_CHAIN_ID": "8453",
}
if base_rpc_primary_plain:
    morpho_env["NEXT_PUBLIC_BASE_RPC_URL"] = base_rpc_primary_plain

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
env.update(morpho_env)
container["environment"] = [{"name": k, "value": v} for k, v in sorted(env.items()) if v != ""]

secret_names = {
    "BASE_RPC_URL",
    "BASE_RPC_URL_PRIMARY",
    "BASE_RPC_URL_FALLBACK",
    "NEXT_PUBLIC_BASE_RPC_URL",
    "PRIVY_APP_SECRET",
}
secrets = [item for item in container.get("secrets", []) if item.get("name") not in secret_names]
if privy_secret_arn:
    secrets.append({"name": "PRIVY_APP_SECRET", "valueFrom": privy_secret_arn})
if base_rpc_primary_arn:
    secrets.append({"name": "BASE_RPC_URL_PRIMARY", "valueFrom": base_rpc_primary_arn})
    secrets.append({"name": "BASE_RPC_URL", "valueFrom": base_rpc_primary_arn})
    if "NEXT_PUBLIC_BASE_RPC_URL" not in morpho_env:
        secrets.append({"name": "NEXT_PUBLIC_BASE_RPC_URL", "valueFrom": base_rpc_primary_arn})
if base_rpc_fallback_arn:
    secrets.append({"name": "BASE_RPC_URL_FALLBACK", "valueFrom": base_rpc_fallback_arn})
container["secrets"] = secrets

print(json.dumps(td, indent=2))
PY
)

if [[ "$DRY_RUN" == "1" ]]; then
  echo "$NEW_TD_JSON" | python3 -c "import json,sys; td=json.load(sys.stdin); c=td['containerDefinitions'][0]; print('environment Morpho/RPC:'); [print(f'  {e[\"name\"]}={e[\"value\"][:40]}...' if len(e['value'])>40 else f'  {e[\"name\"]}={e[\"value\"]}') for e in c.get('environment',[]) if e['name'].startswith('MORPHO_') or 'BASE' in e['name']]; print('secrets RPC:'); [print(f'  {s[\"name\"]}') for s in c.get('secrets',[]) if 'RPC' in s['name'] or s['name']=='PRIVY_APP_SECRET']"
  echo ""
  echo "[dry-run] Aucune modification ECS effectuée."
  exit 0
fi

TMP_TD=$(mktemp)
echo "$NEW_TD_JSON" > "$TMP_TD"
NEW_TASK_ARN=$(aws ecs register-task-definition --region "$AWS_REGION" --cli-input-json "file://$TMP_TD" --query 'taskDefinition.taskDefinitionArn' --output text)
rm -f "$TMP_TD"
echo "  registered $NEW_TASK_ARN"

echo ""
echo "==> Rolling deployment ECS ($ECS_CLUSTER / $ECS_SERVICE)"
aws ecs update-service \
  --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" \
  --task-definition "$NEW_TASK_ARN" \
  --force-new-deployment \
  --region "$AWS_REGION" \
  --query 'service.{serviceName:serviceName,taskDefinition:taskDefinition,desiredCount:desiredCount}' \
  --output json

echo ""
echo "==> Attente stabilisation (max 15 min)…"
aws ecs wait services-stable --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE" --region "$AWS_REGION"

echo ""
echo "Terminé."
echo "  Service     : $ECS_SERVICE (app.vancelian.finance + console.vancelian.finance)"
echo "  Task def    : $NEW_TASK_ARN"
echo "  Monitoring  : https://console.vancelian.finance/admin/morpho-vaults/monitoring"
echo ""
echo "Prochaines étapes :"
echo "  1. Déployer le code Morpho Phase 4 (push main → workflow vancelian-next-deploy)"
echo "  2. npx prisma migrate deploy (prod) — voir scripts/vancelian-morpho-ecs-run-job.sh migrate"
echo "  3. ./scripts/vancelian-morpho-ecs-run-job.sh sync-registry"
echo "  4. ./scripts/vancelian-morpho-ecs-run-job.sh reconcile"
echo "  5. ./scripts/vancelian-morpho-eventbridge-setup.sh (cron prod)"
