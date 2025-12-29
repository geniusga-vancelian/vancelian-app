# 🔍 Diagnostic AWS - Commandes de Vérification

## 🎯 Objectif

Vérifier l'état actuel de l'infrastructure AWS pour identifier pourquoi `/telegram/webhook` retourne 503.

---

## 📋 Commandes AWS CLI

### 1. Vérifier le Service ECS

```bash
# Service status, desired/running count, load balancer
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
    loadBalancers:loadBalancers,
    deployments:deployments[*].{status:status,rollout:rolloutState,taskDef:taskDefinition}
  }' \
  --output json
```

**À vérifier:**
- `status` = ACTIVE (pas INACTIVE)
- `desired` = 1
- `running` = 1
- `loadBalancers` = non vide (le service doit être attaché à un LB)

### 2. Lister les Target Groups

```bash
# Lister tous les Target Groups (chercher ceux liés à ganopa/bot)
aws elbv2 describe-target-groups \
  --region me-central-1 \
  --query 'TargetGroups[?contains(TargetGroupName, `ganopa`) || contains(TargetGroupName, `bot`) || contains(TargetGroupName, `telegram`)].{
    name:TargetGroupName,
    arn:TargetGroupArn,
    port:Port,
    protocol:Protocol,
    type:TargetType,
    healthCheck:HealthCheckPath,
    healthCheckPort:HealthCheckPort
  }' \
  --output json
```

**À vérifier:**
- Type = `ip` (pas `instance`)
- Port = 8000
- Health check path = `/health`

### 3. Vérifier les Targets d'un Target Group

```bash
# Remplacer <TG_ARN> par l'ARN du Target Group trouvé à l'étape 2
aws elbv2 describe-target-health \
  --region me-central-1 \
  --target-group-arn <TG_ARN> \
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
- Au moins 1 target avec `health` = `healthy`
- Si `unhealthy`, voir `reason` et `description`

### 4. Vérifier les Règles ALB

```bash
# D'abord, trouver l'ARN de l'ALB
aws elbv2 describe-load-balancers \
  --region me-central-1 \
  --query 'LoadBalancers[?contains(DNSName, `maisonganopa`)].{
    name:LoadBalancerName,
    arn:LoadBalancerArn,
    dns:DNSName
  }' \
  --output json

# Ensuite, vérifier les règles du listener HTTPS (443)
# Remplacer <ALB_ARN> par l'ARN trouvé ci-dessus
aws elbv2 describe-listeners \
  --region me-central-1 \
  --load-balancer-arn <ALB_ARN> \
  --query 'Listeners[?Port==`443`].{
    port:Port,
    protocol:Protocol,
    rules:DefaultActions[0].TargetGroupArn
  }' \
  --output json

# Vérifier les règles personnalisées (rules)
aws elbv2 describe-rules \
  --region me-central-1 \
  --listener-arn <LISTENER_ARN> \
  --query 'Rules[*].{
    priority:Priority,
    conditions:Conditions[*].{field:Field,values:Values},
    actions:Actions[*].{type:Type,targetGroupArn:TargetGroupArn}
  }' \
  --output json
```

**À vérifier:**
- Une règle avec condition `Path is /telegram/webhook`
- Cette règle forward vers le Target Group de `ganopa-dev-bot-svc`
- L'ordre des règles (priority) - la première qui correspond est utilisée

### 5. Vérifier les Tasks ECS

```bash
# Lister les tasks du service
aws ecs list-tasks \
  --region me-central-1 \
  --cluster vancelian-dev-api-cluster \
  --service-name ganopa-dev-bot-svc \
  --desired-status RUNNING \
  --query 'taskArns[]' \
  --output text

# Décrire une task (remplacer <TASK_ARN> par une task de la liste ci-dessus)
aws ecs describe-tasks \
  --region me-central-1 \
  --cluster vancelian-dev-api-cluster \
  --tasks <TASK_ARN> \
  --query 'tasks[0].{
    lastStatus:lastStatus,
    healthStatus:healthStatus,
    containers:containers[*].{name:name,image:image,lastStatus:lastStatus},
    attachments:attachments[*].{type:type,details:details[*].{name:name,value:value}}
  }' \
  --output json
