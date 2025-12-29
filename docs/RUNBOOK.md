# Runbook - Vancelian App

## TL;DR

Procédures pas à pas pour diagnostiquer et résoudre les problèmes courants du service `ganopa-bot`. Chaque runbook liste: symptômes, causes probables, checks AWS Console, checks CLI, fix, validation.

---

## Ce qui est vrai aujourd'hui

### Runbook 1: Le bot répond en echo (au lieu de l'IA)

**Symptômes:**
- Envoi de "Hello" → Réponse "✅ Reçu: Hello" (ou similaire)
- Pas de prefix "🤖" dans la réponse
- Logs CloudWatch ne contiennent pas `openai_called`

**Causes probables:**
1. Mauvais routing ALB (webhook pointe vers `agent_gateway` au lieu de `ganopa-bot`)
2. Ancienne version déployée (code echo encore présent)
3. `OPENAI_API_KEY` manquante ou invalide
4. Code ne passe pas dans l'image Docker

**Checks AWS Console:**
1. **EC2 → Load Balancers:**
   - Sélectionner l'ALB qui sert `api.maisonganopa.com`
   - Listeners → HTTPS (443) → Rules
   - Vérifier la règle pour `/telegram/webhook` → Target Group doit être celui de `ganopa-dev-bot-svc`

2. **ECS → Services → `ganopa-dev-bot-svc`:**
   - Onglet "Configuration et mise en réseau" → Load balancer
   - Vérifier que le Target Group est correct
   - Onglet "Déploiements" → Vérifier la Task Definition revision
   - Onglet "Configuration" → Container `ganopa-bot` → Environment variables
   - Vérifier que `OPENAI_API_KEY` est présente

3. **ECR → Repositories → `ganopa-bot`:**
   - Vérifier la dernière image (tag = dernier GITHUB_SHA)

**Checks CLI:**
```bash
# 1. Vérifier la version déployée
curl -s https://api.maisonganopa.com/_meta | jq '.version'

# 2. Vérifier le routing ALB
ALB_ARN=$(aws elbv2 describe-load-balancers --region me-central-1 \
  --query 'LoadBalancers[?contains(DNSName, `maisonganopa`)].LoadBalancerArn' --output text)
LISTENER_ARN=$(aws elbv2 describe-listeners --region me-central-1 \
  --load-balancer-arn "${ALB_ARN}" --query 'Listeners[?Port==`443`].ListenerArn' --output text)
aws elbv2 describe-rules --region me-central-1 --listener-arn "${LISTENER_ARN}" \
  --query 'Rules[*].{priority:Priority,conditions:Conditions[*].Values,actions:Actions[*].TargetGroupArn}' \
  --output json | jq

# 3. Vérifier l'image dans la Task Definition
TASKDEF_ARN=$(aws ecs describe-services --region me-central-1 \
  --cluster vancelian-dev-api-cluster --services ganopa-dev-bot-svc \
  --query 'services[0].taskDefinition' --output text)
aws ecs describe-task-definition --region me-central-1 --task-definition "${TASKDEF_ARN}" \
  --query 'taskDefinition.containerDefinitions[?name==`ganopa-bot`].{image:image,env:environment[*].name}' \
  --output json | jq

# 4. Vérifier les logs
aws logs tail /ecs/ganopa-dev-bot-task --region me-central-1 --since 10m \
  --format short --filter-pattern "openai_called OR openai_error"
```

**Fix:**
1. **Si routing ALB incorrect:**
   - EC2 → Load Balancers → ALB → Listeners → HTTPS (443) → Rules
   - Modifier la règle pour `/telegram/webhook` → Forward to → Target Group de `ganopa-dev-bot-svc`

2. **Si ancienne version:**
   - Vérifier que le workflow GitHub Actions a réussi
   - Vérifier que l'image ECR tag correspond au dernier commit
   - Forcer un nouveau déploiement: ECS → Services → `ganopa-dev-bot-svc` → Update service → Force new deployment

