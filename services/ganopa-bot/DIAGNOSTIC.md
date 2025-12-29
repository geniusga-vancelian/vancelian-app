# Diagnostic: Bot qui échoit les messages

## 🔍 Problème

Le bot Telegram répond "✅ Reçu:" au lieu d'utiliser OpenAI, malgré les modifications du code.

## 🎯 Causes Possibles

1. **Ancienne image Docker déployée** - Le code modifié n'est pas dans l'image ECR
2. **Mauvais service ECS** - Le déploiement va vers le mauvais service
3. **Service ECS non mis à jour** - L'ancienne task tourne encore
4. **Cache Docker** - Le build utilise un cache avec l'ancien code
5. **Workflow non déclenché** - "Deploy Ganopa Bot" n'a pas tourné

## 📋 Checklist de Diagnostic

### Étape 1: Vérifier les Workflows GitHub Actions

1. Aller sur: https://github.com/geniusga-vancelian/vancelian-app/actions
2. Chercher "Deploy Ganopa Bot (ECS Fargate)"
3. Vérifier:
   - ✅ A-t-il tourné après le commit `aa101be` ou `b910495`?
   - ✅ A-t-il réussi?
   - ✅ Quelle image a été poussée vers ECR?

**Si le workflow n'a PAS tourné:**
→ Le déclenchement automatique ne fonctionne pas
→ Solution: Déclencher manuellement le workflow

### Étape 2: Vérifier l'Image ECR Déployée

**Via AWS Console:**
1. ECS → Clusters → `vancelian-dev-api-cluster`
2. Services → `ganopa-dev-bot-svc` (ou nom similaire)
3. Tasks → Cliquer sur une task RUNNING
4. Containers → Voir l'IMAGE URI
5. Extraire le tag (après `:`)
6. Comparer avec: `git rev-parse HEAD` (doit être `aa101be` ou `b910495`)

**Si l'IMAGE TAG ne correspond pas:**
→ L'ancienne image tourne encore
→ Solution: Forcer un nouveau déploiement

### Étape 3: Vérifier les Logs CloudWatch

**Chercher dans `/aws/ecs/ganopa-dev-bot`:**

1. **Log `ganopa_bot_started`:**
   ```
   [INFO] ganopa-bot: ganopa_bot_started {
     "bot_build_id": "build-YYYYMMDD-HHMMSS",
     ...
   }
   ```
   - Si absent → L'ancienne version tourne
   - Si présent → Vérifier le `bot_build_id` (doit être récent)

2. **Log `openai_request_start`:**
   ```
   [INFO] ganopa-bot: openai_request_start {
     "chat_id": ...,
     "text_preview": "..."
   }
   ```
   - Si absent → OpenAI n'est jamais appelé
   - Si présent → OpenAI est appelé mais peut échouer

3. **Log `signature_test_response`:**
   - Si présent → Le mode test est activé (normal)

**Si vous voyez `telegram_message_processing` mais PAS `openai_request_start`:**
→ Le code ne passe pas par `call_openai()`
→ Possible: ancien code ou exception silencieuse

### Étape 4: Vérifier le Service ECS

**Vérifier que le bon service est actif:**
- Service attendu: `ganopa-dev-bot-svc`
- Cluster: `vancelian-dev-api-cluster`
- Status: RUNNING
- Desired count: 1
- Running count: 1

**Si le service n'existe pas ou est STOPPED:**
→ Le service n'est pas déployé
→ Solution: Vérifier la Task Definition et redémarrer

### Étape 5: Test Direct avec Signature Mode

**Activer le mode signature test:**
1. ECS → Task Definition → `ganopa-dev-bot-svc` (dernière révision)
2. Container `ganopa-bot` → Environment variables
3. Ajouter: `BOT_SIGNATURE_TEST=1`
4. Enregistrer nouvelle révision
5. Mettre à jour le service avec la nouvelle révision
6. Attendre stabilisation
7. Envoyer message Telegram

**Attendu:** `✅ VERSION-TEST-123 | build-YYYYMMDD-HHMMSS`

