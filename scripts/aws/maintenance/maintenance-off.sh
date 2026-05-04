#!/usr/bin/env bash
# Désactive le mode maintenance Arquantix : restaure la default action du listener HTTPS de l'ALB
# vers le target group `arquantix-web-tg` (Next.js production).
#
# Usage : AWS_PROFILE=arquantix-admin ./maintenance-off.sh
#         AWS_PROFILE=arquantix-admin ./maintenance-off.sh --scale-down
#
# --scale-down : scale aussi le service maintenance à desiredCount=0 pour économiser
#                (~7€/mois). Au prochain `maintenance-on`, le scale remontera à 1
#                automatiquement (~60s pour cold-start).

set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
SERVICE="${ECS_SERVICE:-arquantix-maintenance}"
ALB_NAME="${ALB_NAME:-arquantix-alb}"
WEB_TG_NAME="${WEB_TG_NAME:-arquantix-web-tg}"

SCALE_DOWN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --scale-down) SCALE_DOWN=1; shift ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "[maintenance-off] arg inconnu : $1" >&2; exit 1 ;;
  esac
done

echo "[maintenance-off] Région: $REGION | ALB: $ALB_NAME"

ALB_ARN=$(aws elbv2 describe-load-balancers --region "$REGION" --names "$ALB_NAME" \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)
LISTENER_443=$(aws elbv2 describe-listeners --region "$REGION" --load-balancer-arn "$ALB_ARN" \
  --query 'Listeners[?Port==`443`].ListenerArn | [0]' --output text)
WEB_TG_ARN=$(aws elbv2 describe-target-groups --region "$REGION" --names "$WEB_TG_NAME" \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

# Restaure default action 443 → web TG.
echo "[maintenance-off] Restauration default action listener 443 → $WEB_TG_NAME"
aws elbv2 modify-listener --region "$REGION" --listener-arn "$LISTENER_443" \
  --default-actions "Type=forward,TargetGroupArn=$WEB_TG_ARN" >/dev/null

if [ "$SCALE_DOWN" = "1" ]; then
  echo "[maintenance-off] Scale-down service $SERVICE à 0 (économie ~7€/mois)"
  aws ecs update-service --region "$REGION" --cluster "$CLUSTER" --service "$SERVICE" \
    --desired-count 0 >/dev/null
fi

echo "[maintenance-off] ✅ Mode maintenance désactivé."
echo "[maintenance-off] Test : curl -sI https://arquantix.com/   → attendu 200/307 (page normale)"
