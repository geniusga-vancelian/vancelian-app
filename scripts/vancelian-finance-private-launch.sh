#!/usr/bin/env bash
# Infra privée Vancelian : app.* + console.* → Next.js, apex/www → coming-soon.
# Usage : ./scripts/vancelian-finance-private-launch.sh
# Env optionnel : VANCELIAN_WAF_ALLOW_CIDRS="91.73.77.140/32,1.2.3.4/32"
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT="${AWS_ACCOUNT:-411714852748}"
VPC_ID="${VANCELIAN_VPC_ID:-vpc-06c579f5a937d563b}"
ZONE_ID="${VANCELIAN_ZONE_ID:-Z091663116M960F99DPZB}"
ALB_ARN="${VANCELIAN_ALB_ARN:-arn:aws:elasticloadbalancing:us-east-1:411714852748:loadbalancer/app/vancelian-alb/1536aa6259b51090}"
HTTPS_LISTENER="${VANCELIAN_HTTPS_LISTENER:-arn:aws:elasticloadbalancing:us-east-1:411714852748:listener/app/vancelian-alb/1536aa6259b51090/704b34261fab9968}"
COMING_SOON_TG="${VANCELIAN_COMING_SOON_TG:-arn:aws:elasticloadbalancing:us-east-1:411714852748:targetgroup/vancelian-web-tg/70ba52bfa4001c5e}"
ECS_CLUSTER="${VANCELIAN_ECS_CLUSTER:-arquantix-cluster}"
ECS_SG="${VANCELIAN_ECS_SG:-sg-064dc832914f8e05f}"
ECS_SUBNET="${VANCELIAN_ECS_SUBNET:-subnet-03581e86634f354dd}"
ECR_REPO="vancelian-next"
ECR_URI="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"
ECS_SERVICE="vancelian-next"
TASK_FAMILY="vancelian-next"
WAF_ALLOW_CIDRS="${VANCELIAN_WAF_ALLOW_CIDRS:-91.73.77.140/32,89.247.164.87/32,90.14.87.113/32}"

echo "==> ECR repository ${ECR_REPO}"
if ! aws ecr describe-repositories --repository-names "$ECR_REPO" --region "$AWS_REGION" >/dev/null 2>&1; then
  aws ecr create-repository --repository-name "$ECR_REPO" --region "$AWS_REGION" >/dev/null
  echo "  created"
else
  echo "  exists"
fi

echo "==> CloudWatch log group /ecs/${ECS_SERVICE}"
aws logs create-log-group --log-group-name "/ecs/${ECS_SERVICE}" --region "$AWS_REGION" 2>/dev/null || true

echo "==> Target group vancelian-next-tg (:3000, health /health)"
NEXT_TG=$(aws elbv2 describe-target-groups --names vancelian-next-tg --region "$AWS_REGION" --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null || true)
if [[ -z "$NEXT_TG" || "$NEXT_TG" == "None" ]]; then
  NEXT_TG=$(aws elbv2 create-target-group \
    --name vancelian-next-tg \
    --protocol HTTP \
    --port 3000 \
    --vpc-id "$VPC_ID" \
    --target-type ip \
    --health-check-path /health \
    --health-check-interval-seconds 30 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --matcher HttpCode=200-399 \
    --region "$AWS_REGION" \
    --query 'TargetGroups[0].TargetGroupArn' --output text)
  echo "  created $NEXT_TG"
else
  echo "  exists $NEXT_TG"
fi

echo "==> ALB listener rules (app + console → Next, default → coming-soon)"
while IFS='|' read -r P H; do
  EXISTING=$(aws elbv2 describe-rules --listener-arn "$HTTPS_LISTENER" --region "$AWS_REGION" \
    --query "Rules[?Priority==\`$P\`].RuleArn | [0]" --output text 2>/dev/null || true)
  if [[ -z "$EXISTING" || "$EXISTING" == "None" ]]; then
    aws elbv2 create-rule \
      --listener-arn "$HTTPS_LISTENER" \
      --priority "$P" \
      --conditions "Field=host-header,Values=$H" \
      --actions "Type=forward,TargetGroupArn=$NEXT_TG" \
      --region "$AWS_REGION" >/dev/null
    echo "  rule priority $P → $H"
  else
    aws elbv2 modify-rule \
      --rule-arn "$EXISTING" \
      --conditions "Field=host-header,Values=$H" \
      --actions "Type=forward,TargetGroupArn=$NEXT_TG" \
      --region "$AWS_REGION" >/dev/null
    echo "  updated rule priority $P → $H"
  fi
