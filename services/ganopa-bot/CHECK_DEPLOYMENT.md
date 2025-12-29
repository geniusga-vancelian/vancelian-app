# 🔍 Commandes de Vérification du Déploiement

## Prérequis

```bash
# Configurer AWS CLI (si pas déjà fait)
aws configure --profile default
# Ou utiliser les credentials via IAM role si sur EC2/ECS
```

---

## 1. Vérifier le Routing ALB pour /telegram/webhook

```bash
# Trouver l'ARN de l'ALB
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --region me-central-1 \
  --query 'LoadBalancers[?contains(DNSName, `maisonganopa`)].LoadBalancerArn' \
  --output text)

echo "ALB ARN: ${ALB_ARN}"

# Trouver le listener HTTPS (443)
LISTENER_ARN=$(aws elbv2 describe-listeners \
  --region me-central-1 \
  --load-balancer-arn "${ALB_ARN}" \
  --query 'Listeners[?Port==`443`].ListenerArn' \
  --output text)

echo "Listener ARN: ${LISTENER_ARN}"

# Vérifier les règles pour /telegram/webhook
aws elbv2 describe-rules \
  --region me-central-1 \
  --listener-arn "${LISTENER_ARN}" \
  --query 'Rules[?contains(to_string(Conditions), `telegram/webhook`)].{
    priority:Priority,
    conditions:Conditions[*].{field:Field,values:Values},
    actions:Actions[*].{type:Type,targetGroupArn:TargetGroupArn}
  }' \
  --output json

# Vérifier TOUTES les règles (pour voir l'ordre)
aws elbv2 describe-rules \
  --region me-central-1 \
  --listener-arn "${LISTENER_ARN}" \
  --query 'Rules[*].{
    priority:Priority,
    conditions:Conditions[*].{field:Field,values:Values},
    actions:Actions[*].{type:Type,targetGroupArn:TargetGroupArn}
  }' \
  --output json | jq 'sort_by(.priority)'
```

