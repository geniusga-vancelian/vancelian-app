#!/bin/bash
# Script to verify code in Docker image

set -euo pipefail

IMAGE_URI="411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:30c4b5c7dd4b716e0600ef69a73a986b5eaf7018"

echo "🔍 Checking code in Docker image: ${IMAGE_URI}"
echo ""

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region me-central-1 | \
  docker login --username AWS --password-stdin \
  411714852748.dkr.ecr.me-central-1.amazonaws.com

echo ""
echo "📥 Pulling Docker image..."
docker pull "${IMAGE_URI}"

echo ""
echo "🔍 Checking for '✅ Reçu' in app/main.py..."
if docker run --rm "${IMAGE_URI}" grep -n "✅ Reçu" app/main.py 2>/dev/null; then
  echo ""
  echo "❌ PROBLEM FOUND: Old echo code is present in the image!"
  echo "   The image contains '✅ Reçu' which should not be there."
  echo ""
  echo "🔧 Solution: Rebuild the Docker image with the latest commit."
else
  echo ""
  echo "✅ No '✅ Reçu' found in the image."
  echo "   The code appears to be correct."
fi

echo ""
echo "🔍 Checking for 'openai_request_start' in app/main.py..."
if docker run --rm "${IMAGE_URI}" grep -n "openai_request_start" app/main.py 2>/dev/null; then
  echo ""
  echo "✅ 'openai_request_start' found - new code is present."
else
  echo ""
  echo "❌ 'openai_request_start' NOT found - old code is present."
fi

echo ""
echo "🔍 Listing Python files in app/..."
docker run --rm "${IMAGE_URI}" ls -la app/

echo ""
echo "🔍 Checking main.py structure..."
docker run --rm "${IMAGE_URI}" grep -n "def process_telegram_update" app/main.py || echo "Function not found"

echo ""
echo "✅ Verification complete."


