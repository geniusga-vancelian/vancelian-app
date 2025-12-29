#!/bin/bash
set -euo pipefail

# Script pour forcer un nouveau déploiement du service ECS Ganopa Bot

AWS_REGION="me-central-1"
CLUSTER="vancelian-dev-api-cluster"
SERVICE="ganopa-dev-bot-svc"

echo "🚀 Forcing new deployment of ECS service..."
echo "   Cluster: $CLUSTER"
echo "   Service: $SERVICE"
echo "   Region: $AWS_REGION"
echo ""

# Force new deployment
aws ecs update-service \
  --region "$AWS_REGION" \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --force-new-deployment \
  --output json | jq '{serviceName, status, taskDefinition, deployments: .service.deployments[0]}'

echo ""
echo "✅ Deployment forced. Waiting for service to stabilize..."
echo ""

# Wait a bit and check status
sleep 10

aws ecs describe-services \
  --region "$AWS_REGION" \
  --cluster "$CLUSTER" \
  --services "$SERVICE" \
  --query "services[0].{status:status,desiredCount:desiredCount,runningCount:runningCount,pendingCount:pendingCount,deployments:deployments[0].{status:status,rolloutState:rolloutState,taskDefinition:taskDefinition}}" \
  --output json | jq .

echo ""
echo "📊 Service status retrieved."
echo ""
echo "💡 To monitor deployment progress:"
echo "   aws ecs describe-services --region $AWS_REGION --cluster $CLUSTER --services $SERVICE --query 'services[0].deployments' --output json | jq ."
echo ""
echo "💡 To check logs:"
echo "   aws logs tail /ecs/ganopa-dev-bot-task --region $AWS_REGION --since 10m --format short"