3. **Si OPENAI_API_KEY manquante:**
   - ECS → Task Definitions → `ganopa-bot:XX` → Create new revision
   - Container `ganopa-bot` → Environment variables → Ajouter `OPENAI_API_KEY`
   - Enregistrer → Update service avec nouvelle revision

**Validation:**
```bash
# 1. Vérifier la version
curl -s https://api.maisonganopa.com/_meta | jq '.version'

# 2. Envoyer un message Telegram
# Attendu: Réponse avec prefix "🤖"

# 3. Vérifier les logs
aws logs tail /ecs/ganopa-dev-bot-task --region me-central-1 --since 5m \
  --format short --filter-pattern "openai_ok"
```

---

### Runbook 2: /telegram/webhook renvoie 503/504

**Symptômes:**
- `curl https://api.maisonganopa.com/telegram/webhook` → 503 Service Unavailable
- Telegram ne peut pas envoyer de webhooks
- Health check échoue

**Causes probables:**
1. Target Group vide (0 targets registered)
2. Targets unhealthy (health check échoue)
3. Service ECS INACTIVE
4. Security Group bloque le trafic ALB → Tasks
5. Tasks ne démarrent pas (erreur container)

**Checks AWS Console:**
1. **EC2 → Target Groups:**
   - Sélectionner le Target Group de `ganopa-dev-bot-svc`
   - Onglet "Targets" → Vérifier le nombre de targets
   - Vérifier le statut (healthy/unhealthy)
   - Si unhealthy, voir "Health check details" → Reason

2. **ECS → Services → `ganopa-dev-bot-svc`:**
   - Onglet "Déploiements" → Vérifier `runningCount` et `desiredCount`
   - Onglet "Logs" → Voir les erreurs de démarrage
   - Onglet "Configuration et mise en réseau" → Vérifier que le service est attaché au Target Group

3. **ECS → Clusters → `vancelian-dev-api-cluster` → Tasks:**
   - Vérifier les tasks STOPPED → Voir "Stopped reason"
   - Vérifier les tasks RUNNING → Voir "Health status"

4. **EC2 → Security Groups:**
   - Tasks SG → Inbound rules → Vérifier que port 8000 est autorisé depuis ALB SG
   - ALB SG → Inbound rules → Vérifier que port 443 est autorisé depuis Internet

**Checks CLI:**
```bash
# 1. Vérifier le Target Group
TG_ARN=$(aws elbv2 describe-target-groups --region me-central-1 \
  --query 'TargetGroups[?contains(TargetGroupName, `ganopa`)].TargetGroupArn' --output text | head -1)
aws elbv2 describe-target-health --region me-central-1 --target-group-arn "${TG_ARN}" \
  --query 'TargetHealthDescriptions[*].{target:Target.Id,health:TargetHealth.State,reason:TargetHealth.Reason}' \
  --output json | jq

# 2. Vérifier le service ECS
aws ecs describe-services --region me-central-1 \
  --cluster vancelian-dev-api-cluster --services ganopa-dev-bot-svc \
  --query 'services[0].{status:status,desired:desiredCount,running:runningCount,pending:pendingCount}' \
  --output json | jq

# 3. Vérifier les tasks STOPPED
aws ecs list-tasks --region me-central-1 \
  --cluster vancelian-dev-api-cluster --service-name ganopa-dev-bot-svc \
  --desired-status STOPPED --max-results 5 --query 'taskArns[]' --output text | \
  xargs -I {} aws ecs describe-tasks --region me-central-1 \
  --cluster vancelian-dev-api-cluster --tasks {} \
  --query 'tasks[0].{stoppedReason:stoppedReason,containers:containers[*].{name:name,reason:reason}}' \
  --output json | jq
```

**Fix:**
1. **Si Target Group vide:**
   - Vérifier que le service ECS est attaché au Target Group
   - ECS → Services → `ganopa-dev-bot-svc` → Update service
   - Load balancing → Vérifier que le Target Group est configuré
   - Attendre 1-2 minutes pour que les IPs soient enregistrées