**Si vous ne voyez PAS cette réponse:**
→ Le code déployé n'est pas le bon
→ Solution: Vérifier le build Docker et l'image ECR

## 🔧 Solutions par Scénario

### Scénario A: Workflow n'a pas tourné

**Symptômes:**
- Pas de workflow "Deploy Ganopa Bot" après les commits
- L'image ECR n'a pas été mise à jour

**Solution:**
1. Déclencher manuellement "Deploy Ganopa Bot" via GitHub Actions
2. Vérifier que le workflow se déclenche bien sur push (vérifier les `paths`)

### Scénario B: Image ECR incorrecte

**Symptômes:**
- Le workflow a tourné mais l'IMAGE TAG ne correspond pas au commit

**Solution:**
1. Vérifier le build Docker dans les logs GitHub Actions
2. Vérifier que `docker build` utilise bien `services/ganopa-bot/` comme contexte
3. Vérifier que `COPY app ./app` copie bien les fichiers modifiés
4. Forcer un rebuild sans cache: `docker build --no-cache ...`

### Scénario C: Service ECS non mis à jour

**Symptômes:**
- L'image ECR est correcte mais le service ECS utilise encore l'ancienne

**Solution:**
1. Forcer un nouveau déploiement:
   ```bash
   aws ecs update-service \
     --cluster vancelian-dev-api-cluster \
     --service ganopa-dev-bot-svc \
     --region me-central-1 \
     --force-new-deployment
   ```
2. Attendre la stabilisation
3. Vérifier les nouvelles tasks

### Scénario D: Cache Docker

**Symptômes:**
- Le build réussit mais l'ancien code est dans l'image

**Solution:**
1. Modifier le workflow pour désactiver le cache:
   ```yaml
   docker build --no-cache -t "$IMAGE_URI" ...
   ```
2. Ou forcer le rebuild de la couche `COPY app ./app`

### Scénario E: Mauvais Service

**Symptômes:**
- Le déploiement va vers `vancelian-dev-api-svc` au lieu de `ganopa-dev-bot-svc`

**Solution:**
1. Vérifier le workflow "Deploy Ganopa Bot"
2. Vérifier que le SERVICE est bien `ganopa-dev-bot-svc`
3. Vérifier que le CLUSTER est bien `vancelian-dev-api-cluster`

## 🚨 Action Immédiate

**Pour prouver quelle version tourne:**

1. **Activer le mode signature test:**
   - Task Definition → Ajouter `BOT_SIGNATURE_TEST=1`
   - Redémarrer le service

2. **Envoyer un message Telegram**

3. **Si réponse = `✅ VERSION-TEST-123 | build-...`:**
   - ✅ Le nouveau code tourne
   - Le problème est ailleurs (OpenAI API key, etc.)

4. **Si réponse = `✅ Reçu: ...`:**
   - ❌ L'ancien code tourne encore
   - Vérifier l'image ECR et forcer un nouveau déploiement

## 📊 Commandes de Vérification Rapide

```bash
# 1. Commit actuel
git rev-parse HEAD

# 2. Dernier workflow Ganopa Bot (via GitHub API ou UI)
# Vérifier dans GitHub Actions

# 3. Image déployée (si AWS CLI configuré)
aws ecs describe-services \
  --cluster vancelian-dev-api-cluster \
  --services ganopa-dev-bot-svc \
  --region me-central-1 \
  --query "services[0].taskDefinition" \
  --output text

# 4. Logs récents
aws logs tail /aws/ecs/ganopa-dev-bot \
  --region me-central-1 \
  --since 1h \
  --filter-pattern "ganopa_bot_started" \
  --format short
```

## ✅ Prochaine Action

**Exécutez ces commandes et collez-moi les outputs:**

1. `git log --oneline -3` (vérifier les commits)
2. Vérifier dans GitHub Actions si "Deploy Ganopa Bot" a tourné après `b910495`
3. Si possible, vérifier l'IMAGE URI de la task ECS en cours

Ensuite, on pourra identifier précisément où est le problème.

