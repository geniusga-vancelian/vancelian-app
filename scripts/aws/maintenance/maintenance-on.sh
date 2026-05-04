#!/usr/bin/env bash
# Active le mode maintenance Arquantix : bascule la default action du listener HTTPS de l'ALB
# vers le target group `arquantix-maintenance-tg` (page nginx 503).
#
# Conserve intacts :
#   - Rule prio 50 (Host=arquantix.com Path=/admin*, /api/admin/*, /api/site/media/*, /_next/*) → web TG
#   - Rule prio 100 (Host=api.arquantix.com)                                                   → api TG
#
# Donc /admin et l'API restent accessibles. Seules les pages publiques sont remplacées.
#
# Usage : AWS_PROFILE=arquantix-admin ./maintenance-on.sh
#         AWS_PROFILE=arquantix-admin ./maintenance-on.sh --title "Mise à jour" --subtitle "..." --eta "1h"

set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
SERVICE="${ECS_SERVICE:-arquantix-maintenance}"
ALB_NAME="${ALB_NAME:-arquantix-alb}"
WEB_TG_NAME="${WEB_TG_NAME:-arquantix-web-tg}"
MAINT_TG_NAME="${MAINT_TG_NAME:-arquantix-maintenance-tg}"

TITLE=""
SUBTITLE=""
ETA=""
while [ $# -gt 0 ]; do
  case "$1" in
    --title) TITLE="$2"; shift 2 ;;
    --subtitle) SUBTITLE="$2"; shift 2 ;;
    --eta) ETA="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,16p' "$0"
      exit 0
      ;;
    *) echo "[maintenance-on] arg inconnu : $1" >&2; exit 1 ;;
  esac
done

echo "[maintenance-on] Région: $REGION | ALB: $ALB_NAME"

# Optionnel: customiser le message via env override de la task def maintenance.
if [ -n "$TITLE$SUBTITLE$ETA" ]; then
  echo "[maintenance-on] Customisation message → register new revision + force-new-deployment"
  CURRENT_TD=$(aws ecs describe-services --region "$REGION" --cluster "$CLUSTER" --services "$SERVICE" \
    --query 'services[0].taskDefinition' --output text)
  aws ecs describe-task-definition --region "$REGION" --task-definition "$CURRENT_TD" \
    --query 'taskDefinition' --output json > /tmp/_maint-td.json
  jq --arg t "$TITLE" --arg s "$SUBTITLE" --arg e "$ETA" '
    .containerDefinitions[0].environment |= (
      map(
        if .name=="MAINT_TITLE" and ($t|length>0) then .value=$t
        elif .name=="MAINT_SUBTITLE" and ($s|length>0) then .value=$s
        elif .name=="MAINT_ETA" then .value=$e
        else . end
      )
    )
    | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy)
  ' /tmp/_maint-td.json > /tmp/_maint-td.new.json
  NEW_TD=$(aws ecs register-task-definition --region "$REGION" --cli-input-json file:///tmp/_maint-td.new.json \
    --query 'taskDefinition.taskDefinitionArn' --output text)
  echo "[maintenance-on] New TD: $NEW_TD"
  aws ecs update-service --region "$REGION" --cluster "$CLUSTER" --service "$SERVICE" \
    --task-definition "$NEW_TD" --force-new-deployment >/dev/null
  rm -f /tmp/_maint-td.json /tmp/_maint-td.new.json
fi

# S'assurer que le service tourne (au cas où il aurait été scale à 0).
DESIRED=$(aws ecs describe-services --region "$REGION" --cluster "$CLUSTER" --services "$SERVICE" \
  --query 'services[0].desiredCount' --output text)
if [ "$DESIRED" -lt 1 ]; then
  echo "[maintenance-on] Service à $DESIRED, scale à 1…"
  aws ecs update-service --region "$REGION" --cluster "$CLUSTER" --service "$SERVICE" \
    --desired-count 1 >/dev/null
  echo "[maintenance-on] Wait stabilité (~60s)…"
  aws ecs wait services-stable --region "$REGION" --cluster "$CLUSTER" --services "$SERVICE"
fi

# Récupère ARNs.
ALB_ARN=$(aws elbv2 describe-load-balancers --region "$REGION" --names "$ALB_NAME" \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)
LISTENER_443=$(aws elbv2 describe-listeners --region "$REGION" --load-balancer-arn "$ALB_ARN" \
  --query 'Listeners[?Port==`443`].ListenerArn | [0]' --output text)
MAINT_TG_ARN=$(aws elbv2 describe-target-groups --region "$REGION" --names "$MAINT_TG_NAME" \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

# Bascule default action 443 → maintenance TG.
echo "[maintenance-on] Modification default action listener 443 → $MAINT_TG_NAME"
aws elbv2 modify-listener --region "$REGION" --listener-arn "$LISTENER_443" \
  --default-actions "Type=forward,TargetGroupArn=$MAINT_TG_ARN" >/dev/null

echo "[maintenance-on] ✅ Mode maintenance activé."
echo "[maintenance-on]    /admin et /api/admin/* restent accessibles via la rule prio 50."
echo "[maintenance-on]    api.arquantix.com reste accessible via la rule prio 100."
echo "[maintenance-on] Test : curl -sI https://arquantix.com/   → attendu 503"
