# 🔍 Vérifier le Code dans l'Image Docker

## Problème

- ✅ Code dans le repo: Pas de "✅ Reçu"
- ❌ Bot répond: "✅ Reçu: [votre message]"
- ❌ Image déployée: `30c4b5c...`

**Conclusion:** L'image Docker contient probablement encore l'ancien code.

## 🎯 Vérification

### Option 1: Pull et Inspecter l'Image Docker

```bash
# Login à ECR
aws ecr get-login-password --region me-central-1 | \
  docker login --username AWS --password-stdin \
  411714852748.dkr.ecr.me-central-1.amazonaws.com

# Pull l'image
docker pull 411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:30c4b5c7dd4b716e0600ef69a73a986b5eaf7018

# Vérifier le code
docker run --rm 411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:30c4b5c7dd4b716e0600ef69a73a986b5eaf7018 \
  grep -n "✅ Reçu" app/main.py

# Si vous voyez une ligne → L'ancien code est dans l'image
# Si pas de résultat → Le code est correct dans l'image
```

### Option 2: Vérifier le Build GitHub Actions

**Dans GitHub Actions → "Deploy Ganopa Bot" → Dernier workflow:**

1. **Vérifier l'étape "Build & push Docker image"**
2. **Voir les logs:**
   - ✅ "All Python files verified"
   - ✅ "All files verified in Docker image"
3. **Vérifier quel commit a été utilisé:**
   - Doit être `30c4b5c` ou plus récent

**Si le build a utilisé un ancien commit:**
- Le workflow n'a pas récupéré le bon code
- Vérifier le checkout dans le workflow

### Option 3: Rebuild l'Image avec le Dernier Commit

**Si l'image contient l'ancien code:**

1. **Déclencher le workflow "Deploy Ganopa Bot" manuellement:**
   - GitHub Actions → "Deploy Ganopa Bot"
   - "Run workflow" → `dev`
   - Le workflow va build avec le dernier commit (`ad57f04` ou plus récent)

2. **Vérifier que le build utilise le bon commit:**
   - Voir les logs "Git Debug Info"
   - Doit montrer le dernier commit

3. **Attendre que le déploiement se termine**

## 🔧 Solution: Rebuild et Redéployer

**Pour s'assurer que l'image contient le bon code:**

1. **Vérifier le dernier commit:**
   ```bash
   git log -1 --oneline
   ```

2. **Déclencher le workflow "Deploy Ganopa Bot":**
   - GitHub Actions → "Deploy Ganopa Bot"
   - "Run workflow" → `dev`

3. **Vérifier dans les logs du workflow:**
   - "Git Debug Info" → Doit montrer le dernier commit
   - "Image URI" → Doit être taguée avec le dernier commit SHA

4. **Attendre que le déploiement se termine**

5. **Vérifier l'IMAGE URI dans ECS:**
   - Doit correspondre au dernier commit

6. **Tester le bot:**
   - Ne doit plus répondre "✅ Reçu:"

## 🚨 Action Immédiate

**Vérifiez le code dans l'image Docker:**

```bash
docker pull 411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:30c4b5c7dd4b716e0600ef69a73a986b5eaf7018
docker run --rm 411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:30c4b5c7dd4b716e0600ef69a73a986b5eaf7018 \
  grep -n "✅ Reçu" app/main.py
```

**Si vous voyez une ligne:**
- ❌ L'ancien code est dans l'image
- Solution: Rebuild l'image avec le dernier commit

**Si pas de résultat:**
- ✅ Le code est correct dans l'image
- Le problème est ailleurs (peut-être le webhook pointe vers un autre service)