done <<'EOF'
10|app.vancelian.finance
20|console.vancelian.finance
EOF

echo "==> Route53 app + console → ALB"
ALB_DNS=$(aws elbv2 describe-load-balancers --load-balancer-arns "$ALB_ARN" --region "$AWS_REGION" --query 'LoadBalancers[0].DNSName' --output text)
ALB_ZONE="Z35SXDOTRQ7X7K"
TMP_DNS=$(mktemp)
cat >"$TMP_DNS" <<JSON
{
  "Comment": "Vancelian private subdomains",
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "app.vancelian.finance",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "$ALB_ZONE",
          "DNSName": "$ALB_DNS",
          "EvaluateTargetHealth": false
        }
      }
    },
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "console.vancelian.finance",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "$ALB_ZONE",
          "DNSName": "$ALB_DNS",
          "EvaluateTargetHealth": false
        }
      }
    }
  ]
}
JSON
aws route53 change-resource-record-sets --hosted-zone-id "$ZONE_ID" --change-batch "file://$TMP_DNS" >/dev/null
rm -f "$TMP_DNS"
echo "  app.vancelian.finance + console.vancelian.finance → $ALB_DNS"

echo "==> WAF : app/console IP allowlist (default allow apex/www)"
WAF_NAME="vancelian-private-subdomains"
IPSET_NAME="vancelian-team-allowlist"
SCOPE="REGIONAL"

IPSET_ID=$(aws wafv2 list-ip-sets --scope "$SCOPE" --region "$AWS_REGION" \
  --query "IPSets[?Name=='$IPSET_NAME'].Id | [0]" --output text 2>/dev/null || true)
if [[ -z "$IPSET_ID" || "$IPSET_ID" == "None" ]]; then
  IPSET_OUT=$(aws wafv2 create-ip-set \
    --name "$IPSET_NAME" \
    --scope "$SCOPE" \
    --ip-address-version IPV4 \
    --addresses $(echo "$WAF_ALLOW_CIDRS" | tr ',' ' ') \
    --region "$AWS_REGION")
  IPSET_ARN=$(echo "$IPSET_OUT" | jq -r '.Summary.ARN')
  echo "  created IP set $IPSET_ARN"
else
  IPSET_ARN=$(aws wafv2 list-ip-sets --scope "$SCOPE" --region "$AWS_REGION" \
    --query "IPSets[?Name=='$IPSET_NAME'].ARN | [0]" --output text)
  LOCK=$(aws wafv2 get-ip-set --name "$IPSET_NAME" --scope "$SCOPE" --id "$IPSET_ID" --region "$AWS_REGION" --query 'LockToken' --output text)
  aws wafv2 update-ip-set \
    --name "$IPSET_NAME" \
    --scope "$SCOPE" \
    --id "$IPSET_ID" \
    --addresses $(echo "$WAF_ALLOW_CIDRS" | tr ',' ' ') \
    --lock-token "$LOCK" \
    --region "$AWS_REGION" >/dev/null
  echo "  updated IP set $IPSET_ARN"
fi

ACL_ID=$(aws wafv2 list-web-acls --scope "$SCOPE" --region "$AWS_REGION" \
  --query "WebACLs[?Name=='$WAF_NAME'].Id | [0]" --output text 2>/dev/null || true)
