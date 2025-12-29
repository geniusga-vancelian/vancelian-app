# 🔍 Vérification de l'Image Déployée

## Problème Suspecté

L'image Docker déployée dans ECS ne contient peut-être pas le bon code, ou le code ne passe pas correctement dans l'image.

## 🎯 Vérifications à Faire

### 1. Vérifier l'IMAGE URI dans ECS

**Dans AWS Console → ECS → Services → `ganopa-dev-bot-svc`:**

1. **Cliquer sur une task RUNNING**
2. **Containers → `ganopa-bot`**
3. **Voir IMAGE URI** (ex: `411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:abc123def`)
4. **Extraire le tag** (après `:`, ex: `abc123def`)

**Comparer avec:**
```bash
git rev-parse HEAD
```

**Si différent:**
- ❌ L'ancienne image tourne encore
- Solution: Forcer un nouveau déploiement

### 2. Vérifier les Fichiers dans l'Image Docker

**Option A: Via AWS ECS Exec (si activé)**

```bash
# Récupérer le TASK_ID depuis ECS Console
aws ecs execute-command \
  --cluster vancelian-dev-api-cluster \
  --task <TASK_ID> \
  --container ganopa-bot \
  --command "/bin/sh" \
  --interactive
```

Puis dans le container:
```bash
# Vérifier que les fichiers existent
ls -la app/
cat app/main.py | head -50
grep -n "openai_request_start" app/main.py
```

**Option B: Tester l'Image Localement**

```bash
# Build l'image localement
cd services/ganopa-bot
docker build -t ganopa-bot-test .

# Vérifier les fichiers
docker run --rm ganopa-bot-test ls -la app/
docker run --rm ganopa-bot-test cat app/main.py | head -50
docker run --rm ganopa-bot-test grep -n "openai_request_start" app/main.py
```

### 3. Vérifier le Build dans GitHub Actions

**Dans GitHub Actions → "Deploy Ganopa Bot" → Dernier workflow:**

1. **Vérifier l'étape "Build & push Docker image"**
2. **Voir les logs:**
   - ✅ "All Python files verified"
   - ✅ "All files verified in Docker image"
3. **Vérifier l'IMAGE URI poussée:**
   - Doit correspondre au Git SHA du commit

**Si les vérifications échouent:**
- ❌ Les fichiers ne sont pas dans l'image
- Vérifier le Dockerfile et le contexte de build

### 4. Vérifier le Code dans l'Image ECR

**Option A: Via AWS CLI**

```bash
# Lister les images dans ECR
aws ecr list-images \
  --repository-name ganopa-bot \
  --region me-central-1

# Voir les tags
aws ecr describe-images \
  --repository-name ganopa-bot \
  --region me-central-1 \
  --query 'imageDetails[*].imageTags' \
  --output table
```

**Option B: Pull et Inspecter l'Image**

```bash
# Login à ECR
aws ecr get-login-password --region me-central-1 | \
  docker login --username AWS --password-stdin \
  411714852748.dkr.ecr.me-central-1.amazonaws.com

# Pull l'image déployée (remplacer TAG par le tag de la task ECS)
docker pull 411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:<TAG>

# Inspecter les fichiers
docker run --rm 411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:<TAG> \
  ls -la app/

docker run --rm 411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:<TAG> \
  grep -n "openai_request_start" app/main.py
```

## 🔧 Solutions

### Solution 1: Forcer un Nouveau Build et Déploiement

**Si l'image ne contient pas le bon code:**

1. **Vérifier que tous les fichiers sont commités:**
   ```bash
   git status
   git add -A
   git commit -m "fix: ensure all files are committed"
   git push origin main
   ```

2. **Déclencher manuellement le workflow:**
   - GitHub Actions → "Deploy Ganopa Bot"
   - "Run workflow" → Environnement: `dev`

3. **Vérifier que le build réussit:**
   - Voir les logs "Build & push Docker image"
   - Vérifier que "All files verified in Docker image" apparaît

4. **Forcer un nouveau déploiement ECS:**
   - ECS → Services → `ganopa-dev-bot-svc`
   - Update service
   - ✅ **Force new deployment**
   - Attendre stabilisation

### Solution 2: Vérifier le Dockerfile

**Si les fichiers ne sont pas copiés:**

1. **Vérifier le Dockerfile:**
   ```dockerfile
   COPY app/ ./app/
   ```

2. **Vérifier le contexte de build:**
   - Le workflow utilise: `docker build -f services/ganopa-bot/Dockerfile services/ganopa-bot`
   - Le contexte est `services/ganopa-bot`
   - Donc `COPY app/ ./app/` copie depuis `services/ganopa-bot/app/`

3. **Vérifier que les fichiers existent dans le repo:**
   ```bash
   ls -la services/ganopa-bot/app/
   git ls-files services/ganopa-bot/app/
   ```

### Solution 3: Ajouter des Logs de Debug

**Pour vérifier que le bon code tourne:**

Ajouter dans `main.py` au démarrage:
```python
logger.info("CODE_VERSION_CHECK", extra={
    "git_sha": "25a67cf",  # Remplacer par le commit actuel
    "has_call_openai": "call_openai" in dir(),
    "main_file_path": __file__,
})
```

## 📊 Checklist

- [ ] IMAGE URI dans ECS correspond au Git SHA du dernier commit
- [ ] Les fichiers Python sont présents dans l'image (test local ou ECS Exec)
- [ ] Le code dans l'image contient `openai_request_start` (grep dans l'image)
- [ ] Le build GitHub Actions montre "All files verified in Docker image"
- [ ] Le service ECS a été mis à jour avec la nouvelle image
- [ ] Les logs montrent `ganopa_bot_started` avec un `bot_build_id` récent

## 🚨 Action Immédiate

**Vérifiez l'IMAGE URI dans ECS et comparez avec le Git SHA:**

1. AWS Console → ECS → Services → `ganopa-dev-bot-svc`
2. Tasks → Cliquer sur task RUNNING
3. Containers → Voir IMAGE URI
4. Extraire le tag (après `:`)
5. Comparer avec: `git rev-parse HEAD`

**Si différent:**
- Forcer un nouveau déploiement
- Ou vérifier que le workflow a bien tourné avec le dernier commit

