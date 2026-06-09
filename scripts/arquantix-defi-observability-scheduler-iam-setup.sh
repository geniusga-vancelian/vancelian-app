#!/usr/bin/env bash
# Crée le rôle IAM EventBridge Scheduler → ECS RunTask (tick defi_observability).
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT="${AWS_ACCOUNT:-411714852748}"
ECS_CLUSTER="${ECS_CLUSTER:-arquantix-cluster}"
ECS_SERVICE="${ECS_SERVICE:-arquantix-api}"
ROLE_NAME="${DEFI_ECS_SCHEDULER_ROLE_NAME:-arquantix-defi-ecs-scheduler}"

TASK_DEF=$(aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE" \
  --region "$AWS_REGION" --query 'services[0].taskDefinition' --output text)
EXEC_ROLE=$(aws ecs describe-task-definition --task-definition "$TASK_DEF" --region "$AWS_REGION" \
  --query 'taskDefinition.executionRoleArn' --output text)
TASK_ROLE=$(aws ecs describe-task-definition --task-definition "$TASK_DEF" --region "$AWS_REGION" \
  --query 'taskDefinition.taskRoleArn' --output text)
CLUSTER_ARN="arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT}:cluster/${ECS_CLUSTER}"

TRUST_POLICY='{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "scheduler.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}'

PERMISSIONS_POLICY=$(EXEC_ROLE="$EXEC_ROLE" TASK_ROLE="$TASK_ROLE" CLUSTER_ARN="$CLUSTER_ARN" python3 - <<'PY'
import json, os

pass_roles = [os.environ["EXEC_ROLE"]]
task_role = (os.environ.get("TASK_ROLE") or "").strip()
if task_role and task_role.lower() not in ("none", "null"):
    pass_roles.append(task_role)

print(json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["ecs:RunTask"],
            "Resource": "*",
            "Condition": {
                "ArnEquals": {
                    "ecs:cluster": os.environ["CLUSTER_ARN"],
                }
            },
        },
        {
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": pass_roles,
        },
    ],
}))
PY
)

echo "==> IAM role ${ROLE_NAME}"
echo "  cluster: ${CLUSTER_ARN}"
echo "  exec role: ${EXEC_ROLE}"
echo "  task role: ${TASK_ROLE}"

if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  aws iam update-assume-role-policy --role-name "$ROLE_NAME" --policy-document "$TRUST_POLICY"
  echo "OK trust policy updated"
else
  aws iam create-role --role-name "$ROLE_NAME" --assume-role-policy-document "$TRUST_POLICY"
  echo "OK role created"
fi

aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "${ROLE_NAME}-ecs-run-task" \
  --policy-document "$PERMISSIONS_POLICY"

echo "OK inline policy ${ROLE_NAME}-ecs-run-task"
echo "ARN: arn:aws:iam::${AWS_ACCOUNT}:role/${ROLE_NAME}"
