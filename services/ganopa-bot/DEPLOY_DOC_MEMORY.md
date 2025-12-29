# Déploiement Doc-Memory Mode - Checklist

## TL;DR

Le workflow GitHub Actions devrait **automatiquement** déployer les changements. Aucune action manuelle dans AWS n'est normalement requise. Mais vérifiez ces points.

---

## ✅ Ce qui est Automatique (GitHub Actions)

Le workflow `.github/workflows/deploy-ganopa-bot.yml` fait automatiquement :

1. ✅ Build l'image Docker (avec `docs/` copié)
2. ✅ Push vers ECR (tag = `GITHUB_SHA`)
3. ✅ Update la Task Definition (nouvelle image)
4. ✅ Update le service ECS avec `--force-new-deployment`
5. ✅ Attend que le service se stabilise

**Aucune action manuelle requise** si le workflow réussit.

---

## 🔍 Vérifications à Faire (si ça ne marche pas)

### 1. Vérifier que le Workflow s'est Déclenché

**GitHub Actions:**
- Aller sur: https://github.com/geniusga-vancelian/vancelian-app/actions
- Chercher "Deploy Ganopa Bot (ECS Fargate)"
- Vérifier que le dernier workflow a réussi (✅ vert)

**Si le workflow n'a PAS tourné:**
- Vérifier que vous avez push sur `main`
- Vérifier que les fichiers modifiés sont dans `services/ganopa-bot/**`
- Déclencher manuellement: Actions → "Deploy Ganopa Bot" → Run workflow

---

### 2. Vérifier que l'Image Docker Contient la Doc

**Dans le workflow GitHub Actions, chercher:**
```
✅ Docs directory is present
```

**Si vous voyez:**
```
⚠️  Docs directory not found (will use fallback)
```
→ La doc n'est pas dans l'image → Vérifier le Dockerfile

---

### 3. Vérifier les Variables d'Environnement (Optionnel)

**Les variables suivantes ont des defaults, donc pas obligatoires:**
- `DOCS_DIR` (default: `/app/docs`) - Pas besoin de l'ajouter
- `DOCS_REFRESH_SECONDS` (default: `300`) - Pas besoin de l'ajouter
- `MEMORY_TTL_SECONDS` (default: `1800`) - Pas besoin de l'ajouter
- `MEMORY_MAX_MESSAGES` (default: `20`) - Pas besoin de l'ajouter

**Variables REQUISES (déjà configurées normalement):**
- `TELEGRAM_BOT_TOKEN` ✅
- `OPENAI_API_KEY` ✅
- `WEBHOOK_SECRET` (optionnel)
- `OPENAI_MODEL` (default: `gpt-4o-mini`)
- `PORT` (default: `8000`)

**Où vérifier:**
- AWS Console → ECS → Task Definitions → `ganopa-bot` (dernière révision)
- Container `ganopa-bot` → Environment variables

**Action requise:** Aucune, sauf si vous voulez changer les defaults.

---

### 4. Vérifier que le Service ECS a été Mis à Jour

**Via AWS Console:**
1. ECS → Clusters → `vancelian-dev-api-cluster`
2. Services → `ganopa-dev-bot-svc`
3. Onglet "Déploiements"
4. Vérifier que la Task Definition revision est récente
5. Vérifier que `rolloutState` = `COMPLETED`

**Via CLI:**
```bash
aws ecs describe-services \
  --region me-central-1 \
  --cluster vancelian-dev-api-cluster \
  --services ganopa-dev-bot-svc \
  --query "services[0].{taskDef:taskDefinition,deployments:deployments[0].{status:status,rolloutState:rolloutState}}" \
  --output json
```

**Si le service n'a pas été mis à jour:**
- Le workflow a peut-être échoué
- Vérifier les logs GitHub Actions
- Forcer un nouveau déploiement manuellement si nécessaire

---

### 5. Vérifier que la Doc est Chargée

**Via Endpoint `/_meta`:**
```bash
curl -s https://api.maisonganopa.com/_meta | jq '{docs_hash, docs_loaded, memory_enabled}'
```

**Attendu:**
```json
{
  "docs_hash": "a1b2c3d4e5f6",  // Pas "no-docs"
  "docs_loaded": true,
  "memory_enabled": true
}
```