APP_HOST_B64=$(printf 'app.vancelian.finance' | base64 | tr -d '\n')
CONSOLE_HOST_B64=$(printf 'console.vancelian.finance' | base64 | tr -d '\n')
WAF_JSON=$(mktemp)
cat >"$WAF_JSON" <<JSON
{
  "Name": "${WAF_NAME}",
  "Scope": "${SCOPE}",
  "DefaultAction": { "Allow": {} },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "${WAF_NAME}"
  },
  "Rules": [
    {
      "Name": "BlockPrivateSubdomainsWithoutAllowlist",
      "Priority": 1,
      "Action": { "Block": {} },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "BlockPrivateSubdomainsWithoutAllowlist"
      },
      "Statement": {
        "AndStatement": {
          "Statements": [
            {
              "OrStatement": {
                "Statements": [
                  {
                    "ByteMatchStatement": {
                      "SearchString": "${APP_HOST_B64}",
                      "FieldToMatch": { "SingleHeader": { "Name": "host" } },
                      "TextTransformations": [{ "Priority": 0, "Type": "LOWERCASE" }],
                      "PositionalConstraint": "EXACTLY"
                    }
                  },
                  {
                    "ByteMatchStatement": {
                      "SearchString": "${CONSOLE_HOST_B64}",
                      "FieldToMatch": { "SingleHeader": { "Name": "host" } },
                      "TextTransformations": [{ "Priority": 0, "Type": "LOWERCASE" }],
                      "PositionalConstraint": "EXACTLY"
                    }
                  }
                ]
              }
            },
            {
              "NotStatement": {
                "Statement": {
                  "IPSetReferenceStatement": { "ARN": "${IPSET_ARN}" }
                }
              }
            }
          ]
        }
      }
    }
  ]
}
JSON
if [[ -z "$ACL_ID" || "$ACL_ID" == "None" ]]; then
  ACL_OUT=$(aws wafv2 create-web-acl --cli-input-json "file://$WAF_JSON" --region "$AWS_REGION")
  ACL_ARN=$(echo "$ACL_OUT" | jq -r '.Summary.ARN')
  echo "  created Web ACL $ACL_ARN"
else
  LOCK=$(aws wafv2 get-web-acl --name "$WAF_NAME" --scope "$SCOPE" --id "$ACL_ID" --region "$AWS_REGION" --query 'LockToken' --output text)
  jq --arg lock "$LOCK" --arg id "$ACL_ID" '. + {Id: $id, LockToken: $lock}' "$WAF_JSON" > "${WAF_JSON}.update"
  aws wafv2 update-web-acl --cli-input-json "file://${WAF_JSON}.update" --region "$AWS_REGION" >/dev/null
  ACL_ARN=$(aws wafv2 list-web-acls --scope "$SCOPE" --region "$AWS_REGION" --query "WebACLs[?Name=='$WAF_NAME'].ARN | [0]" --output text)
  echo "  updated Web ACL $ACL_ARN"
fi
rm -f "$WAF_JSON" "${WAF_JSON}.update"

for attempt in 1 2 3 4 5; do
  if aws wafv2 associate-web-acl \
    --web-acl-arn "$ACL_ARN" \
    --resource-arn "$ALB_ARN" \
    --region "$AWS_REGION" >/dev/null 2>&1; then
    echo "  WAF associé à l'ALB"
    break
  fi
  if [[ "$attempt" -eq 5 ]]; then
    echo "  WARN: association WAF/ALB échouée — réessayer: aws wafv2 associate-web-acl --web-acl-arn $ACL_ARN --resource-arn $ALB_ARN --region $AWS_REGION" >&2
  else
    sleep "$((attempt * 3))"
  fi
done