2. **Si Targets unhealthy:**
   - Vérifier le health check path (`/health`) et port (8000)
   - Vérifier que le container écoute sur `0.0.0.0:8000`
   - Vérifier les Security Groups (ALB → Tasks)
   - Vérifier les logs CloudWatch pour erreurs de démarrage

3. **Si Service INACTIVE:**
   - ECS → Services → `ganopa-dev-bot-svc` → Update service
   - Desired count: 1
   - Update service

4. **Si Security Group bloque:**
   - EC2 → Security Groups → Tasks SG
   - Inbound rules → Ajouter: Type Custom TCP, Port 8000, Source: ALB SG

**Validation:**
```bash
# 1. Vérifier le health check
curl -s https://api.maisonganopa.com/health | jq

# 2. Vérifier le webhook
curl -s https://api.maisonganopa.com/telegram/webhook

# 3. Vérifier les targets
aws elbv2 describe-target-health --region me-central-1 --target-group-arn "${TG_ARN}" \
  --query 'TargetHealthDescriptions[*].TargetHealth.State' --output text
# Attendu: "healthy" (au moins 1)
```

---

### Runbook 3: ACM/HTTPS ne marche pas

**Symptômes:**
- `curl https://api.maisonganopa.com/health` → SSL certificate error
- Browser: "Your connection is not private"
- Certificate expired ou invalide

**Causes probables:**
1. Certificate ACM expiré
2. Certificate non attaché au listener ALB
3. Domain name ne correspond pas au certificate
4. Certificate en statut "Validation failed"

**Checks AWS Console:**
1. **ACM → Certificates:**
   - Vérifier le statut (Issued, Validation failed, Expired)
   - Vérifier le domaine (`*.maisonganopa.com` ou `api.maisonganopa.com`)
   - Vérifier la date d'expiration

2. **EC2 → Load Balancers:**
   - Sélectionner l'ALB
   - Onglet "Listeners" → HTTPS (443)
   - Vérifier que le certificate ACM est attaché

**Checks CLI:**
```bash
# 1. Vérifier les certificates ACM
aws acm list-certificates --region me-central-1 \
  --query 'CertificateSummaryList[*].{domain:DomainName,arn:CertificateArn,status:Status}' \
  --output json | jq

# 2. Vérifier le certificate attaché au listener
ALB_ARN=$(aws elbv2 describe-load-balancers --region me-central-1 \
  --query 'LoadBalancers[?contains(DNSName, `maisonganopa`)].LoadBalancerArn' --output text)
aws elbv2 describe-listeners --region me-central-1 --load-balancer-arn "${ALB_ARN}" \
  --query 'Listeners[?Port==`443`].{port:Port,certificates:Certificates[*].CertificateArn}' \
  --output json | jq
```

**Fix:**
1. **Si certificate expiré:**
   - ACM → Request a certificate
   - Domain: `api.maisonganopa.com` (ou `*.maisonganopa.com`)
   - Validation: DNS (ajouter le CNAME dans Route53)
   - Attendre la validation
   - Attacher au listener ALB

2. **Si certificate non attaché:**
   - EC2 → Load Balancers → ALB → Listeners → HTTPS (443) → Edit
   - Default SSL certificate → Sélectionner le certificate ACM
   - Save

**Validation:**
```bash
# Vérifier le certificate
openssl s_client -connect api.maisonganopa.com:443 -servername api.maisonganopa.com < /dev/null 2>/dev/null | \
  openssl x509 -noout -dates
```

---

### Runbook 4: Target group draining / no registered targets

**Symptômes:**
- Target Group → Targets → 0 targets
- Health check: "No registered targets"
- ALB ne peut pas forward les requêtes

**Causes probables:**
1. Service ECS non attaché au Target Group
2. Tasks ne démarrent pas (erreur container, image invalide)
3. Tasks démarrent mais ne passent pas le health check
4. Service ECS INACTIVE

**Checks AWS Console:**
1. **ECS → Services → `ganopa-dev-bot-svc`:**
   - Onglet "Configuration et mise en réseau" → Load balancer
   - Vérifier que le Target Group est listé
   - Si non, le service n'est pas attaché

