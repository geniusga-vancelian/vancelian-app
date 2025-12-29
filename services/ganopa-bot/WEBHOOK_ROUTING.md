# 🔍 Diagnostic: Webhook Routing

## Problème Identifié

**Il y a DEUX services avec `/telegram/webhook` :**

1. **`agent_gateway/app.py`** (ligne 50)
   - Service: `vancelian-dev-api-svc` (probablement)
   - Endpoint: `POST /telegram/webhook`
   - Usage: Commandes Telegram (`/brainstorm`, `/plan`, etc.)

2. **`services/ganopa-bot/app/main.py`** (ligne 105)
   - Service: `ganopa-dev-bot-svc`
   - Endpoint: `POST /telegram/webhook`
   - Usage: Bot AI Ganopa (réponses OpenAI)

## 🎯 Action Immédiate

### 1. Vérifier quel service reçoit les webhooks

**Test 1: Vérifier l'endpoint `/telegram/webhook`**

```bash
curl -X GET https://api.maisonganopa.com/telegram/webhook
```

**Résultats possibles:**

**A) `{"ok": true, "hint": "Telegram webhook expects POST"}`**
- ✅ Le webhook pointe vers `ganopa-bot`
- Le problème est ailleurs (OpenAI API key, etc.)

**B) Autre réponse ou 404**
- ❌ Le webhook pointe vers `agent_gateway` ou un autre service
- Il faut rediriger le webhook vers `ganopa-bot`

**Test 2: Vérifier l'endpoint `/version`**

```bash
curl https://api.maisonganopa.com/version
```

**Résultats possibles:**

**A) `{"service": "ganopa-bot", "bot_build_id": "...", ...}`**
- ✅ Le service `ganopa-bot` est accessible
- Le webhook doit pointer vers ce service

**B) 404 ou autre service**
- ❌ Le service `ganopa-bot` n'est pas accessible via l'ALB
- Il faut configurer le routing ALB

### 2. Vérifier la configuration Telegram

**Vérifier où le webhook Telegram est configuré:**

```bash
# Remplacer <TELEGRAM_BOT_TOKEN> par votre token
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo"
```

**Résultat attendu:**
```json
{
  "ok": true,
  "result": {
    "url": "https://api.maisonganopa.com/telegram/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

**Si l'URL est différente ou pointe vers un autre domaine:**
- Il faut reconfigurer le webhook Telegram

### 3. Vérifier le routing ALB

**Dans AWS Console:**

1. **EC2 → Load Balancers**
   - Chercher l'ALB qui sert `api.maisonganopa.com`
   - Voir les Listeners → Rules

2. **Vérifier les règles de routing:**
   - Path `/telegram/webhook` → Quel Target Group?
   - Path `/version` → Quel Target Group?
   - Path `/health` → Quel Target Group?

3. **Vérifier les Target Groups:**
   - Quel service ECS est dans chaque Target Group?
   - `ganopa-dev-bot-svc` doit être dans le Target Group pour `/telegram/webhook`

## 🔧 Solution: Rediriger le webhook vers ganopa-bot

### Option 1: Reconfigurer le webhook Telegram (Recommandé)

**Si le webhook pointe vers `agent_gateway`, il faut le rediriger vers `ganopa-bot`:**

```bash
# Remplacer <TELEGRAM_BOT_TOKEN> et <WEBHOOK_SECRET> si configuré
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.maisonganopa.com/telegram/webhook",
    "secret_token": "<WEBHOOK_SECRET>"
  }'
```

**Mais d'abord, vérifier que l'ALB route `/telegram/webhook` vers `ganopa-bot`.**

### Option 2: Configurer le routing ALB

**Si l'ALB route `/telegram/webhook` vers `agent_gateway`:**

1. **Créer un nouveau Target Group pour `ganopa-bot`:**
   - EC2 → Target Groups → Create target group
   - Type: IP
   - Protocol: HTTP, Port: 8000
   - Health check: `/health`
   - Register targets: IPs du service `ganopa-dev-bot-svc`

2. **Modifier les règles ALB:**
   - Listener (HTTPS:443) → Rules
   - Ajouter/modifier une règle:
     - Condition: Path is `/telegram/webhook`
     - Action: Forward to → Target Group `ganopa-bot-tg`

3. **Alternative: Utiliser un path différent:**
   - `agent_gateway`: `/telegram/webhook` (commandes)
   - `ganopa-bot`: `/ganopa/webhook` (bot AI)
   - Reconfigurer le webhook Telegram vers `/ganopa/webhook`

## 📊 Checklist de Vérification

- [ ] Test `/version` retourne `{"service": "ganopa-bot", ...}`
- [ ] Test `/telegram/webhook` (GET) retourne `{"ok": true, "hint": ...}`
- [ ] `getWebhookInfo` montre `url: https://api.maisonganopa.com/telegram/webhook`
- [ ] ALB route `/telegram/webhook` vers `ganopa-dev-bot-svc`
- [ ] Logs CloudWatch de `ganopa-bot` montrent `telegram_update_received`
- [ ] Logs CloudWatch de `ganopa-bot` montrent `openai_request_start`

## 🚨 Prochaine Étape

**Exécutez ces commandes et partagez les résultats:**

```bash
# 1. Vérifier quel service répond à /version
curl https://api.maisonganopa.com/version

# 2. Vérifier quel service répond à /telegram/webhook
curl -X GET https://api.maisonganopa.com/telegram/webhook

# 3. Vérifier où le webhook Telegram est configuré
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo"
```

**Avec ces résultats, je pourrai identifier exactement où est le problème et proposer la solution précise.**

