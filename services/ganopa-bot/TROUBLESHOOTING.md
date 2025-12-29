# Troubleshooting: Bot qui échoit les messages

## 🎯 Diagnostic Rapide

### Question 1: Le workflow "Deploy Ganopa Bot" a-t-il tourné?

**Vérifier:**
1. GitHub → Actions → "Deploy Ganopa Bot (ECS Fargate)"
2. Chercher un workflow récent (après commit `b910495`)
3. Vérifier qu'il a réussi

**Si NON:**
→ Le code n'a jamais été déployé
→ **Solution:** Déclencher manuellement le workflow

**Si OUI:**
→ Passer à la question 2

### Question 2: Quelle image est déployée dans ECS?

**Vérifier dans AWS Console:**
1. ECS → Clusters → `vancelian-dev-api-cluster`
2. Services → Chercher service avec "ganopa" ou "bot"
3. Tasks → Cliquer sur task RUNNING
4. Containers → Voir IMAGE URI
5. Extraire le tag (après `:`)

**Comparer avec:**
```bash
git rev-parse HEAD
```

**Si différent:**
→ L'ancienne image tourne encore
→ **Solution:** Forcer un nouveau déploiement (voir ci-dessous)

**Si identique:**
→ Passer à la question 3

### Question 3: Les logs CloudWatch montrent-ils `ganopa_bot_started`?

**Vérifier dans CloudWatch:**
- Log group: `/aws/ecs/ganopa-dev-bot` (ou similaire)
- Chercher: `ganopa_bot_started`
- Vérifier le `bot_build_id` (doit être récent)

**Si absent:**
→ L'ancienne version tourne (pas de log de démarrage)
→ **Solution:** Vérifier que le service a redémarré après le déploiement

**Si présent:**
→ Passer à la question 4

### Question 4: Le mode signature test fonctionne-t-il?

**Activer le mode test:**
1. ECS → Task Definition → Dernière révision de `ganopa-dev-bot-svc`
2. Container `ganopa-bot` → Environment variables
3. Ajouter: `BOT_SIGNATURE_TEST=1`
4. Enregistrer nouvelle révision
5. Mettre à jour le service
6. Attendre stabilisation
7. Envoyer message Telegram

**Attendu:** `✅ VERSION-TEST-123 | build-YYYYMMDD-HHMMSS`

**Si vous voyez cette réponse:**
→ ✅ Le nouveau code tourne
→ Le problème est ailleurs (OpenAI API key, etc.)

**Si vous voyez "✅ Reçu:":**
→ ❌ L'ancien code tourne encore
→ **Solution:** Vérifier l'image ECR et forcer rebuild

## 🔧 Solutions par Problème

### Problème 1: Workflow n'a pas tourné

**Symptômes:**
- Pas de workflow "Deploy Ganopa Bot" dans GitHub Actions
- L'image ECR n'a pas été mise à jour

**Solution:**
1. Aller sur GitHub Actions
2. "Deploy Ganopa Bot (ECS Fargate)" → "Run workflow"
3. Environnement: `dev`
4. Lancer

### Problème 2: Image ECR incorrecte

**Symptômes:**
- Le workflow a tourné mais l'IMAGE TAG ne correspond pas

**Solution:**
1. Vérifier les logs du workflow (étape "Build & push Docker image")
2. Vérifier que l'image a bien été poussée
3. Le workflow a été modifié pour utiliser `--no-cache` (commit `b910495`)
4. Redéployer si nécessaire

### Problème 3: Service ECS non mis à jour

**Symptômes:**
- L'image ECR est correcte mais le service utilise l'ancienne

**Solution - Via AWS Console:**
1. ECS → Services → `ganopa-dev-bot-svc`
2. "Update service"
3. "Force new deployment" → Cocher
4. "Update service"
5. Attendre stabilisation

**Solution - Via AWS CLI:**
```bash
aws ecs update-service \
  --cluster vancelian-dev-api-cluster \
  --service ganopa-dev-bot-svc \
  --region me-central-1 \
  --force-new-deployment
```

### Problème 4: Cache Docker

**Symptômes:**
- Le build réussit mais l'ancien code est dans l'image

