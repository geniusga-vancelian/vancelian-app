#!/usr/bin/env bash
# ============================================================================
# scripts/aws/github-oidc/setup.sh
#
# Idempotent setup of the GitHub Actions <-> AWS OIDC trust for the
# Arquantix repository. Provisions:
#   1. The OpenID Connect provider for token.actions.githubusercontent.com
#      (one shared resource per AWS account; safe if it already exists).
#   2. An IAM role usable by GitHub Actions runs to assume short-lived
#      credentials, scoped to the repo set in $GITHUB_OWNER/$GITHUB_REPO.
#
# Required AWS permissions to run this script (one-time admin operation):
#   iam:CreateOpenIDConnectProvider, iam:GetOpenIDConnectProvider,
#   iam:CreateRole, iam:GetRole, iam:UpdateAssumeRolePolicy,
#   iam:PutRolePolicy, iam:AttachRolePolicy
#
# Usage:
#   AWS_ACCOUNT_ID=411714852748 \
#   AWS_REGION=us-east-1 \
#   GITHUB_OWNER=geniusga-vancelian \
#   GITHUB_REPO=vancelian-app \
#   ROLE_NAME=arquantix-github-actions-deployer \
#   ./scripts/aws/github-oidc/setup.sh
#
# Output: prints the role ARN to copy into the GitHub repo secret AWS_ROLE_ARN.
# ============================================================================
set -euo pipefail

# ---- Inputs (with sane defaults for this project) -------------------------
: "${AWS_ACCOUNT_ID:=411714852748}"
: "${AWS_REGION:=us-east-1}"
: "${GITHUB_OWNER:=geniusga-vancelian}"
: "${GITHUB_REPO:=vancelian-app}"
: "${ROLE_NAME:=arquantix-github-actions-deployer}"
: "${POLICY_NAME:=arquantix-github-actions-deployer-policy}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRUST_TEMPLATE="${SCRIPT_DIR}/trust-policy.json.template"
PERMS_TEMPLATE="${SCRIPT_DIR}/permissions-policy.json.template"

# ---- Sanity checks --------------------------------------------------------
command -v aws >/dev/null || { echo "ERROR: aws CLI is required" >&2; exit 1; }
command -v jq  >/dev/null || { echo "ERROR: jq is required"      >&2; exit 1; }
[[ -f "$TRUST_TEMPLATE" ]] || { echo "ERROR: missing $TRUST_TEMPLATE" >&2; exit 1; }
[[ -f "$PERMS_TEMPLATE" ]] || { echo "ERROR: missing $PERMS_TEMPLATE" >&2; exit 1; }

# Whoami sanity (catches "InvalidClientTokenId" early with a friendlier msg)
CURRENT_ACCOUNT="$(aws sts get-caller-identity --query Account --output text 2>&1 || true)"
if [[ "$CURRENT_ACCOUNT" != "$AWS_ACCOUNT_ID" ]]; then
  echo "ERROR: aws CLI not pointing at expected account."        >&2
  echo "  expected: $AWS_ACCOUNT_ID"                              >&2
  echo "  got:      $CURRENT_ACCOUNT"                             >&2
  echo "  Run 'aws configure' first or export AWS_PROFILE."       >&2
  exit 2
fi

echo "==> AWS account ${AWS_ACCOUNT_ID} (region ${AWS_REGION})"
echo "==> Repo scope:  ${GITHUB_OWNER}/${GITHUB_REPO}"
echo "==> Role name:   ${ROLE_NAME}"
echo

# ---- 1. OIDC provider (idempotent) ----------------------------------------
OIDC_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"

if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$OIDC_ARN" >/dev/null 2>&1; then
  echo "[1/3] OIDC provider already exists: $OIDC_ARN"
else
  echo "[1/3] Creating OIDC provider..."
  aws iam create-open-id-connect-provider \
    --url "https://token.actions.githubusercontent.com" \
    --client-id-list "sts.amazonaws.com" \
    --thumbprint-list "ffffffffffffffffffffffffffffffffffffffff" >/dev/null
  echo "      Created: $OIDC_ARN"
fi

# ---- 2. Render policy documents -------------------------------------------
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

sed \
  -e "s|__AWS_ACCOUNT_ID__|${AWS_ACCOUNT_ID}|g" \
  -e "s|__GITHUB_OWNER__|${GITHUB_OWNER}|g" \
  -e "s|__GITHUB_REPO__|${GITHUB_REPO}|g" \
  "$TRUST_TEMPLATE" > "${TMP_DIR}/trust.json"

sed \
  -e "s|__AWS_ACCOUNT_ID__|${AWS_ACCOUNT_ID}|g" \
  -e "s|__AWS_REGION__|${AWS_REGION}|g" \
  "$PERMS_TEMPLATE" > "${TMP_DIR}/perms.json"

jq . "${TMP_DIR}/trust.json" >/dev/null
jq . "${TMP_DIR}/perms.json" >/dev/null

# ---- 3. IAM role + inline policy (idempotent) -----------------------------
if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  echo "[2/3] Role already exists: $ROLE_NAME -> updating trust policy"
  aws iam update-assume-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-document "file://${TMP_DIR}/trust.json"
else
  echo "[2/3] Creating role: $ROLE_NAME"
  aws iam create-role \
    --role-name "$ROLE_NAME" \
    --description "GitHub Actions OIDC role for ${GITHUB_OWNER}/${GITHUB_REPO} deploys" \
    --assume-role-policy-document "file://${TMP_DIR}/trust.json" \
    --max-session-duration 3600 >/dev/null
fi

echo "[3/3] Putting inline policy: $POLICY_NAME"
aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "$POLICY_NAME" \
  --policy-document "file://${TMP_DIR}/perms.json"

ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"

# ---- Done -----------------------------------------------------------------
cat <<EOM

============================================================================
Done. Setup is idempotent — you can re-run this script safely.

  Role ARN: ${ROLE_ARN}

Next step (one-time):
  Add this ARN as a GitHub repo secret named AWS_ROLE_ARN.

  Via web:
    https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/settings/secrets/actions/new
    Name:  AWS_ROLE_ARN
    Value: ${ROLE_ARN}

  Via gh CLI (after 'gh auth login'):
    gh secret set AWS_ROLE_ARN --repo ${GITHUB_OWNER}/${GITHUB_REPO} --body "${ROLE_ARN}"

After that, push to main or trigger a workflow_dispatch — the deploy workflows
will exchange the GitHub OIDC token for short-lived AWS credentials, no static
access keys needed.
============================================================================
EOM