2. **ECS → Clusters → Tasks:**
   - Vérifier les tasks RUNNING
   - Vérifier les tasks STOPPED → Voir "Stopped reason"

3. **EC2 → Target Groups:**
   - Onglet "Targets" → Vérifier le statut
   - Onglet "Health checks" → Vérifier path (`/health`) et port (8000)

**Checks CLI:**
```bash
# 1. Vérifier l'attachement du service au Target Group
aws ecs describe-services --region me-central-1 \
  --cluster vancelian-dev-api-cluster --services ganopa-dev-bot-svc \
  --query 'services[0].loadBalancers[*].{targetGroupArn:targetGroupArn,containerName:containerName,containerPort:containerPort}' \
  --output json | jq

# 2. Vérifier les tasks
aws ecs list-tasks --region me-central-1 \
  --cluster vancelian-dev-api-cluster --service-name ganopa-dev-bot-svc \
  --desired-status RUNNING --query 'taskArns[]' --output text
```

**Fix:**
1. **Si service non attaché:**
   - ECS → Services → `ganopa-dev-bot-svc` → Update service
   - Load balancing → Add load balancer
   - Target group: Sélectionner le Target Group
   - Container name: `ganopa-bot`
   - Container port: 8000
   - Update service
   - Attendre 2-3 minutes pour que les IPs soient enregistrées

2. **Si tasks ne démarrent pas:**
   - Vérifier les logs CloudWatch pour erreurs
   - Vérifier l'image Docker (existe-t-elle dans ECR ?)
   - Vérifier les variables d'environnement requises

**Validation:**
```bash
# Vérifier les targets
TG_ARN=$(aws elbv2 describe-target-groups --region me-central-1 \
  --query 'TargetGroups[?contains(TargetGroupName, `ganopa`)].TargetGroupArn' --output text | head -1)
aws elbv2 describe-target-health --region me-central-1 --target-group-arn "${TG_ARN}" \
  --query 'TargetHealthDescriptions[*].TargetHealth.State' --output text
# Attendu: "healthy" (au moins 1)
```

---

### Runbook 5.5: Doc-Memory Mode (CTO Agent)

### Symptômes
- Le bot répond avec le préfixe "J'ai bien relu toute la doc (version: ...)" au premier message
- Les messages suivants n'ont pas le préfixe (mémoire active)
- Le endpoint `/_meta` montre `docs_hash` et `memory_enabled: true`

### Probable Causes
- Mode normal: le bot charge la documentation au premier message d'un chat
- La mémoire expire après `MEMORY_TTL_SECONDS` (default: 1800 = 30 minutes)

### Vérifications

**1. Vérifier que la doc est chargée:**
```bash
curl -s https://api.maisonganopa.com/_meta | jq '{docs_hash, docs_loaded, memory_enabled}'
```

**Résultat attendu:**
- `docs_hash`: Hash SHA256 (12 caractères) ou "no-docs"
- `docs_loaded`: `true` si la doc est présente
- `memory_enabled`: `true`

**2. Vérifier les logs CloudWatch:**
```bash
aws logs tail /ecs/ganopa-dev-bot-task \
  --region me-central-1 \
  --since 10m \
  --format short \
  --filter-pattern "docs_loaded OR memory_miss OR memory_hit"
```

**Logs attendus:**
- `docs_loaded`: Hash + length de la doc
- `memory_miss`: Premier message d'un chat (fresh context)
- `memory_hit`: Messages suivants (mémoire existante)

**3. Vérifier que le dossier docs/ est dans l'image Docker:**
```bash
# Dans le workflow GitHub Actions, vérifier:
docker run --rm <IMAGE_URI> test -d docs && echo "✅ Docs present" || echo "❌ Docs missing"
```

### Fix

**Si docs_hash = "no-docs":**
1. Vérifier que le Dockerfile copie `docs/` (build depuis repo root)
2. Vérifier que le workflow GitHub Actions build depuis repo root: `docker build -f services/ganopa-bot/Dockerfile .`
3. Vérifier que `DOCS_DIR` env var pointe vers `/app/docs` (default)