**Solution:**
- ✅ Déjà corrigé: Le workflow utilise maintenant `--no-cache`
- Si le problème persiste, vérifier que le workflow a bien tourné après `b910495`

### Problème 5: Mauvais Service

**Symptômes:**
- Le déploiement va vers `vancelian-dev-api-svc` au lieu de `ganopa-dev-bot-svc`

**Solution:**
- ✅ Déjà corrigé: Le workflow "Deploy Ganopa Bot" déploie vers `ganopa-dev-bot-svc`
- Vérifier que vous utilisez le bon workflow

## 🚀 Action Immédiate Recommandée

### Option A: Forcer un Nouveau Déploiement (Rapide)

1. **Via GitHub Actions:**
   - "Deploy Ganopa Bot (ECS Fargate)" → "Run workflow" → `dev`
   - Attendre la fin
   - Vérifier les logs

2. **Via AWS Console:**
   - ECS → Services → `ganopa-dev-bot-svc`
   - "Update service" → "Force new deployment"
   - Attendre stabilisation

### Option B: Activer le Mode Signature Test (Preuve)

1. **Modifier la Task Definition:**
   - ECS → Task Definitions → `ganopa-dev-bot-svc` (dernière révision)
   - Container `ganopa-bot` → Environment variables
   - Ajouter: `BOT_SIGNATURE_TEST` = `1`
   - Enregistrer nouvelle révision

2. **Mettre à jour le Service:**
   - Services → `ganopa-dev-bot-svc` → "Update service"
   - Task Definition: Sélectionner la nouvelle révision
   - "Force new deployment" → Cocher
   - "Update service"

3. **Tester:**
   - Envoyer message Telegram
   - Attendu: `✅ VERSION-TEST-123 | build-YYYYMMDD-HHMMSS`

4. **Si ça fonctionne:**
   - ✅ Le nouveau code tourne
   - Désactiver le mode test (`BOT_SIGNATURE_TEST=0` ou retirer)
   - Le bot devrait maintenant utiliser OpenAI

## 📊 Checklist Complète

- [ ] Workflow "Deploy Ganopa Bot" a tourné après `b910495`
- [ ] Workflow a réussi (toutes les étapes vertes)
- [ ] Image ECR tag correspond à `git rev-parse HEAD`
- [ ] Service ECS `ganopa-dev-bot-svc` est RUNNING
- [ ] Task Definition utilise la bonne image
- [ ] Logs CloudWatch montrent `ganopa_bot_started` avec `bot_build_id` récent
- [ ] Mode signature test répond `✅ VERSION-TEST-123 | build-...`
- [ ] Mode normal appelle OpenAI (log `openai_request_start`)

## 🆘 Si Rien ne Fonctionne

1. **Vérifier le nom exact du service:**
   ```bash
   # Lister tous les services
   aws ecs list-services --cluster vancelian-dev-api-cluster --region me-central-1
   ```

2. **Vérifier tous les log groups:**
   ```bash
   # Lister tous les log groups ECS
   aws logs describe-log-groups --region me-central-1 --log-group-name-prefix "/aws/ecs/" | grep ganopa
   ```

3. **Vérifier les tasks en cours:**
   ```bash
   # Lister toutes les tasks
   aws ecs list-tasks --cluster vancelian-dev-api-cluster --region me-central-1
   ```

4. **Vérifier les images de toutes les tasks:**
   - Pour chaque task, voir l'IMAGE URI
   - Identifier laquelle correspond au bot Telegram

## 📝 Informations à Me Fournir

Pour que je puisse vous aider, j'ai besoin de:

1. **Commit SHA actuel:**
   ```bash
   git rev-parse HEAD
   ```

2. **Workflow GitHub Actions:**
   - A-t-il tourné après `b910495`?
   - A-t-il réussi?

3. **Image ECR déployée:**
   - IMAGE URI de la task ECS
   - Tag extrait (après `:`)

4. **Logs CloudWatch:**
   - Dernières 20 lignes du log group
   - Chercher `ganopa_bot_started`

5. **Test signature:**
   - Réponse du bot avec `BOT_SIGNATURE_TEST=1`

