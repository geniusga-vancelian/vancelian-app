#!/usr/bin/env bash
# Crée ou met à jour les secrets Privy API dans AWS Secrets Manager (us-east-1).
#
# Usage complet (recommandé avant go-live dépôts live) :
#   PRIVY_APP_ID=... \
#   PRIVY_JWKS_URL=... \
#   PRIVY_APP_SECRET=... \
#   PRIVY_WEBHOOK_SECRET=whsec_... \
#   ./scripts/arquantix-sync-privy-secrets.sh
#
# Ou sans args : lit depuis la task ECS arquantix-api courante (env ou secrets).
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
SECRET_APP_ID_NAME="${PRIVY_APP_ID_SECRET_NAME:-arquantix/prod/privy-app-id}"
SECRET_JWKS_URL_NAME="${PRIVY_JWKS_URL_SECRET_NAME:-arquantix/prod/privy-jwks-url}"
SECRET_APP_SECRET_NAME="${PRIVY_APP_SECRET_SECRET_NAME:-arquantix/prod/privy-app-secret}"
SECRET_WEBHOOK_SECRET_NAME="${PRIVY_WEBHOOK_SECRET_SECRET_NAME:-arquantix/prod/privy-webhook-secret}"

upsert_secret() {
  local name=$1
  local value=$2
  if [[ -z "$value" ]]; then
    echo "  skip $name (valeur vide)"
    return 0
  fi
  if aws secretsmanager describe-secret --secret-id "$name" --region "$AWS_REGION" >/dev/null 2>&1; then
    aws secretsmanager put-secret-value --secret-id "$name" --secret-string "$value" --region "$AWS_REGION" >/dev/null
    echo "  updated $name"
  else
    aws secretsmanager create-secret \
      --name "$name" \
      --description "Privy config for arquantix-api ECS" \
      --secret-string "$value" \
      --region "$AWS_REGION" >/dev/null
    echo "  created $name"
  fi
}

if [[ -z "${PRIVY_APP_ID:-}" || -z "${PRIVY_JWKS_URL:-}" ]]; then
  echo "==> Lecture depuis task definition arquantix-api (ECS)"
  TD=$(aws ecs describe-task-definition --task-definition arquantix-api --region "$AWS_REGION" --query 'taskDefinition.containerDefinitions[0]' --output json)
  PRIVY_APP_ID=$(echo "$TD" | python3 -c "import json,sys; c=json.load(sys.stdin); env={e['name']:e['value'] for e in c.get('environment',[])}; print(env.get('PRIVY_APP_ID',''))")
  PRIVY_JWKS_URL=$(echo "$TD" | python3 -c "import json,sys; c=json.load(sys.stdin); env={e['name']:e['value'] for e in c.get('environment',[])}; print(env.get('PRIVY_JWKS_URL',''))")
  if [[ -z "$PRIVY_APP_ID" ]]; then
    PRIVY_APP_ID=$(aws secretsmanager get-secret-value --secret-id "$SECRET_APP_ID_NAME" --region "$AWS_REGION" --query SecretString --output text 2>/dev/null || true)
  fi
  if [[ -z "$PRIVY_JWKS_URL" ]]; then
    PRIVY_JWKS_URL=$(aws secretsmanager get-secret-value --secret-id "$SECRET_JWKS_URL_NAME" --region "$AWS_REGION" --query SecretString --output text 2>/dev/null || true)
  fi
fi

if [[ -z "${PRIVY_APP_ID:-}" ]]; then
  echo "PRIVY_APP_ID requis (env ou dashboard Privy)." >&2
  exit 1
fi
if [[ -z "${PRIVY_JWKS_URL:-}" ]]; then
  PRIVY_JWKS_URL="https://auth.privy.io/api/v1/apps/${PRIVY_APP_ID}/jwks.json"
fi

echo "==> Secrets Manager (region=$AWS_REGION)"
upsert_secret "$SECRET_APP_ID_NAME" "$PRIVY_APP_ID"
upsert_secret "$SECRET_JWKS_URL_NAME" "$PRIVY_JWKS_URL"
upsert_secret "$SECRET_APP_SECRET_NAME" "${PRIVY_APP_SECRET:-}"
upsert_secret "$SECRET_WEBHOOK_SECRET_NAME" "${PRIVY_WEBHOOK_SECRET:-}"

echo ""
echo "ARNs (pour task definition ECS arquantix-api — secrets[]) :"
for name in "$SECRET_APP_ID_NAME" "$SECRET_JWKS_URL_NAME" "$SECRET_APP_SECRET_NAME" "$SECRET_WEBHOOK_SECRET_NAME"; do
  if aws secretsmanager describe-secret --secret-id "$name" --region "$AWS_REGION" >/dev/null 2>&1; then
    aws secretsmanager describe-secret --secret-id "$name" --region "$AWS_REGION" --query 'ARN' --output text
  fi
done
echo ""
echo "Variables plain ECS (environment[]) :"
echo "  PRIVY_EXCHANGE_VERIFICATION_MODE=jwt"
echo "  PRIVY_WEBHOOK_VERIFICATION_MODE=svix"
echo ""
echo "Webhook dashboard Privy → https://api.arquantix.com/api/webhooks/privy"
echo "Événement : wallet.funds_deposited"
echo ""
echo "Post-deploy : GET https://api.arquantix.com/api/admin/privy-wallet/infra-readiness (admin)"
