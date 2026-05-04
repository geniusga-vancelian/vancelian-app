#!/usr/bin/env bash
# Affiche l'état actuel du mode maintenance Arquantix.
#
# Usage : AWS_PROFILE=arquantix-admin ./maintenance-status.sh

set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
SERVICE="${ECS_SERVICE:-arquantix-maintenance}"
ALB_NAME="${ALB_NAME:-arquantix-alb}"
MAINT_TG_NAME="${MAINT_TG_NAME:-arquantix-maintenance-tg}"
WEB_TG_NAME="${WEB_TG_NAME:-arquantix-web-tg}"

ALB_ARN=$(aws elbv2 describe-load-balancers --region "$REGION" --names "$ALB_NAME" \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)
LISTENER_443=$(aws elbv2 describe-listeners --region "$REGION" --load-balancer-arn "$ALB_ARN" \
  --query 'Listeners[?Port==`443`].ListenerArn | [0]' --output text)

DEFAULT_TG=$(aws elbv2 describe-listeners --region "$REGION" --listener-arns "$LISTENER_443" \
  --query 'Listeners[0].DefaultActions[0].TargetGroupArn' --output text)

MAINT_TG_ARN=$(aws elbv2 describe-target-groups --region "$REGION" --names "$MAINT_TG_NAME" \
  --query 'TargetGroups[0].TargetGroupArn' --output text)
WEB_TG_ARN=$(aws elbv2 describe-target-groups --region "$REGION" --names "$WEB_TG_NAME" \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

if [ "$DEFAULT_TG" = "$MAINT_TG_ARN" ]; then
  STATE="🚧 MAINTENANCE ON"
elif [ "$DEFAULT_TG" = "$WEB_TG_ARN" ]; then
  STATE="✅ NORMAL (web)"
else
  STATE="⚠️  UNKNOWN ($DEFAULT_TG)"
fi

echo "Mode actuel              : $STATE"
echo "Default action 443       : $(echo "$DEFAULT_TG" | sed 's|.*/targetgroup/||')"
echo ""

# État service maintenance.
SVC_INFO=$(aws ecs describe-services --region "$REGION" --cluster "$CLUSTER" --services "$SERVICE" \
  --query 'services[0].{Desired:desiredCount,Running:runningCount,Pending:pendingCount,TaskDef:taskDefinition}' \
  --output json)
echo "Service $SERVICE :"
echo "$SVC_INFO" | jq -r '"  Desired: \(.Desired) | Running: \(.Running) | Pending: \(.Pending) | TD: \(.TaskDef)"'

# Health.
HEALTH=$(aws elbv2 describe-target-health --region "$REGION" --target-group-arn "$MAINT_TG_ARN" \
  --query 'TargetHealthDescriptions[].{IP:Target.Id,Health:TargetHealth.State}' --output json)
echo "Targets maintenance      : $HEALTH"
echo ""

# Dernier message custom (si défini).
TD_INFO=$(aws ecs describe-task-definition --region "$REGION" --task-definition "$SERVICE" \
  --query 'taskDefinition.containerDefinitions[0].environment[?starts_with(name, `MAINT_`)]' --output json)
echo "Variables MAINT_* sur la task def courante :"
echo "$TD_INFO" | jq -r '.[] | "  \(.name)=\(.value)"'
