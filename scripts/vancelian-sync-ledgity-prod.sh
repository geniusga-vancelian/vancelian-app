#!/usr/bin/env bash
# Active les vaults Ledgity live sur ECS vancelian-next (accès ouvert, plafonds faibles).
#
# Usage :
#   BASE_RPC_URL_PRIMARY='https://base-mainnet.g.alchemy.com/v2/...' \
#   ./scripts/vancelian-sync-ledgity-prod.sh
#
# Dry-run :
#   DRY_RUN=1 ./scripts/vancelian-sync-ledgity-prod.sh
#
# Prérequis : AWS CLI (us-east-1), droits ECS + Secrets Manager.
# Déployer le code Ledgity sur main avant (workflow vancelian-next-deploy).
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
  --output text 2>/dev/null || true)

CURRENT_HAS_RPC="false"
if [[ -n "$CURRENT_TD_ARN" && "$CURRENT_TD_ARN" != "None" ]]; then
  CURRENT_HAS_RPC=$(aws ecs describe-task-definition \
    --task-definition "$CURRENT_TD_ARN" \
    --region "$AWS_REGION" \
    --query 'taskDefinition.containerDefinitions[0].secrets[?name==`BASE_RPC_URL_PRIMARY`].name | [0]' \
    --output text 2>/dev/null || echo "false")
  [[ "$CURRENT_HAS_RPC" == "BASE_RPC_URL_PRIMARY" ]] && CURRENT_HAS_RPC="true" || CURRENT_HAS_RPC="false"
fi

echo "==> Secrets RPC Base (Alchemy primary + fallback public)"
if [[ -n "${BASE_RPC_URL_PRIMARY:-}" ]]; then
  upsert_secret "$SECRET_BASE_RPC_PRIMARY_NAME" "$BASE_RPC_URL_PRIMARY" "Base mainnet RPC primary (Alchemy/QuickNode)"
else
  echo "  skip $SECRET_BASE_RPC_PRIMARY_NAME (BASE_RPC_URL_PRIMARY non fourni)"
fi
upsert_secret "$SECRET_BASE_RPC_FALLBACK_NAME" "$BASE_RPC_URL_FALLBACK" "Base mainnet RPC fallback (public)"

BASE_RPC_PRIMARY_ARN=$(secret_arn "$SECRET_BASE_RPC_PRIMARY_NAME")
BASE_RPC_FALLBACK_ARN=$(secret_arn "$SECRET_BASE_RPC_FALLBACK_NAME")
PRIVY_APP_SECRET_ARN=$(secret_arn "$SECRET_PRIVY_APP_SECRET_NAME")

if [[ "$DRY_RUN" != "1" && -z "$PRIVY_APP_SECRET_ARN" ]]; then
  echo "ERREUR: secret $SECRET_PRIVY_APP_SECRET_NAME introuvable." >&2
  exit 1
fi

# Ledgity live — accès ouvert, plafonds faibles, beta OFF
LEDGITY_VAULTS_ENABLED="${LEDGITY_VAULTS_ENABLED:-true}"
LEDGITY_BETA_ENABLED="${LEDGITY_BETA_ENABLED:-false}"
LEDGITY_DEPOSITS_DISABLED="${LEDGITY_DEPOSITS_DISABLED:-false}"
LEDGITY_WITHDRAWS_DISABLED="${LEDGITY_WITHDRAWS_DISABLED:-false}"
LEDGITY_MAX_DEPOSIT_RAW="${LEDGITY_MAX_DEPOSIT_RAW:-10000000}"
LEDGITY_MAX_USER_EXPOSURE_RAW="${LEDGITY_MAX_USER_EXPOSURE_RAW:-50000000}"
LEDGITY_MAX_GLOBAL_EXPOSURE_RAW="${LEDGITY_MAX_GLOBAL_EXPOSURE_RAW:-500000000}"
LEDGITY_MIN_DEPOSIT_RAW="${LEDGITY_MIN_DEPOSIT_RAW:-1000000}"
LEDGITY_RECONCILIATION_TOLERANCE_RAW="${LEDGITY_RECONCILIATION_TOLERANCE_RAW:-10}"
LEDGITY_ALERT_MISMATCH_TOLERANCE_RAW="${LEDGITY_ALERT_MISMATCH_TOLERANCE_RAW:-1000000}"
LEDGITY_PENDING_ALERT_MINUTES="${LEDGITY_PENDING_ALERT_MINUTES:-15}"
LEDGITY_LIQUIDITY_WARNING_RATIO_BPS="${LEDGITY_LIQUIDITY_WARNING_RATIO_BPS:-1000}"
LEDGITY_LOCAL_SANDBOX_ENABLED="false"
MORPHO_LOCAL_SANDBOX_ENABLED="${MORPHO_LOCAL_SANDBOX_ENABLED:-false}"
EXTERNAL_WALLET_LOCAL_MOCK_ENABLED="false"
LIFI_LOCAL_SANDBOX_ENABLED="false"
LIFI_SWAPS_MOCK="false"
APP_BASE_URL="${APP_BASE_URL:-https://app.vancelian.finance}"
ADMIN_BASE_URL="${ADMIN_BASE_URL:-https://console.vancelian.finance}"
NEXTAUTH_URL="${NEXTAUTH_URL:-https://app.vancelian.finance}"

if [[ "$LEDGITY_VAULTS_ENABLED" != "true" ]]; then
  echo "ERREUR: LEDGITY_VAULTS_ENABLED doit être true pour ce script." >&2
  exit 1