**Si memory ne fonctionne pas:**
1. Vérifier les env vars: `MEMORY_TTL_SECONDS`, `MEMORY_MAX_MESSAGES`
2. Vérifier les logs pour erreurs `agent_service_error`
3. Vérifier que `memory_enabled: true` dans `/_meta`

### Validation

**Test manuel:**
1. Envoyer un premier message au bot → doit avoir le préfixe "J'ai bien relu..."
2. Envoyer un deuxième message → ne doit PAS avoir le préfixe
3. Attendre 30+ minutes → le prochain message doit avoir le préfixe (mémoire expirée)

**Vérifier via `/_meta`:**
```bash
curl -s https://api.maisonganopa.com/_meta | jq '{docs_hash, memory_active_chats}'
```

---

## Runbook 6: Le déploiement GitHub est vert mais la version n'a pas changé

**Symptômes:**
- GitHub Actions workflow: ✅ Success
- `curl https://api.maisonganopa.com/_meta | jq .version` → Ancienne version
- Code modifié mais pas déployé

**Causes probables:**
1. Image Docker tag incorrect (pas le bon GITHUB_SHA)
2. Task Definition non mise à jour
3. Service ECS utilise encore l'ancienne Task Definition revision
4. Service ECS n'a pas redémarré (force new deployment manquant)

**Checks AWS Console:**
1. **ECR → Repositories → `ganopa-bot`:**
   - Vérifier la dernière image (tag = dernier GITHUB_SHA)
   - Vérifier la date de push

2. **ECS → Task Definitions → `ganopa-bot`:**
   - Vérifier la dernière revision
   - Container `ganopa-bot` → Image → Vérifier le tag

3. **ECS → Services → `ganopa-dev-bot-svc`:**
   - Onglet "Déploiements" → Vérifier la Task Definition utilisée
   - Comparer avec la dernière revision

**Checks CLI:**
```bash
# 1. Vérifier la dernière image ECR
aws ecr describe-images --region me-central-1 --repository-name ganopa-bot \
  --query 'sort_by(imageDetails, &imagePushedAt)[-1].{tag:imageTags[0],pushed:imagePushedAt}' \
  --output json | jq

# 2. Vérifier la Task Definition du service
TASKDEF_ARN=$(aws ecs describe-services --region me-central-1 \
  --cluster vancelian-dev-api-cluster --services ganopa-dev-bot-svc \
  --query 'services[0].taskDefinition' --output text)
aws ecs describe-task-definition --region me-central-1 --task-definition "${TASKDEF_ARN}" \
  --query 'taskDefinition.{revision:revision,image:containerDefinitions[0].image}' \
  --output json | jq

# 3. Vérifier la version déployée
curl -s https://api.maisonganopa.com/_meta | jq '{version,build_id}'
```

**Fix:**
1. **Si image tag incorrect:**
   - Vérifier le workflow GitHub Actions (étape "Build & push Docker image")
   - Vérifier que `IMAGE_TAG="${GITHUB_SHA}"` est utilisé
   - Relancer le workflow si nécessaire

2. **Si Task Definition non mise à jour:**
   - Vérifier le workflow GitHub Actions (étape "Register new task definition revision")
   - Vérifier que l'image est bien patchée dans la Task Definition

3. **Si service utilise ancienne revision:**
   - ECS → Services → `ganopa-dev-bot-svc` → Update service
   - Task definition: Sélectionner la dernière revision
   - Force new deployment: ✅
   - Update service

**Validation:**
```bash
# Vérifier la version
curl -s https://api.maisonganopa.com/_meta | jq '.version'
# Comparer avec le dernier GITHUB_SHA
```

---

## À vérifier quand ça casse

### Un runbook ne couvre pas le problème

1. Documenter le problème (symptômes, causes, fix)
2. Ajouter un nouveau runbook dans ce fichier
3. Mettre à jour la table des matières si nécessaire

### Un runbook est obsolète

1. Vérifier si la procédure fonctionne encore
2. Mettre à jour avec les nouvelles étapes
3. Tester la procédure

---

**Dernière mise à jour:** 2025-12-29

