# Commandes de Vérification - Ganopa Bot

## 📋 Checklist de Preuve (3 minutes)

### A) Test Webhook GET
```bash
curl -X GET https://api.maisonganopa.com/telegram/webhook
```
**Attendu:** `{"ok": true, "hint": "Telegram webhook expects POST"}`

### B) Test Signature Telegram
1. Activer le mode test dans la Task Definition ECS:
   - Variable: `BOT_SIGNATURE_TEST=1`
2. Envoyer un message au bot Telegram
3. **Attendu:** `✅ VERSION-TEST-123 | build-YYYYMMDD-HHMMSS`

### C) Vérifier Logs CloudWatch
Chercher dans `/aws/ecs/ganopa-dev-bot`:
- `ganopa_bot_started` avec `bot_build_id`
- `signature_test_response` (si mode test activé)

### D) Vérifier Image ECR
Comparer l'image déployée avec le dernier commit Git

---

## 🔧 Commandes Terminal (Mac zsh)

### 1. État Git Local

```bash
cd /Users/gael/Library/CloudStorage/OneDrive-Vancelian/Documents/vancelian-app

# État actuel
git status

# Derniers commits locaux
git log --oneline -5

# Derniers commits sur origin/main
git log origin/main --oneline -5

# Différence entre local et remote
git log origin/main..HEAD --oneline
```

### 2. Commit et Push

```bash
# Vérifier les fichiers modifiés
git status

# Ajouter les fichiers (exclure .env et .venv)
git add services/ganopa-bot/app/main.py services/ganopa-bot/app/config.py

# Commit
git commit -m "feat: add build stamp and signature test mode for deployment verification"

# Push
git push origin main
```

**Si conflit de rebase:**
```bash
# Voir les fichiers en conflit
git status

# Pour main.py, garder la version locale (nos corrections)
git checkout --ours services/ganopa-bot/app/main.py
git add services/ganopa-bot/app/main.py

# Continuer le rebase
git rebase --continue
```

### 3. AWS CLI - Vérification ECS

**Prérequis:** AWS CLI configuré avec credentials pour région `me-central-1`

```bash
# Lister les services dans le cluster
aws ecs list-services \
  --cluster vancelian-dev-api-cluster \
  --region me-central-1 \
  --output table

# Décrire le service Ganopa (essayer les noms possibles)
aws ecs describe-services \
  --cluster vancelian-dev-api-cluster \
  --services ganopa-dev-bot-svc \
  --region me-central-1 \
  --query "services[0].{serviceName:serviceName,status:status,desiredCount:desiredCount,runningCount:runningCount,taskDefinition:taskDefinition}" \
  --output json

# Si le service n'existe pas, lister tous les services pour trouver le bon nom
aws ecs list-services \
  --cluster vancelian-dev-api-cluster \
  --region me-central-1 \
  --output text | grep -i ganopa

# Lister les tasks en cours d'exécution
aws ecs list-tasks \
  --cluster vancelian-dev-api-cluster \
  --service-name ganopa-dev-bot-svc \
  --desired-status RUNNING \
  --region me-central-1 \
  --output text

# Décrire une task pour obtenir l'IMAGE URI
TASK_ARN=$(aws ecs list-tasks \
  --cluster vancelian-dev-api-cluster \
  --service-name ganopa-dev-bot-svc \
  --desired-status RUNNING \
  --region me-central-1 \
  --query "taskArns[0]" \
  --output text)

echo "Task ARN: $TASK_ARN"

# Extraire l'image URI
aws ecs describe-tasks \
  --cluster vancelian-dev-api-cluster \
  --tasks $TASK_ARN \
  --region me-central-1 \
  --query "tasks[0].containers[?name=='ganopa-bot'].image" \
  --output text

# Vérifier la Task Definition
TASKDEF_ARN=$(aws ecs describe-services \
  --cluster vancelian-dev-api-cluster \
  --services ganopa-dev-bot-svc \
  --region me-central-1 \
  --query "services[0].taskDefinition" \
  --output text)

echo "Task Definition: $TASKDEF_ARN"

# Voir les variables d'environnement de la Task Definition
aws ecs describe-task-definition \
  --task-definition $TASKDEF_ARN \
  --region me-central-1 \
  --query "taskDefinition.containerDefinitions[?name=='ganopa-bot'].environment" \
  --output json
```

### 4. CloudWatch Logs

```bash
# Voir les derniers logs (50 lignes)
aws logs tail /aws/ecs/ganopa-dev-bot \
  --region me-central-1 \
  --since 10m \
  --format short

# Filtrer pour "ganopa_bot_started"
aws logs tail /aws/ecs/ganopa-dev-bot \
  --region me-central-1 \
  --since 1h \
  --filter-pattern "ganopa_bot_started" \
  --format short

# Filtrer pour "signature_test"
aws logs tail /aws/ecs/ganopa-dev-bot \
  --region me-central-1 \
  --since 1h \
  --filter-pattern "signature_test" \
  --format short

# Suivre les logs en temps réel
aws logs tail /aws/ecs/ganopa-dev-bot \
  --region me-central-1 \
  --follow \
  --format short
```

### 5. Vérifier le Commit SHA dans l'Image