fi

if [[ "$LEDGITY_BETA_ENABLED" == "true" ]]; then
  echo "ERREUR: LEDGITY_BETA_ENABLED=true interdit — utiliser accès ouvert + plafonds LEDGITY_MAX_*_RAW." >&2
  exit 1
fi

if [[ "$CURRENT_HAS_RPC" != "true" && -z "$BASE_RPC_PRIMARY_ARN" && -z "${BASE_RPC_URL_PRIMARY:-}" && "${LEDGITY_SYNC_SKIP_RPC_CHECK:-}" != "true" ]]; then
  echo "ERREUR: Ledgity live sans BASE_RPC_URL_PRIMARY (Alchemy requis)." >&2
  exit 1
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
  "$LEDGITY_VAULTS_ENABLED" \
  "$LEDGITY_BETA_ENABLED" \
  "$LEDGITY_DEPOSITS_DISABLED" \
  "$LEDGITY_WITHDRAWS_DISABLED" \
  "$LEDGITY_MAX_DEPOSIT_RAW" \
  "$LEDGITY_MAX_USER_EXPOSURE_RAW" \
  "$LEDGITY_MAX_GLOBAL_EXPOSURE_RAW" \
  "$LEDGITY_MIN_DEPOSIT_RAW" \
  "$LEDGITY_RECONCILIATION_TOLERANCE_RAW" \
  "$LEDGITY_ALERT_MISMATCH_TOLERANCE_RAW" \
  "$LEDGITY_PENDING_ALERT_MINUTES" \
  "$LEDGITY_LIQUIDITY_WARNING_RATIO_BPS" \
  "$LEDGITY_LOCAL_SANDBOX_ENABLED" \
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
ledgity_env = {
    "LEDGITY_VAULTS_ENABLED": sys.argv[6],
    "LEDGITY_BETA_ENABLED": sys.argv[7],
    "LEDGITY_DEPOSITS_DISABLED": sys.argv[8],
    "LEDGITY_WITHDRAWS_DISABLED": sys.argv[9],
    "LEDGITY_MAX_DEPOSIT_RAW": sys.argv[10],
    "LEDGITY_MAX_USER_EXPOSURE_RAW": sys.argv[11],
    "LEDGITY_MAX_GLOBAL_EXPOSURE_RAW": sys.argv[12],
    "LEDGITY_MIN_DEPOSIT_RAW": sys.argv[13],
    "LEDGITY_RECONCILIATION_TOLERANCE_RAW": sys.argv[14],
    "LEDGITY_ALERT_MISMATCH_TOLERANCE_RAW": sys.argv[15],
    "LEDGITY_PENDING_ALERT_MINUTES": sys.argv[16],
    "LEDGITY_LIQUIDITY_WARNING_RATIO_BPS": sys.argv[17],
    "LEDGITY_LOCAL_SANDBOX_ENABLED": sys.argv[18],
    "MORPHO_LOCAL_SANDBOX_ENABLED": sys.argv[19],
    "EXTERNAL_WALLET_LOCAL_MOCK_ENABLED": sys.argv[20],
    "LIFI_LOCAL_SANDBOX_ENABLED": sys.argv[21],
    "LIFI_SWAPS_MOCK": sys.argv[22],
    "APP_BASE_URL": sys.argv[23],
    "ADMIN_BASE_URL": sys.argv[24],
    "NEXTAUTH_URL": sys.argv[25],
    "NEXT_PUBLIC_BASE_CHAIN_ID": "8453",
}
if base_rpc_primary_plain:
    ledgity_env["NEXT_PUBLIC_BASE_RPC_URL"] = base_rpc_primary_plain

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
env.update(ledgity_env)
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
    if "NEXT_PUBLIC_BASE_RPC_URL" not in ledgity_env:
        secrets.append({"name": "NEXT_PUBLIC_BASE_RPC_URL", "valueFrom": base_rpc_primary_arn})
if base_rpc_fallback_arn:
    secrets.append({"name": "BASE_RPC_URL_FALLBACK", "valueFrom": base_rpc_fallback_arn})
container["secrets"] = secrets

print(json.dumps(td, indent=2))
PY
)

if [[ "$DRY_RUN" == "1" ]]; then
  echo "$NEW_TD_JSON" | python3 -c "import json,sys; td=json.load(sys.stdin); c=td['containerDefinitions'][0]; print('environment Ledgity/RPC:'); [print(f'  {e[\"name\"]}={e[\"value\"]}') for e in c.get('environment',[]) if e['name'].startswith('LEDGITY_') or e['name'] in ('NEXT_PUBLIC_BASE_RPC_URL','NEXT_PUBLIC_BASE_CHAIN_ID')]; print('secrets RPC:'); [print(f'  {s[\"name\"]}') for s in c.get('secrets',[]) if 'RPC' in s['name'] or s['name']=='PRIVY_APP_SECRET']"
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
echo "  Service     : $ECS_SERVICE (app.vancelian.finance)"
echo "  Monitoring  : https://console.vancelian.finance/admin/ledgity-vaults/monitoring"
echo ""
echo "Prochaines étapes :"
echo "  1. Smoke tests lyUSDC + lyEURC (Privy + MetaMask) — voir docs/arquantix/LEDGITY_LIVE_RUNBOOK.md"
echo "  2. cd services/arquantix/web && npm run ledgity:reconcile"
echo "  3. Cron 06:15 UTC — scripts/ledgity-cron.crontab.example"
