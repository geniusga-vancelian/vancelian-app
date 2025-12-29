# ✅ Résumé du Déploiement - Ganopa Bot

## 📋 Modifications Apportées

### A) Audit Local ✅
- ✅ **Aucun code "echo fallback" trouvé** - Le code utilise toujours `call_openai()`
- ✅ Vérification complète de `main.py`, `config.py`, `ai_service.py`, `ai_prompt.py`
- ✅ Pas de `return f"✅ Reçu: {text}"` ou `call_vancelian_backend()`

### B) Logs "Prouve que c'est cette version" ✅
- ✅ **Constante VERSION** ajoutée: `ganopa-bot-{hash}` (basé sur SERVICE_NAME + BUILD_ID)
- ✅ **Endpoint `/_meta`** amélioré avec:
  - `service`: "ganopa-bot"
  - `version`: hash unique
  - `hostname`: hostname du container
  - `openai_model`: modèle OpenAI utilisé
  - `has_openai_key`: booléen (pas le secret)
  - `has_webhook_secret`: booléen (pas le secret)
  - `ts`: timestamp ISO
- ✅ **Logs structurés** ajoutés:
  - `telegram_webhook_post`: update_id, chat_id, text_len, path, header_secret_ok
  - `telegram_message_extracted`: update_id, chat_id, text_len, text_preview
  - `openai_request_start`: model, text_len, text_preview
  - `openai_request_success`: response_len, tokens_used, latency_ms, http_status
  - `telegram_send_start`: reply_len, reply_preview
  - `telegram_send_success`: status_code
  - Tous les logs d'erreur incluent `error_type` et détails