**À vérifier:**
- Une règle avec condition `Path is /telegram/webhook` existe
- Cette règle forward vers un Target Group (noter l'ARN)
- L'ordre des règles (priority) - la règle `/telegram/webhook` doit être avant la règle par défaut

---

## 2. Vérifier le Target Group "ganopa-dev-bot-tg" (ou similaire)

```bash
# Trouver le Target Group (remplacer par le nom exact si différent)
TG_ARN=$(aws elbv2 describe-target-groups \
  --region me-central-1 \
  --query 'TargetGroups[?contains(TargetGroupName, `ganopa`) || contains(TargetGroupName, `bot`)].TargetGroupArn' \
  --output text | head -1)

echo "Target Group ARN: ${TG_ARN}"

# Vérifier les détails du Target Group
aws elbv2 describe-target-groups \
  --region me-central-1 \
  --target-group-arns "${TG_ARN}" \
  --query 'TargetGroups[0].{
    name:TargetGroupName,
    port:Port,
    protocol:Protocol,
    type:TargetType,
    healthCheck:HealthCheckPath,
    healthCheckPort:HealthCheckPort,
    healthCheckProtocol:HealthCheckProtocol
  }' \
  --output json

# Vérifier les targets (IPs des tasks ECS)
aws elbv2 describe-target-health \
  --region me-central-1 \
  --target-group-arn "${TG_ARN}" \
  --query 'TargetHealthDescriptions[*].{
    target:Target.Id,
    port:Target.Port,
    health:TargetHealth.State,
    reason:TargetHealth.Reason,
    description:TargetHealth.Description
  }' \
  --output json
```

**À vérifier:**
- Type = `ip` (pas `instance`)
- Port = 8000
- Health check path = `/health`
- Au moins 1 target avec `health` = `healthy`
- Si `unhealthy`, voir `reason` et `description`

---

## 3. Vérifier l'ECS Service ganopa-dev-bot-svc

```bash
# Vérifier le service ECS
aws ecs describe-services \
  --region me-central-1 \
  --cluster vancelian-dev-api-cluster \
  --services ganopa-dev-bot-svc \
  --query 'services[0].{
    status:status,
    desired:desiredCount,
    running:runningCount,
    pending:pendingCount,
    taskDef:taskDefinition,
    loadBalancers:loadBalancers[*].{targetGroupArn:targetGroupArn,containerName:containerName,containerPort:containerPort},
    deployments:deployments[*].{status:status,rollout:rolloutState,taskDef:taskDefinition,desired:desiredCount,running:runningCount}
  }' \
  --output json

# Vérifier la Task Definition actuelle
TASKDEF_ARN=$(aws ecs describe-services \
  --region me-central-1 \
  --cluster vancelian-dev-api-cluster \
  --services ganopa-dev-bot-svc \
  --query 'services[0].taskDefinition' \
  --output text)

echo "Task Definition ARN: ${TASKDEF_ARN}"

# Vérifier l'image Docker dans la Task Definition
aws ecs describe-task-definition \
  --region me-central-1 \
  --task-definition "${TASKDEF_ARN}" \
  --query 'taskDefinition.containerDefinitions[?name==`ganopa-bot`].{
    name:name,
    image:image,
    environment:environment[*].{name:name,value:value}
  }' \
  --output json

# Lister les tasks en cours
aws ecs list-tasks \
  --region me-central-1 \
  --cluster vancelian-dev-api-cluster \
  --service-name ganopa-dev-bot-svc \
  --desired-status RUNNING \
  --query 'taskArns[]' \
  --output text

# Vérifier une task (remplacer <TASK_ARN> par une task de la liste ci-dessus)
TASK_ARN=$(aws ecs list-tasks \
  --region me-central-1 \
  --cluster vancelian-dev-api-cluster \
  --service-name ganopa-dev-bot-svc \
  --desired-status RUNNING \
  --query 'taskArns[0]' \
  --output text)

if [ -n "${TASK_ARN}" ] && [ "${TASK_ARN}" != "None" ]; then
  echo "Task ARN: ${TASK_ARN}"
  aws ecs describe-tasks \
    --region me-central-1 \
    --cluster vancelian-dev-api-cluster \
    --tasks "${TASK_ARN}" \
    --query 'tasks[0].{
      lastStatus:lastStatus,
      healthStatus:healthStatus,
      containers:containers[*].{name:name,image:image,lastStatus:lastStatus},
      attachments:attachments[*].{type:type,details:details[*].{name:name,value:value}}
    }' \
    --output json
fi
```

**À vérifier:**
- `status` = ACTIVE
- `desired` = 1
- `running` = 1
- `loadBalancers` contient le Target Group ARN trouvé à l'étape 2
- `image` dans la Task Definition correspond au dernier commit (tag = GITHUB_SHA)
- Tasks sont RUNNING et HEALTHY

---

## 4. Vérifier /_meta renvoie la VERSION attendue

```bash
# Test de l'endpoint /_meta
curl -s https://api.maisonganopa.com/_meta | jq

# Vérifier les headers
curl -s -I https://api.maisonganopa.com/_meta | grep -i "x-ganopa"

# Test avec version spécifique
VERSION_ATTENDUE="ganopa-bot-7f22c89b"  # Remplacer par la version attendue
VERSION_ACTUELLE=$(curl -s https://api.maisonganopa.com/_meta | jq -r '.version')

if [ "${VERSION_ACTUELLE}" = "${VERSION_ATTENDUE}" ]; then
  echo "✅ Version correcte: ${VERSION_ACTUELLE}"
else
  echo "❌ Version incorrecte:"
  echo "  Attendu: ${VERSION_ATTENDUE}"
  echo "  Actuel: ${VERSION_ACTUELLE}"
fi
```

**À vérifier:**
- `service` = "ganopa-bot"
- `version` correspond à la version attendue (hash basé sur BUILD_ID)
- `build_id` correspond au BUILD_ID dans ECS
- `has_openai_key` = true
- `has_webhook_secret` = true
- Headers `X-Ganopa-Build-Id` et `X-Ganopa-Version` présents

---

## 5. Test End-to-End: Envoyer un message Telegram

```bash
# Vérifier que le webhook répond
curl -X GET https://api.maisonganopa.com/telegram/webhook

# Vérifier les logs CloudWatch après avoir envoyé un message Telegram
# (remplacer <LOG_GROUP> par le nom du log group ECS)
LOG_GROUP="/ecs/ganopa-dev-bot-task"  # À adapter selon votre configuration

aws logs tail "${LOG_GROUP}" \
  --region me-central-1 \
  --since 10m \
  --format short \
  --filter-pattern "telegram_webhook_post OR openai_request_start OR openai_request_success OR telegram_send_success"
```

**À vérifier dans les logs:**
- `telegram_webhook_post` avec `update_id`, `chat_id`, `text_len`
- `telegram_message_extracted` avec `text_preview`
- `openai_request_start` avec `model`, `text_len`
- `openai_request_success` avec `response_len`, `tokens_used`, `latency_ms`
- `telegram_send_success` avec `status_code`

---

## Checklist de Validation

- [ ] ALB route `/telegram/webhook` vers le bon Target Group
- [ ] Target Group a au moins 1 target healthy
- [ ] ECS service est ACTIVE avec running count = 1
- [ ] Task Definition utilise la dernière image (tag = dernier GITHUB_SHA)
- [ ] `/_meta` renvoie la VERSION attendue
- [ ] Headers `X-Ganopa-Build-Id` et `X-Ganopa-Version` présents
- [ ] Envoi d'un message Telegram génère les logs attendus
- [ ] La réponse Telegram contient le prefix "🤖" (preuve OpenAI)

---

## Commandes Rapides (One-liner)

```bash
# Vérifier routing ALB + Target Group + ECS en une commande
echo "=== ALB Rules ===" && \
aws elbv2 describe-rules --region me-central-1 --listener-arn $(aws elbv2 describe-listeners --region me-central-1 --load-balancer-arn $(aws elbv2 describe-load-balancers --region me-central-1 --query 'LoadBalancers[?contains(DNSName, `maisonganopa`)].LoadBalancerArn' --output text) --query 'Listeners[?Port==`443`].ListenerArn' --output text) --query 'Rules[*].{p:Priority,c:Conditions[*].Values,a:Actions[*].TargetGroupArn}' --output json && \
echo "=== Target Group Health ===" && \
aws elbv2 describe-target-health --region me-central-1 --target-group-arn $(aws elbv2 describe-target-groups --region me-central-1 --query 'TargetGroups[?contains(TargetGroupName, `ganopa`)].TargetGroupArn' --output text | head -1) --query 'TargetHealthDescriptions[*].{target:Target.Id,health:TargetHealth.State}' --output json && \
echo "=== ECS Service ===" && \
aws ecs describe-services --region me-central-1 --cluster vancelian-dev-api-cluster --services ganopa-dev-bot-svc --query 'services[0].{status:status,running:runningCount,taskDef:taskDefinition}' --output json && \
echo "=== /_meta ===" && \
curl -s https://api.maisonganopa.com/_meta | jq
```

