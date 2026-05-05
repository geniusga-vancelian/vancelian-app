#!/usr/bin/env bash
# ============================================================================
# scripts/aws/github-oidc/inventory.sh
#
# Read-only inventory of the AWS resources the Arquantix GitHub deploy
# workflows expect (ECR repos, ECS cluster + services, task definitions,
# common IAM roles). No mutation: safe to run anytime to confirm the
# infrastructure is in the expected shape after the account was reactivated.
#
# Usage:
#   AWS_ACCOUNT_ID=411714852748 AWS_REGION=us-east-1 \
#     ./scripts/aws/github-oidc/inventory.sh
# ============================================================================
set -euo pipefail

: "${AWS_ACCOUNT_ID:=411714852748}"
: "${AWS_REGION:=us-east-1}"
: "${ECS_CLUSTER:=arquantix-cluster}"

ECR_REPOS=(arquantix-web arquantix-api arquantix-coming-soon)
ECS_SERVICES=(arquantix-coming-soon arquantix-web arquantix-api)

# Roles that the workflows reference indirectly (PassRole) or that ECS uses.
EXPECTED_ROLES=(ecsTaskExecutionRole arquantix-coming-soon-task-role)

command -v aws >/dev/null || { echo "ERROR: aws CLI required" >&2; exit 1; }

# ---- Sanity: caller identity ----------------------------------------------
CURRENT_ACCOUNT="$(aws sts get-caller-identity --query Account --output text 2>&1 || true)"
echo "==> aws CLI account: ${CURRENT_ACCOUNT}"
echo "==> expected:        ${AWS_ACCOUNT_ID}"
echo "==> region:          ${AWS_REGION}"
echo
[[ "$CURRENT_ACCOUNT" == "$AWS_ACCOUNT_ID" ]] || {
  echo "WARNING: aws CLI is not pointing at the expected account."
  echo "         Continuing read-only checks anyway (some may fail)."
  echo
}

ok()   { printf "  [OK]   %s\n" "$*"; }
miss() { printf "  [MISS] %s\n" "$*"; }
err()  { printf "  [ERR]  %s\n" "$*"; }

# ---- ECR repositories ------------------------------------------------------
echo "ECR repositories (region ${AWS_REGION}):"
for repo in "${ECR_REPOS[@]}"; do
  if aws ecr describe-repositories --region "$AWS_REGION" --repository-names "$repo" >/dev/null 2>&1; then
    URI=$(aws ecr describe-repositories --region "$AWS_REGION" --repository-names "$repo" --query "repositories[0].repositoryUri" --output text)
    ok "$repo  (${URI})"
  else
    miss "$repo  (run: aws ecr create-repository --repository-name $repo --region $AWS_REGION)"
  fi
done
echo

# ---- ECS cluster -----------------------------------------------------------
echo "ECS cluster:"
CLUSTER_STATUS=$(aws ecs describe-clusters --clusters "$ECS_CLUSTER" --region "$AWS_REGION" --query "clusters[0].status" --output text 2>/dev/null || echo "ABSENT")
if [[ "$CLUSTER_STATUS" == "ACTIVE" ]]; then
  ok "$ECS_CLUSTER (status=ACTIVE)"
elif [[ "$CLUSTER_STATUS" == "ABSENT" ]]; then
  miss "$ECS_CLUSTER (no such cluster in $AWS_REGION)"
else
  err "$ECS_CLUSTER (status=$CLUSTER_STATUS)"
fi
echo

# ---- ECS services in that cluster -----------------------------------------
echo "ECS services in $ECS_CLUSTER:"
for svc in "${ECS_SERVICES[@]}"; do
  STATUS=$(aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$svc" --region "$AWS_REGION" --query "services[0].status" --output text 2>/dev/null || echo "ABSENT")
  TASKDEF=$(aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$svc" --region "$AWS_REGION" --query "services[0].taskDefinition" --output text 2>/dev/null || echo "")
  case "$STATUS" in
    ACTIVE)   ok   "$svc  (taskDef=${TASKDEF##*/})" ;;
    DRAINING) err  "$svc  (DRAINING — taskDef=${TASKDEF##*/})" ;;
    ABSENT)   miss "$svc  (service does not exist on cluster $ECS_CLUSTER)" ;;
    *)        err  "$svc  (status=$STATUS)" ;;
  esac
done
echo

# ---- IAM roles referenced by the deploy flow ------------------------------
echo "IAM roles (expected by the deploy workflows):"
for role in "${EXPECTED_ROLES[@]}"; do
  if aws iam get-role --role-name "$role" >/dev/null 2>&1; then
    ok "$role"
  else
    miss "$role"
  fi
done
echo

# ---- OIDC provider + GitHub Actions role ----------------------------------
echo "GitHub Actions OIDC integration:"
OIDC_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$OIDC_ARN" >/dev/null 2>&1; then
  ok "OIDC provider $OIDC_ARN"
else
  miss "OIDC provider not yet created (run scripts/aws/github-oidc/setup.sh)"
fi

DEPLOYER_ROLE="arquantix-github-actions-deployer"
if aws iam get-role --role-name "$DEPLOYER_ROLE" >/dev/null 2>&1; then
  ok "Deployer role $DEPLOYER_ROLE"
  ARN=$(aws iam get-role --role-name "$DEPLOYER_ROLE" --query "Role.Arn" --output text)
  printf "         ARN: %s\n" "$ARN"
else
  miss "Deployer role not yet created (run scripts/aws/github-oidc/setup.sh)"
fi

echo
echo "Done."
