#!/bin/bash
# audit-aws-infrastructure.sh
# Script pour auditer l'infrastructure AWS (ECR, ECS, ALB)

set -euo pipefail

REGION="me-central-1"

echo "=== AUDIT AWS INFRASTRUCTURE ==="
echo "Région: $REGION"
echo "Date: $(date)"
echo ""

echo "=== 1. ECR REPOSITORIES ==="
aws ecr describe-repositories \
  --region "$REGION" \
  --query 'repositories[*].{name:repositoryName,uri:repositoryUri,created:createdAt}' \
  --output table || echo "⚠️  Erreur: Vérifiez les permissions ECR"

echo ""
echo "=== 2. ECS CLUSTERS ==="
aws ecs list-clusters \
  --region "$REGION" \
  --output json 2>/dev/null | jq -r '.clusterArns[]' 2>/dev/null | while read -r cluster_arn; do
  if [ -n "$cluster_arn" ]; then
    aws ecs describe-clusters \
      --region "$REGION" \
      --clusters "$cluster_arn" \
      --query 'clusters[0].{name:clusterName,status:status}' \
      --output table || echo "⚠️  Erreur: Vérifiez les permissions ECS"
  fi
done || echo "⚠️  Erreur: Vérifiez les permissions ECS"

echo ""
echo "=== 3. ECS SERVICES - DEV CLUSTER ==="
aws ecs list-services \
  --region "$REGION" \
  --cluster vancelian-dev-api-cluster \
  --output json 2>/dev/null | jq -r '.serviceArns[]' 2>/dev/null | while read -r service_arn; do
  if [ -n "$service_arn" ]; then
    service_name=$(echo "$service_arn" | awk -F'/' '{print $NF}')
    aws ecs describe-services \
      --region "$REGION" \
      --cluster vancelian-dev-api-cluster \
      --services "$service_name" \
      --query 'services[0].{name:serviceName,status:status,desired:desiredCount,running:runningCount,taskDef:taskDefinition}' \
      --output table || echo "⚠️  Erreur: Vérifiez les permissions ECS"
  fi
done || echo "⚠️  Erreur: Vérifiez les permissions ECS ou le cluster n'existe pas"

echo ""
echo "=== 4. ALB LOAD BALANCERS ==="
aws elbv2 describe-load-balancers \
  --region "$REGION" \
  --query 'LoadBalancers[*].{name:LoadBalancerName,dns:DNSName,arn:LoadBalancerArn}' \
  --output table || echo "⚠️  Erreur: Vérifiez les permissions ELB"

echo ""
echo "=== 5. TARGET GROUPS ==="
aws elbv2 describe-target-groups \
  --region "$REGION" \
  --query 'TargetGroups[*].{name:TargetGroupName,port:Port,type:TargetType,protocol:Protocol,health:HealthCheckPath}' \
  --output table || echo "⚠️  Erreur: Vérifiez les permissions ELB"

echo ""
echo "=== 6. TASK DEFINITIONS - Ganopa Bot ==="
latest_taskdef=$(aws ecs list-task-definitions \
  --region "$REGION" \
  --family-prefix ganopa-bot \
  --query 'taskDefinitionArns[-1]' \
  --output text 2>/dev/null || echo "")
if [ -n "$latest_taskdef" ] && [ "$latest_taskdef" != "None" ]; then
  aws ecs describe-task-definition \
    --region "$REGION" \
    --task-definition "$latest_taskdef" \
    --query 'taskDefinition.{family:family,revision:revision,image:containerDefinitions[0].image,cpu:cpu,memory:memory}' \
    --output json | jq || echo "⚠️  Erreur: Vérifiez les permissions ECS"
else
  echo "⚠️  Aucune Task Definition trouvée pour ganopa-bot"
fi

echo ""
echo "=== AUDIT TERMINÉ ==="