**Si `docs_hash = "no-docs"`:**
→ La doc n'est pas trouvée dans le container
→ Vérifier que `docs/` est bien copié dans l'image Docker

---

### 6. Vérifier les Logs CloudWatch

**Chercher ces logs pour confirmer que la doc est utilisée:**
```bash
aws logs tail /ecs/ganopa-dev-bot-task \
  --region me-central-1 \
  --since 10m \
  --format short \
  --filter-pattern "docs_injected OR docs_loaded OR format_reply_prefix"
```

**Logs attendus:**
- `docs_injected`: Confirme que la doc est injectée dans le system prompt
- `docs_loaded`: Confirme que la doc est chargée (hash + length)
- `format_reply_prefix`: Montre le préfixe créé (`(doc ok) ` ou `(doc non disponible) `)

**Si ces logs n'apparaissent pas:**
→ Le code n'est peut-être pas encore déployé
→ Vérifier la version déployée via `/_meta`

---

## 🚨 Actions Manuelles (si nécessaire)

### Forcer un Nouveau Déploiement

**Si le workflow a réussi mais le service n'a pas changé:**

**Via AWS Console:**
1. ECS → Services → `ganopa-dev-bot-svc`
2. Update service
3. ✅ Cocher "Force new deployment"
4. Update service

**Via CLI:**
```bash
aws ecs update-service \
  --region me-central-1 \
  --cluster vancelian-dev-api-cluster \
  --service ganopa-dev-bot-svc \
  --force-new-deployment
```

---

### Vérifier que l'Image Docker Contient les Fichiers

**Si vous suspectez que les fichiers ne sont pas dans l'image:**

```bash
# Récupérer l'IMAGE_URI depuis ECR ou le workflow
IMAGE_URI="411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:34a9e97"

# Vérifier les fichiers
docker run --rm "$IMAGE_URI" ls -la app/
docker run --rm "$IMAGE_URI" test -f app/agent_service.py && echo "✅ agent_service.py present"
docker run --rm "$IMAGE_URI" test -f app/doc_store.py && echo "✅ doc_store.py present"
docker run --rm "$IMAGE_URI" test -f app/memory_store.py && echo "✅ memory_store.py present"
docker run --rm "$IMAGE_URI" test -d docs && echo "✅ docs directory present"
docker run --rm "$IMAGE_URI" ls -la docs/ | head -5
```

---

## ✅ Checklist Post-Déploiement

Après un déploiement, vérifier:

- [ ] Workflow GitHub Actions: ✅ Success
- [ ] `/_meta` endpoint: `docs_loaded: true`, `docs_hash` != "no-docs"
- [ ] Logs CloudWatch: `docs_injected` apparaît
- [ ] Message Telegram: Commence par "(doc ok) "
- [ ] Logs CloudWatch: `format_reply_prefix` avec `doc_prefix: "(doc ok) "`

---

## 🐛 Si ça ne Marche Toujours Pas

1. **Vérifier la version déployée:**
   ```bash
   curl -s https://api.maisonganopa.com/_meta | jq '.version'
   ```
   Comparer avec le dernier commit: `git log --oneline -1`

2. **Vérifier les logs CloudWatch pour erreurs:**
   ```bash
   aws logs tail /ecs/ganopa-dev-bot-task \
     --region me-central-1 \
     --since 10m \
     --format short \
     --filter-pattern "ERROR OR Exception OR Traceback"
   ```

3. **Vérifier que le service ECS utilise la bonne Task Definition:**
   ```bash
   aws ecs describe-services \
     --region me-central-1 \
     --cluster vancelian-dev-api-cluster \
     --services ganopa-dev-bot-svc \
     --query "services[0].taskDefinition" \
     --output text
   ```

4. **Vérifier que l'image dans la Task Definition est récente:**
   ```bash
   TASKDEF_ARN=$(aws ecs describe-services \
     --region me-central-1 \
     --cluster vancelian-dev-api-cluster \
     --services ganopa-dev-bot-svc \
     --query "services[0].taskDefinition" \
     --output text)
   
   aws ecs describe-task-definition \
     --region me-central-1 \
     --task-definition "$TASKDEF_ARN" \
     --query "taskDefinition.containerDefinitions[0].image" \
     --output text
   ```

---

**Dernière mise à jour:** 2025-12-30

