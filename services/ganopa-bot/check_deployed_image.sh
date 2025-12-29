#!/bin/bash
# Script to verify which Docker image is deployed in ECS

set -euo pipefail

AWS_REGION="me-central-1"
CLUSTER="vancelian-dev-api-cluster"
SERVICE="ganopa-dev-bot-svc"

echo "🔍 Checking deployed image in ECS..."
echo ""

# Get current Git SHA
CURRENT_SHA=$(git rev-parse HEAD)
echo "📌 Current Git SHA: ${CURRENT_SHA}"
echo ""

# Get deployed image from ECS service
echo "🔍 Fetching ECS service information..."
SERVICE_INFO=$(aws ecs describe-services \
  --region "${AWS_REGION}" \
  --cluster "${CLUSTER}" \
  --services "${SERVICE}" \
  --query 'services[0]' \
  --output json)

TASKDEF_ARN=$(echo "${SERVICE_INFO}" | jq -r '.taskDefinition')
echo "📋 Task Definition: ${TASKDEF_ARN}"
echo ""

# Get task definition details
echo "🔍 Fetching task definition..."
TASKDEF=$(aws ecs describe-task-definition \
  --region "${AWS_REGION}" \
  --task-definition "${TASKDEF_ARN}" \
  --query 'taskDefinition' \
  --output json)

# Extract image URI
IMAGE_URI=$(echo "${TASKDEF}" | jq -r '.containerDefinitions[0].image')
echo "🐳 Deployed Image URI: ${IMAGE_URI}"
echo ""

# Extract image tag
IMAGE_TAG=$(echo "${IMAGE_URI}" | cut -d: -f2)
echo "🏷️  Image Tag: ${IMAGE_TAG}"
echo ""

# Compare
if [ "${IMAGE_TAG}" = "${CURRENT_SHA}" ]; then
  echo "✅ Image tag matches current Git SHA"
else
  echo "❌ Image tag does NOT match current Git SHA"
  echo "   Expected: ${CURRENT_SHA}"
  echo "   Found:    ${IMAGE_TAG}"
  echo ""
  echo "⚠️  The deployed image is from a different commit!"
fi

echo ""
echo "📊 Summary:"
echo "   Current Git SHA: ${CURRENT_SHA}"
echo "   Deployed Image:  ${IMAGE_URI}"
echo "   Match:           $([ "${IMAGE_TAG}" = "${CURRENT_SHA}" ] && echo "✅ YES" || echo "❌ NO")"

