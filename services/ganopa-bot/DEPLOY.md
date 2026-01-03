# Guide de Déploiement - Ganopa Bot

## État Actuel

✅ **Rebase terminé** - Les corrections sont dans le commit `0ebd4c2`
✅ **Conflits résolus** - Aucun marqueur de conflit dans le code
✅ **Code prêt** - `main.py` et `config.py` sont production-ready

## Prochaines Étapes

### 1. Vérifier les Changements

```bash
# Voir les fichiers modifiés
git status

# Voir les différences
git diff HEAD~1 services/ganopa-bot/app/main.py
git diff HEAD~1 services/ganopa-bot/app/config.py

# Vérifier qu'il n'y a plus de conflits
grep -r "<<<<<<\|======\|>>>>>>" services/ganopa-bot/app/
```

### 2. Pousser vers GitHub

```bash
# Vérifier que vous êtes sur la bonne branche
git branch

# Pousser vers origin/main
git push origin main
```

**Note:** Si vous avez des commits locaux non poussés, utilisez:
```bash
git push origin main --force-with-lease
```

⚠️ **Attention:** `--force-with-lease` est plus sûr que `--force` car il vérifie que personne d'autre n'a poussé entre-temps.

### 3. Déployer via GitHub Actions

#### Option A: Via l'interface GitHub

1. Aller sur: `https://github.com/geniusga-vancelian/vancelian-app/actions`
2. Sélectionner le workflow: **"Deploy Ganopa Bot (ECS Fargate)"**
3. Cliquer sur **"Run workflow"**
4. Sélectionner l'environnement: `dev`, `staging`, ou `prod`
5. Cliquer sur **"Run workflow"**

#### Option B: Via GitHub CLI (si installé)

```bash
gh workflow run "Deploy Ganopa Bot (ECS Fargate).yml" \
  -f target_env=dev
```

### 4. Surveiller le Déploiement

#### Dans GitHub Actions

1. Aller sur la page Actions
2. Cliquer sur le workflow en cours d'exécution
3. Surveiller les étapes:
   - ✅ Checkout
   - ✅ Configure AWS credentials
   - ✅ Build & push Docker image
   - ✅ Update ECS service
   - ✅ Wait for service to stabilize

#### Dans AWS CloudWatch

1. Aller sur AWS Console → CloudWatch → Log Groups
2. Chercher le log group: `/aws/ecs/ganopa-{env}-bot` (ex: `/aws/ecs/ganopa-dev-bot`)
3. Vérifier les logs récents pour:
   ```
   [INFO] ganopa-bot: ganopa_bot_started
   ```

### 5. Vérifier que le Service Fonctionne

#### Health Check

```bash
# Récupérer l'URL ALB depuis ECS
# Puis tester:
curl https://<ALB_DNS>/health
```

Réponse attendue:
```json
{
  "status": "ok",
  "service": "ganopa-bot",
  "ts": "2025-01-XX..."
}
```

#### Test Telegram

1. Envoyer un message au bot Telegram
2. Vérifier les logs CloudWatch pour:
   - `telegram_update_received`
   - `openai_call_start`
   - `openai_call_success`
   - `telegram_send_success`

## Checklist de Déploiement

- [ ] Code poussé vers GitHub (`git push origin main`)
- [ ] Workflow GitHub Actions déclenché
- [ ] Build Docker réussi
- [ ] Image poussée vers ECR
- [ ] Task Definition mise à jour
- [ ] Service ECS déployé
- [ ] Service stabilisé (pas d'erreurs)
- [ ] Log `ganopa_bot_started` visible dans CloudWatch
- [ ] Health check répond 200 OK
- [ ] Test Telegram: bot répond avec IA (pas d'écho)

## Variables d'Environnement Requises (ECS Task Definition)

Assurez-vous que ces variables sont configurées dans la Task Definition ECS:

**Requis:**
- `TELEGRAM_BOT_TOKEN` - Token du bot Telegram
- `OPENAI_API_KEY` - Clé API OpenAI

**Optionnel:**
- `OPENAI_MODEL` - Modèle OpenAI (défaut: `gpt-4o-mini`)
- `WEBHOOK_SECRET` - Secret pour vérifier les webhooks Telegram
- `PORT` - Port du serveur (défaut: `8000`)

## Dépannage

### Le workflow échoue au build

```bash
# Vérifier les logs GitHub Actions
# Erreur probable: dépendance manquante dans requirements.txt
```

### Le service ne démarre pas

```bash
# Vérifier les logs ECS
aws ecs describe-tasks \
  --cluster vancelian-dev-api-cluster \
  --tasks <TASK_ARN> \
  --region me-central-1

# Vérifier les logs CloudWatch
# Chercher: ImportError, SyntaxError, RuntimeError
```

### Le bot ne répond pas

1. Vérifier que le webhook Telegram est configuré:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
   ```

2. Vérifier les logs CloudWatch:
   - `telegram_update_received` → webhook reçu
   - `openai_call_start` → OpenAI appelé
   - `openai_call_success` → OpenAI a répondu
   - `telegram_send_success` → message envoyé

3. Si `telegram_update_received` mais pas `openai_call_start`:
   - Problème dans `process_telegram_update()`
   - Vérifier les logs d'erreur

### Le bot échoit encore les messages

1. Vérifier que la bonne image est déployée:
   ```bash
   aws ecs describe-services \
     --cluster vancelian-dev-api-cluster \
     --services ganopa-dev-bot-svc \
     --region me-central-1 \
     --query "services[0].taskDefinition"
   ```

2. Vérifier le hash Git de l'image:
   - L'image devrait être taggée avec `${GITHUB_SHA}`
   - Comparer avec le commit déployé

3. Vérifier les logs pour `ganopa_bot_started`:
   - Si absent, l'ancienne version tourne peut-être encore

## Commandes Utiles

### Vérifier l'état du service ECS

```bash
aws ecs describe-services \
  --cluster vancelian-dev-api-cluster \
  --services ganopa-dev-bot-svc \
  --region me-central-1 \
  --query "services[0].{status:status,desired:desiredCount,running:runningCount,pending:pendingCount}"
```

### Voir les logs récents

```bash
aws logs tail /aws/ecs/ganopa-dev-bot \
  --region me-central-1 \
  --follow \
  --since 10m
```

### Redémarrer le service (force new deployment)

```bash
aws ecs update-service \
  --cluster vancelian-dev-api-cluster \
  --service ganopa-dev-bot-svc \
  --region me-central-1 \
  --force-new-deployment
```

## Support

En cas de problème:
1. Vérifier les logs CloudWatch
2. Vérifier les logs GitHub Actions
3. Vérifier l'état du service ECS
4. Consulter `FIX_SUMMARY.md` pour les détails techniques