### C) Branchement OpenAI (MVP Robuste) ✅
- ✅ **Timeout 20s** (au lieu de 25s)
- ✅ **Gestion d'erreurs complète**: HTTP, JSON, timeout, network
- ✅ **Vérification OPENAI_API_KEY**: message explicite si manquante
- ✅ **Prefix "🤖"** ajouté à toutes les réponses OpenAI (preuve que ce n'est pas un echo)
- ✅ **Logs détaillés** à chaque étape

### D) Tests Locaux ✅
- ✅ Script `test_local.sh`: compilation, imports, endpoints
- ✅ Script `test_webhook_sample.sh`: test POST avec payload Telegram
- ✅ Commande `python3 -m compileall services/ganopa-bot/app` ✅

### E) Commit / Push ✅
- ✅ Commit: `31c7684` - "ganopa-bot: add meta + logs + openai reply with 🤖 prefix"
- ✅ Push sur `main` ✅

---

## 📄 Fichiers Modifiés

### `services/ganopa-bot/app/main.py`
- ✅ Ajout de `VERSION` (hash basé sur SERVICE_NAME + BUILD_ID)
- ✅ Ajout de `HOSTNAME` (socket.gethostname())
- ✅ Amélioration de `/_meta` avec version et hostname
- ✅ Ajout de headers `X-Ganopa-Version` sur `/health` et `/_meta`
- ✅ Logs structurés complets à chaque étape
- ✅ Prefix "🤖" sur toutes les réponses OpenAI
- ✅ Timeout OpenAI réduit à 20s
- ✅ Aucun secret logué (seulement booléens)

### `services/ganopa-bot/app/config.py`
- ✅ **Aucune modification** - Déjà correct

### Nouveaux Fichiers
- ✅ `test_local.sh`: Script de test local
- ✅ `test_webhook_sample.sh`: Test webhook avec payload Telegram
- ✅ `CHECK_DEPLOYMENT.md`: Commandes AWS CLI pour vérification

---

## 🧪 Commandes de Test Local

### 1. Compilation Python
```bash
python3 -m compileall services/ganopa-bot/app -q
```

### 2. Test des Endpoints
```bash
# Démarrer le serveur
cd services/ganopa-bot
export TELEGRAM_BOT_TOKEN=...
export OPENAI_API_KEY=...
export WEBHOOK_SECRET=Azerty0334
uvicorn app.main:app --reload --port 8000

# Dans un autre terminal
curl http://localhost:8000/health
curl http://localhost:8000/_meta | jq
```

### 3. Test du Webhook (POST)
```bash
# Utiliser le script fourni
cd services/ganopa-bot
export CHAT_ID=<votre_chat_id>
./test_webhook_sample.sh

# Ou manuellement
curl -X POST http://localhost:8000/telegram/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: Azerty0334" \
  -d '{
    "update_id": 123456789,
    "message": {
      "message_id": 1,
      "from": {"id": 123456, "is_bot": false, "first_name": "Test"},
      "chat": {"id": <CHAT_ID>, "type": "private"},
      "date": 1234567890,
      "text": "Hello"
    }
  }'
```

**Vérifier:**
- Réponse immédiate: `{"ok": true}`
- Logs: `telegram_webhook_post`, `openai_request_start`, `openai_request_success`, `telegram_send_success`

---

## 🔍 Commandes AWS CLI pour Vérification

### 1. Vérifier le Routing ALB pour /telegram/webhook

```bash
# Trouver l'ALB
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --region me-central-1 \
  --query 'LoadBalancers[?contains(DNSName, `maisonganopa`)].LoadBalancerArn' \
  --output text)

# Trouver le listener HTTPS
LISTENER_ARN=$(aws elbv2 describe-listeners \
  --region me-central-1 \
  --load-balancer-arn "${ALB_ARN}" \
  --query 'Listeners[?Port==`443`].ListenerArn' \
  --output text)

# Vérifier les règles
aws elbv2 describe-rules \
  --region me-central-1 \
  --listener-arn "${LISTENER_ARN}" \
  --query 'Rules[*].{
    priority:Priority,
    conditions:Conditions[*].{field:Field,values:Values},
    actions:Actions[*].{type:Type,targetGroupArn:TargetGroupArn}
  }' \
  --output json | jq 'sort_by(.priority)'
```

**À vérifier:** Une règle avec `Path is /telegram/webhook` forward vers le Target Group de `ganopa-dev-bot-svc`

### 2. Vérifier le Target Group

```bash
# Trouver le Target Group
TG_ARN=$(aws elbv2 describe-target-groups \
  --region me-central-1 \
  --query 'TargetGroups[?contains(TargetGroupName, `ganopa`) || contains(TargetGroupName, `bot`)].TargetGroupArn' \
  --output text | head -1)

# Vérifier les targets
aws elbv2 describe-target-health \
  --region me-central-1 \
  --target-group-arn "${TG_ARN}" \
  --query 'TargetHealthDescriptions[*].{
    target:Target.Id,
    port:Target.Port,
    health:TargetHealth.State
  }' \
  --output json
```

**À vérifier:** Au moins 1 target avec `health` = `healthy`

### 3. Vérifier l'ECS Service

```bash
# Vérifier le service
aws ecs describe-services \
  --region me-central-1 \
  --cluster vancelian-dev-api-cluster \
  --services ganopa-dev-bot-svc \
  --query 'services[0].{
    status:status,
    desired:desiredCount,
    running:runningCount,
    taskDef:taskDefinition
  }' \
  --output json

# Vérifier l'image dans la Task Definition
TASKDEF_ARN=$(aws ecs describe-services \
  --region me-central-1 \
  --cluster vancelian-dev-api-cluster \
  --services ganopa-dev-bot-svc \
  --query 'services[0].taskDefinition' \
  --output text)

aws ecs describe-task-definition \
  --region me-central-1 \
  --task-definition "${TASKDEF_ARN}" \
  --query 'taskDefinition.containerDefinitions[?name==`ganopa-bot`].image' \
  --output text
```

**À vérifier:**
- `status` = ACTIVE
- `running` = 1
- `image` tag = dernier GITHUB_SHA (commit `31c7684`)

### 4. Vérifier /_meta renvoie la VERSION

```bash
# Test de l'endpoint
curl -s https://api.maisonganopa.com/_meta | jq

# Vérifier les headers
curl -s -I https://api.maisonganopa.com/_meta | grep -i "x-ganopa"

# Vérifier la version
VERSION=$(curl -s https://api.maisonganopa.com/_meta | jq -r '.version')
echo "Version déployée: ${VERSION}"
```

**À vérifier:**
- `service` = "ganopa-bot"
- `version` = hash unique (ex: "ganopa-bot-7f22c89b")
- `has_openai_key` = true
- Headers `X-Ganopa-Build-Id` et `X-Ganopa-Version` présents

---

## ✅ Checklist de Validation (3-5 items)

### Post-Déploiement

1. **✅ Vérifier /_meta renvoie la VERSION attendue**
   ```bash
   curl -s https://api.maisonganopa.com/_meta | jq '.version'
   ```
   - Doit retourner un hash (ex: "ganopa-bot-7f22c89b")
   - Headers `X-Ganopa-Version` présent

2. **✅ Vérifier que l'ALB route /telegram/webhook vers le bon Target Group**
   - Voir commandes AWS CLI section 1
   - La règle doit forward vers le Target Group de `ganopa-dev-bot-svc`

3. **✅ Vérifier que le Target Group a des targets Healthy**
   - Voir commandes AWS CLI section 2
   - Au moins 1 target avec `health` = `healthy`

4. **✅ Vérifier que l'ECS service déploie la dernière image**
   - Voir commandes AWS CLI section 3
   - Image tag = dernier GITHUB_SHA (commit `31c7684`)

5. **✅ Tester end-to-end: Envoyer "Hello" sur Telegram**
   - La réponse doit commencer par "🤖" (preuve OpenAI)
   - Vérifier les logs CloudWatch pour:
     - `telegram_webhook_post`
     - `openai_request_start`
     - `openai_request_success`
     - `telegram_send_success`

---

## 🎯 Preuve que la Version Déployée est Correcte

### Méthode 1: Endpoint /_meta
```bash
curl -s https://api.maisonganopa.com/_meta | jq
```

**Attendu:**
```json
{
  "service": "ganopa-bot",
  "version": "ganopa-bot-7f22c89b",
  "build_id": "...",
  "hostname": "...",
  "openai_model": "gpt-4o-mini",
  "has_openai_key": true,
  "has_webhook_secret": true,
  "ts": "2025-12-29T..."
}
```

### Méthode 2: Headers HTTP
```bash
curl -s -I https://api.maisonganopa.com/_meta | grep -i "x-ganopa"
```

**Attendu:**
```
X-Ganopa-Build-Id: ...
X-Ganopa-Version: ganopa-bot-7f22c89b
```

### Méthode 3: Prefix "🤖" dans les Réponses
- Envoyer "Hello" sur Telegram
- La réponse doit commencer par "🤖" (preuve que c'est OpenAI, pas un echo)

### Méthode 4: Logs CloudWatch
- Vérifier que les logs contiennent `version` dans `ganopa_bot_started`
- Vérifier que les logs contiennent tous les événements structurés

---

## 📝 Notes Importantes

- ✅ **Aucun secret logué**: Seulement des booléens (`has_openai_key`, `has_webhook_secret`)
- ✅ **Timeout OpenAI**: 20s (comme demandé)
- ✅ **Prefix "🤖"**: Toutes les réponses OpenAI ont ce prefix pour prouver qu'elles ne sont pas des echos
- ✅ **Endpoint /health**: Non modifié (fonctionne toujours)
- ✅ **Path /telegram/webhook**: Non modifié (règle ALB existante)

---

## 🚀 Prochaines Étapes

1. **Attendre le déploiement automatique** (workflow GitHub Actions)
2. **Vérifier /_meta** pour confirmer la version
3. **Tester avec un message Telegram** pour voir le prefix "🤖"
4. **Vérifier les logs CloudWatch** pour confirmer tous les événements

---

**Commit:** `31c7684`  
**Date:** 2025-12-29  
**Status:** ✅ Prêt pour déploiement

