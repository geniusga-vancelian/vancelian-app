# 🔍 Debug: Bot Échoit Encore

## État Actuel

- ✅ Workflow GitHub Actions réussi
- ✅ Image Docker construite avec le bon commit (`ab7be15...`)
- ❌ Bot échoit toujours

## 🎯 Vérifications Critiques

### 1. Vérifier l'IMAGE URI dans ECS (PRIORITÉ 1)

**Dans AWS Console → ECS → Services → `ganopa-dev-bot-svc`:**

1. **Cliquer sur une task RUNNING**
2. **Containers → `ganopa-bot`**
3. **Voir IMAGE URI**

**Question:** Quel tag voyez-vous ?
- `ab7be15423df39f3659600146bb7d8e696afcd73` → ✅ Nouvelle image
- `df1aeda0c420874e535f2bb538cbb643b7d48cc3` → ❌ Ancienne image (le service n'a pas été mis à jour)

**Si c'est l'ancienne image:**
- Le workflow a réussi mais le service ECS n'a pas été mis à jour
- Solution: Forcer un nouveau déploiement manuellement

### 2. Vérifier les Logs CloudWatch (PRIORITÉ 2)

**Dans CloudWatch → `/ecs/ganopa-dev-bot-task`:**

**Après avoir envoyé un message Telegram, chercher:**

#### A) `telegram_update_received`
- **Présent ?** → Le webhook arrive
- **Absent ?** → Le webhook ne pointe pas vers le bon service

#### B) `telegram_message_processing`
- **Présent ?** → Le message est traité
- **Absent ?** → Exception avant cette ligne

#### C) `openai_request_start`
- **Présent ?** → OpenAI est appelé (le nouveau code tourne)
- **Absent ?** → Le code n'arrive jamais à cette ligne (problème)

#### D) `telegram_update_processing_failed`
- **Présent ?** → Exception catchée, voir l'erreur
- **Absent ?** → Pas d'exception catchée

### 3. Vérifier le Code dans l'Image (PRIORITÉ 3)

**Si l'IMAGE URI est correcte mais le bot échoit encore:**

Le code dans l'image pourrait être incorrect. Vérifier:

**Option A: Via ECS Exec (si activé)**
```bash
aws ecs execute-command \
  --cluster vancelian-dev-api-cluster \
  --task <TASK_ID> \
  --container ganopa-bot \
  --command "/bin/sh" \
  --interactive
```

Puis dans le container:
```bash
grep -n "openai_request_start" app/main.py
grep -n "✅ Reçu" app/main.py
```

**Option B: Pull l'Image et Vérifier**
```bash
# Login à ECR
aws ecr get-login-password --region me-central-1 | \
  docker login --username AWS --password-stdin \
  411714852748.dkr.ecr.me-central-1.amazonaws.com

# Pull l'image
docker pull 411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:ab7be15423df39f3659600146bb7d8e696afcd73

# Vérifier le code
docker run --rm 411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:ab7be15423df39f3659600146bb7d8e696afcd73 \
  grep -n "✅ Reçu" app/main.py

# Doit retourner: rien (pas de résultat)

docker run --rm 411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:ab7be15423df39f3659600146bb7d8e696afcd73 \
  grep -n "openai_request_start" app/main.py

# Doit retourner: une ligne avec "openai_request_start"
```

### 4. Vérifier que le Service a Redémarré

**Dans AWS Console → ECS → Services → `ganopa-dev-bot-svc`:**

1. **Events tab**
2. **Voir les événements récents:**
   - "Service updated" → Le service a été mis à jour
   - "Task started" → Une nouvelle task a démarré
   - "Task stopped" → L'ancienne task a été arrêtée

**Si vous ne voyez pas ces événements:**
- Le service n'a pas été mis à jour
- Solution: Forcer un nouveau déploiement

## 🔧 Solutions

### Solution 1: Forcer un Nouveau Déploiement ECS

**Si l'IMAGE URI est incorrecte:**

1. **ECS → Services → `ganopa-dev-bot-svc`**
2. **Update service**
3. **Task Definition:** Sélectionner la dernière révision
4. **Vérifier l'IMAGE URI** dans la Task Definition:
   - Doit être: `...ganopa-bot:ab7be15423df39f3659600146bb7d8e696afcd73`
5. **Si incorrect:** Modifier manuellement l'IMAGE URI
6. **Enregistrer nouvelle révision**
7. **Update service** → Sélectionner nouvelle révision
8. ✅ **Force new deployment**
9. Attendre stabilisation (2-3 minutes)

### Solution 2: Vérifier le Code dans l'Image

**Si l'IMAGE URI est correcte mais le bot échoit encore:**

1. Pull l'image et vérifier le code (voir Option B ci-dessus)
2. Si le code contient encore "✅ Reçu":
   - L'image n'a pas été construite avec le bon code
   - Vérifier le workflow GitHub Actions (logs du build)
3. Si le code est correct:
   - Le problème est ailleurs (probablement exception silencieuse)

### Solution 3: Vérifier les Logs pour les Erreurs

**Si `openai_request_start` n'apparaît jamais:**

1. Chercher `telegram_update_processing_failed` dans les logs
2. Chercher `ERROR` ou `Exception` dans les logs
3. Voir l'erreur exacte et la corriger

## 🚨 Action Immédiate

**Répondez à ces questions:**

1. **Quel IMAGE URI voyez-vous dans ECS ?**
   - `ab7be15...` ou `df1aeda...` ?

2. **Voyez-vous `openai_request_start` dans les logs CloudWatch quand vous envoyez un message ?**
   - Oui → Le code tourne, le problème est ailleurs
   - Non → Le code n'arrive jamais à cette ligne

3. **Voyez-vous `telegram_update_processing_failed` dans les logs ?**
   - Oui → Voir l'erreur exacte
   - Non → Pas d'exception catchée

**Avec ces réponses, je pourrai identifier le problème exact.**

