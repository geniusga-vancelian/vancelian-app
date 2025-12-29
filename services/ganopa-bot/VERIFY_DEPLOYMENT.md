# ✅ Vérification du Déploiement

## État du Workflow

✅ **Build réussi** - L'image Docker a été construite et poussée vers ECR
✅ **Tag correct** - L'image est taguée avec `ab7be15423df39f3659600146bb7d8e696afcd73`
✅ **Fichiers présents** - Tous les fichiers Python sont dans l'image

## 🎯 Vérifications à Faire

### 1. Vérifier que le Workflow est Complet

**Dans GitHub Actions:**

1. Vérifier que toutes les étapes sont vertes:
   - ✅ Build & push Docker image
   - ✅ Fetch current task definition ARN
   - ✅ Download task definition JSON
   - ✅ Patch task definition image
   - ✅ Register new task definition revision
   - ✅ Update ECS service
   - ✅ Wait for service to stabilize

**Si toutes les étapes sont vertes:**
- ✅ Le déploiement est complet
- L'image devrait être déployée dans ECS

### 2. Vérifier l'IMAGE URI dans ECS

**Dans AWS Console → ECS → Services → `ganopa-dev-bot-svc`:**

1. **Cliquer sur une task RUNNING**
2. **Containers → `ganopa-bot`**
3. **Voir IMAGE URI**

**Attendu:**
```
411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:ab7be15423df39f3659600146bb7d8e696afcd73
```

**Si vous voyez ce tag:**
- ✅ La nouvelle image est déployée

**Si vous voyez encore `df1aeda...`:**
- ❌ Le service n'a pas été mis à jour
- Solution: Forcer un nouveau déploiement manuellement

### 3. Vérifier les Logs CloudWatch

**Dans CloudWatch → `/ecs/ganopa-dev-bot-task`:**

Chercher les logs récents (dernières 10 minutes):

#### ✅ Log de Démarrage
```
[INFO] ganopa-bot: ganopa_bot_started {
  "bot_build_id": "build-YYYYMMDD-HHMMSS",
  ...
}
```

**Si présent avec un timestamp récent:**
- ✅ Le nouveau code tourne

#### ✅ Test du Bot

**Envoyer un message Telegram**

**Attendu:**
- ✅ Réponse AI générée (pas d'écho)
- ✅ Logs montrent `openai_request_start`
- ✅ Logs montrent `openai_request_done`

### 4. Test de l'Endpoint /version

```bash
curl https://api.maisonganopa.com/version
```

**Attendu:**
```json
{
  "service": "ganopa-bot",
  "bot_build_id": "build-YYYYMMDD-HHMMSS",
  "git_sha": "c78b569",
  ...
}
```

**Si vous voyez un `bot_build_id` récent:**
- ✅ Le nouveau code tourne

## 🚨 Si l'Image n'est Pas Déployée

**Si l'IMAGE URI dans ECS montre encore `df1aeda...`:**

1. **Vérifier que le workflow est complet:**
   - Toutes les étapes doivent être vertes
   - L'étape "Wait for service to stabilize" doit être complète

2. **Forcer un nouveau déploiement manuellement:**
   - ECS → Services → `ganopa-dev-bot-svc`
   - Update service
   - Sélectionner la dernière révision de la Task Definition
   - ✅ **Force new deployment**
   - Attendre stabilisation (2-3 minutes)

3. **Vérifier les événements ECS:**
   - ECS → Services → `ganopa-dev-bot-svc`
   - Events tab
   - Voir s'il y a des erreurs de déploiement

## 📊 Checklist Finale

- [ ] Workflow GitHub Actions complet (toutes les étapes vertes)
- [ ] IMAGE URI dans ECS = `...ganopa-bot:ab7be15...`
- [ ] Logs CloudWatch montrent `ganopa_bot_started` récent
- [ ] Test du bot: réponse AI (pas d'écho)
- [ ] Logs montrent `openai_request_start` et `openai_request_done`

## 🎯 Action Immédiate

**Vérifiez l'IMAGE URI dans ECS maintenant:**

1. AWS Console → ECS → Services → `ganopa-dev-bot-svc`
2. Tasks → Cliquer sur task RUNNING
3. Containers → Voir IMAGE URI
4. **Comparer avec:** `ab7be15423df39f3659600146bb7d8e696afcd73`

**Si c'est le même tag:**
- ✅ Le déploiement est réussi !
- Testez le bot pour confirmer qu'il ne fait plus d'écho

**Si c'est un autre tag:**
- Le service n'a pas été mis à jour
- Forcer un nouveau déploiement (voir ci-dessus)