echo "==> ECS task definition ${TASK_FAMILY}"
IMAGE="${VANCELIAN_NEXT_IMAGE:-${ECR_URI}:latest}"
TASK_DEF=$(cat <<JSON
{
  "family": "${TASK_FAMILY}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::${AWS_ACCOUNT}:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::${AWS_ACCOUNT}:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "vancelian-next",
      "image": "${IMAGE}",
      "essential": true,
      "portMappings": [{ "containerPort": 3000, "protocol": "tcp" }],
      "environment": [
        { "name": "NODE_ENV", "value": "production" },
        { "name": "PORT", "value": "3000" },
        { "name": "HOSTNAME", "value": "0.0.0.0" },
        { "name": "RUN_PRISMA_MIGRATE_ON_START", "value": "0" },
        { "name": "SKIP_BFF_ANONYMOUS_ADMIN_DB_CHECK", "value": "1" },
        { "name": "APP_ENV", "value": "staging" },
        { "name": "ARQUANTIX_ENV", "value": "staging" },
        { "name": "NEXT_PUBLIC_SITE_URL", "value": "https://vancelian.finance" },
        { "name": "NEXT_PUBLIC_API_URL", "value": "https://api.arquantix.com" },
        { "name": "NEXT_PUBLIC_BACKEND_URL", "value": "https://api.arquantix.com" },
        { "name": "ADMIN_SEED_EMAIL", "value": "admin@arquantix.com" }
      ],
      "secrets": [
        { "name": "DATABASE_URL", "valueFrom": "arn:aws:secretsmanager:us-east-1:411714852748:secret:arquantix/prod/database-url-BsnHcb" },
        { "name": "JWT_SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:us-east-1:411714852748:secret:arquantix/prod/jwt-secret-key-kG2EFL" },
        { "name": "AUTH_SECRET", "valueFrom": "arn:aws:secretsmanager:us-east-1:411714852748:secret:arquantix/prod/jwt-secret-key-kG2EFL" },
        { "name": "ADMIN_PASSWORD", "valueFrom": "arn:aws:secretsmanager:us-east-1:411714852748:secret:arquantix/prod/admin-password-q7HCD4" },
        { "name": "ADMIN_SEED_PASSWORD", "valueFrom": "arn:aws:secretsmanager:us-east-1:411714852748:secret:arquantix/prod/admin-seed-password-8MBe5A" },
        { "name": "STORAGE_BUCKET_NAME", "valueFrom": "arn:aws:secretsmanager:us-east-1:411714852748:secret:arquantix/prod/storage-bucket-name-5gaiWn" },
        { "name": "STORAGE_REGION", "valueFrom": "arn:aws:secretsmanager:us-east-1:411714852748:secret:arquantix/prod/storage-region-Dcxm1c" },
        { "name": "STORAGE_ENDPOINT", "valueFrom": "arn:aws:secretsmanager:us-east-1:411714852748:secret:arquantix/prod/storage-endpoint-511hgP" },
        { "name": "STORAGE_PUBLIC_URL", "valueFrom": "arn:aws:secretsmanager:us-east-1:411714852748:secret:arquantix/prod/storage-public-url-JO9lJ4" },
        { "name": "STORAGE_ACCESS_KEY_ID", "valueFrom": "arn:aws:secretsmanager:us-east-1:411714852748:secret:arquantix/prod/storage-access-key-id-3sav5C" },
        { "name": "STORAGE_SECRET_ACCESS_KEY", "valueFrom": "arn:aws:secretsmanager:us-east-1:411714852748:secret:arquantix/prod/storage-secret-access-key-6E3lf6" }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/${ECS_SERVICE}",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "next"
        }
      }
    }
  ]
}
JSON
)
echo "$TASK_DEF" > /tmp/vancelian-next-taskdef.json
TASK_ARN=$(aws ecs register-task-definition --cli-input-json file:///tmp/vancelian-next-taskdef.json --region "$AWS_REGION" --query 'taskDefinition.taskDefinitionArn' --output text)
echo "  registered $TASK_ARN"

echo "==> ECS service ${ECS_SERVICE}"
if aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE" --region "$AWS_REGION" --query 'services[0].status' --output text 2>/dev/null | grep -q ACTIVE; then
  aws ecs update-service \
    --cluster "$ECS_CLUSTER" \
    --service "$ECS_SERVICE" \
    --task-definition "$TASK_ARN" \
    --force-new-deployment \
    --region "$AWS_REGION" >/dev/null
  echo "  updated service (force new deployment)"
else
  aws ecs create-service \
    --cluster "$ECS_CLUSTER" \
    --service-name "$ECS_SERVICE" \
    --task-definition "$TASK_ARN" \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$ECS_SUBNET],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" \
    --load-balancers "targetGroupArn=$NEXT_TG,containerName=vancelian-next,containerPort=3000" \
    --health-check-grace-period-seconds 120 \
    --region "$AWS_REGION" >/dev/null
  echo "  created service"
fi

echo ""
echo "==> Terminé."
echo "  Apex (public)     : https://vancelian.finance  → coming-soon"
echo "  Webapp (privé)    : https://app.vancelian.finance"
echo "  Console CMS       : https://console.vancelian.finance/admin/login"
echo "  WAF allowlist     : $WAF_ALLOW_CIDRS"
echo "  Image attendue    : $IMAGE"
echo ""
echo "Prochaine étape : build & push l'image Next.js puis relancer ce script ou force-new-deployment."