```bash
# Extraire l'IMAGE URI de la task
IMAGE_URI=$(aws ecs describe-tasks \
  --cluster vancelian-dev-api-cluster \
  --tasks $TASK_ARN \
  --region me-central-1 \
  --query "tasks[0].containers[?name=='ganopa-bot'].image" \
  --output text)

echo "Image URI: $IMAGE_URI"

# Extraire le tag (GITHUB_SHA) de l'URI
# Format attendu: 411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:abc123def456...
IMAGE_TAG=$(echo $IMAGE_URI | cut -d: -f2)
echo "Image Tag (Git SHA): $IMAGE_TAG"

# Comparer avec le dernier commit local
git log --oneline -1
echo "Local commit SHA: $(git rev-parse HEAD)"
```

---

## 🌐 AWS Console (si AWS CLI non configuré)

### Trouver le Service ECS

1. **AWS Console** → **ECS** → **Clusters**
2. Sélectionner: `vancelian-dev-api-cluster`
3. Onglet **Services**
4. Chercher un service contenant "ganopa" ou "bot"
5. Cliquer sur le service

### Voir l'Image Déployée

1. Dans le service, onglet **Tasks**
2. Cliquer sur une task RUNNING
3. Onglet **Containers**
4. Voir le champ **Image** (ex: `411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:abc123...`)
5. Le tag après `:` est le `GITHUB_SHA` du commit déployé

### Voir les Variables d'Environnement

1. Dans le service, onglet **Configuration and tasks**
2. Cliquer sur la Task Definition (lien bleu)
3. Section **Container definitions**
4. Cliquer sur le container `ganopa-bot`
5. Voir **Environment variables**

### CloudWatch Logs

1. **AWS Console** → **CloudWatch** → **Log groups**
2. Chercher: `/aws/ecs/ganopa-dev-bot` (ou similaire)
3. Cliquer sur le log group
4. Voir les **Log streams** récents
5. Cliquer sur un stream pour voir les logs

---

## 📊 Outputs à Coller

Après avoir exécuté les commandes, collez-moi ces outputs:

1. **Git status:**
   ```bash
   git status
   ```

2. **Derniers commits:**
   ```bash
   git log --oneline -5
   git log origin/main --oneline -5
   ```

3. **Service ECS:**
   ```bash
   aws ecs describe-services --cluster vancelian-dev-api-cluster --services ganopa-dev-bot-svc --region me-central-1
   ```

4. **Image URI de la task:**
   ```bash
   # (commande complète ci-dessus)
   ```

5. **Logs CloudWatch (dernières 20 lignes):**
   ```bash
   aws logs tail /aws/ecs/ganopa-dev-bot --region me-central-1 --since 30m --format short | tail -20
   ```

6. **Test webhook:**
   ```bash
   curl -X GET https://api.maisonganopa.com/telegram/webhook
   ```

---

## 🔍 Analyse des Résultats

### Si vous voyez "✅ Reçu:" au lieu de "VERSION-TEST-123"

**Causes possibles:**
1. ❌ L'ancienne image tourne encore (vérifier IMAGE_URI vs GITHUB_SHA)
2. ❌ Le mauvais service est déployé (vérifier le nom du service)
3. ❌ Le mode signature test n'est pas activé (`BOT_SIGNATURE_TEST=1`)
4. ❌ Le code n'a pas été déployé (vérifier le workflow GitHub Actions)

### Si vous ne voyez pas `ganopa_bot_started` dans les logs

**Causes possibles:**
1. ❌ Le service ne démarre pas (vérifier les logs ECS pour erreurs)
2. ❌ Mauvais log group (vérifier le nom exact)
3. ❌ Le service n'a pas été redémarré après le déploiement

### Si l'IMAGE_URI ne correspond pas au GITHUB_SHA

**Causes possibles:**
1. ❌ Le workflow GitHub Actions n'a pas tourné
2. ❌ Le workflow a échoué (vérifier GitHub Actions)
3. ❌ Le service ECS n'a pas été mis à jour (forcer un nouveau déploiement)

---

## 🚀 Déploiement via GitHub Actions

Si l'image ne correspond pas:

1. Aller sur: https://github.com/geniusga-vancelian/vancelian-app/actions
2. Workflow: **"Deploy Ganopa Bot (ECS Fargate)"**
3. **Run workflow** → Environnement: `dev`
4. Attendre la fin du workflow
5. Vérifier à nouveau l'IMAGE_URI

---

## ⚡ Commandes Rapides (Copier-Coller)

```bash
# 1. État Git
cd /Users/gael/Library/CloudStorage/OneDrive-Vancelian/Documents/vancelian-app && git status && echo "---" && git log --oneline -3

# 2. Service ECS
aws ecs describe-services --cluster vancelian-dev-api-cluster --services ganopa-dev-bot-svc --region me-central-1 --query "services[0].{name:serviceName,status:status,taskDef:taskDefinition}" --output json

# 3. Image déployée
TASK_ARN=$(aws ecs list-tasks --cluster vancelian-dev-api-cluster --service-name ganopa-dev-bot-svc --desired-status RUNNING --region me-central-1 --query "taskArns[0]" --output text) && aws ecs describe-tasks --cluster vancelian-dev-api-cluster --tasks $TASK_ARN --region me-central-1 --query "tasks[0].containers[?name=='ganopa-bot'].image" --output text

# 4. Logs récents
aws logs tail /aws/ecs/ganopa-dev-bot --region me-central-1 --since 30m --format short | grep -E "ganopa_bot_started|signature_test|BOT_BUILD_ID" | tail -10

# 5. Test webhook
curl -s https://api.maisonganopa.com/telegram/webhook | jq .
```


