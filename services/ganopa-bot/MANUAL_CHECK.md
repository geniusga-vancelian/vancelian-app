# 🔍 Vérification Manuelle du Code dans l'Image Docker

## Commandes à Exécuter

### 1. Login à ECR

```bash
aws ecr get-login-password --region me-central-1 | \
  docker login --username AWS --password-stdin \
  411714852748.dkr.ecr.me-central-1.amazonaws.com
```

### 2. Pull l'Image

```bash
docker pull 411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:30c4b5c7dd4b716e0600ef69a73a986b5eaf7018
```

### 3. Vérifier si "✅ Reçu" est Présent

```bash
docker run --rm 411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:30c4b5c7dd4b716e0600ef69a73a986b5eaf7018 \
  grep -n "✅ Reçu" app/main.py
```

**Résultats possibles:**

- **Si vous voyez une ligne** (ex: `123:reply = f"✅ Reçu: {text}"`):
  - ❌ **PROBLÈME:** L'ancien code est dans l'image
  - Solution: Rebuild l'image avec le dernier commit

- **Si pas de résultat:**
  - ✅ Le code est correct dans l'image
  - Le problème est ailleurs (peut-être le webhook pointe vers un autre service)

### 4. Vérifier si "openai_request_start" est Présent

```bash
docker run --rm 411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:30c4b5c7dd4b716e0600ef69a73a986b5eaf7018 \
  grep -n "openai_request_start" app/main.py
```

**Résultats possibles:**

- **Si vous voyez une ligne** (ex: `408:logger.info("openai_request_start",`):
  - ✅ Le nouveau code est présent

- **Si pas de résultat:**
  - ❌ L'ancien code est présent
  - Solution: Rebuild l'image

### 5. Voir le Contenu de process_telegram_update

```bash
docker run --rm 411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:30c4b5c7dd4b716e0600ef69a73a986b5eaf7018 \
  sed -n '/def process_telegram_update/,/^def /p' app/main.py | head -50
```

**Vérifier:**
- Pas de `reply = f"✅ Reçu:`
- Présence de `openai_request_start`
- Présence de `call_openai`

## 📊 Interprétation des Résultats

### Scénario 1: "✅ Reçu" Trouvé

**Problème:** L'image contient l'ancien code

**Solution:**
1. Déclencher le workflow "Deploy Ganopa Bot" pour rebuild avec le dernier commit
2. Attendre que le déploiement se termine
3. Vérifier que la nouvelle image est déployée

### Scénario 2: "✅ Reçu" Non Trouvé, Mais Bot Échoit Encore

**Problème:** Le webhook Telegram pointe peut-être vers un autre service

**Vérifications:**
1. Vérifier quel service ECS répond à `/telegram/webhook`
2. Vérifier le routing ALB
3. Vérifier les logs CloudWatch du service `ganopa-dev-bot-svc`

## 🚨 Action Immédiate

**Exécutez les commandes ci-dessus et partagez les résultats.**

En particulier:
- Voyez-vous "✅ Reçu" dans l'image ?
- Voyez-vous "openai_request_start" dans l'image ?

Avec ces réponses, je pourrai déterminer si un rebuild est nécessaire ou si le problème est ailleurs.