```

**À vérifier:**
- `lastStatus` = RUNNING
- `healthStatus` = HEALTHY (si health check configuré)
- `attachments` contient les IPs enregistrées dans le Target Group

---

## 🔧 Commandes de Correction

### Si le Service ECS est INACTIVE

```bash
# Activer le service avec desired count 1
aws ecs update-service \
  --region me-central-1 \
  --cluster vancelian-dev-api-cluster \
  --service ganopa-dev-bot-svc \
  --desired-count 1 \
  --force-new-deployment
```

### Si le Service n'est pas attaché au Load Balancer

**Via AWS Console (recommandé):**
1. ECS → Services → `ganopa-dev-bot-svc`
2. Update service
3. Load balancing → Add load balancer
4. Sélectionner le Target Group correct
5. Container name: `ganopa-bot`
6. Container port: 8000
7. Update service

**Important:** ECS enregistrera automatiquement les IPs des tasks dans le Target Group.

### Si le Target Group n'a pas de Targets

**Vérifier d'abord:**
- Le service ECS est-il attaché au Target Group?
- Les tasks sont-elles RUNNING?

**Si oui, les targets devraient être enregistrés automatiquement.**

**Si non, vérifier:**
- Le service ECS a-t-il un Load Balancer attaché?
- Le port mapping est-il correct (8000)?

---

## 📊 Résumé des Vérifications

### Checklist

- [ ] Service ECS existe et est ACTIVE
- [ ] Service ECS a desired count = 1 et running count = 1
- [ ] Service ECS est attaché à un Load Balancer
- [ ] Target Group existe pour `ganopa-bot`
- [ ] Target Group type = IP (pas Instance)
- [ ] Target Group port = 8000
- [ ] Target Group health check = `/health` sur port 8000
- [ ] Target Group a au moins 1 target healthy
- [ ] ALB a une règle pour `/telegram/webhook`
- [ ] Cette règle forward vers le Target Group de `ganopa-dev-bot-svc`
- [ ] L'ordre des règles ALB est correct (la règle `/telegram/webhook` est avant la règle par défaut)

---

## 🚨 Problèmes Courants et Solutions

### Problème 1: Service INACTIVE

**Symptôme:** `ServiceNotActiveException`

**Solution:**
```bash
aws ecs update-service \
  --region me-central-1 \
  --cluster vancelian-dev-api-cluster \
  --service ganopa-dev-bot-svc \
  --desired-count 1
```

### Problème 2: Target Group Vide (0 targets)

**Symptôme:** 503 sur `/telegram/webhook`

**Cause:** Le service ECS n'est pas attaché au Target Group, ou les tasks ne sont pas RUNNING.

**Solution:**
1. Vérifier que le service ECS est attaché au Load Balancer
2. Vérifier que les tasks sont RUNNING
3. Attendre 1-2 minutes pour que les IPs soient enregistrées automatiquement

### Problème 3: Targets Unhealthy

**Symptôme:** Targets dans le TG mais status = unhealthy

**Causes possibles:**
- Health check path incorrect (`/health` doit exister)
- Port incorrect (8000)
- Security Group bloque le trafic ALB → Tasks
- Container ne démarre pas correctement

**Solution:**
1. Vérifier les logs CloudWatch du service
2. Vérifier le Security Group (autoriser le trafic ALB → Tasks sur port 8000)
3. Tester manuellement: `curl http://<TASK_IP>:8000/health`

### Problème 4: Règle ALB Incorrecte

**Symptôme:** `/telegram/webhook` pointe vers le mauvais Target Group

**Solution:**
1. Modifier la règle ALB pour `/telegram/webhook`
2. Forward to → Target Group de `ganopa-dev-bot-svc`

---

## 📞 Prochaines Étapes

1. **Exécuter les commandes de diagnostic** ci-dessus
2. **Prendre des captures d'écran** de:
   - ECS Service → Load Balancer
   - Target Group → Targets
   - ALB → Listener Rules
3. **Appliquer les corrections** selon les résultats
4. **Tester** les endpoints après correction

