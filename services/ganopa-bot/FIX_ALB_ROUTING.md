# 🔧 Correction du Routing ALB

## Problème Identifié

Le webhook Telegram `/telegram/webhook` pointe vers le mauvais service ECS via l'ALB.

## 🎯 Solution: Corriger le Routing ALB

### Option 1: Modifier la Règle ALB pour `/telegram/webhook`

**Dans AWS Console → EC2 → Load Balancers:**

1. **Sélectionner l'ALB qui sert `api.maisonganopa.com`**
2. **Onglet "Listeners"**
3. **Cliquer sur le Listener HTTPS (port 443)**
4. **Voir les règles (Rules)**

**Chercher la règle pour `/telegram/webhook`:**

- Si elle existe, la modifier
- Si elle n'existe pas, créer une nouvelle règle

**Configuration de la règle:**

1. **Condition:** `Path is /telegram/webhook`
2. **Action:** `Forward to` → Sélectionner le Target Group de `ganopa-dev-bot-svc`

**Pour trouver le Target Group de `ganopa-dev-bot-svc`:**

1. **ECS → Services → `ganopa-dev-bot-svc`**
2. **Onglet "Configuration et mise en réseau"**
3. **Voir "Load balancer"** → Cliquer sur le nom
4. **Voir "Target groups"** → Noter le nom du Target Group

**OU**

1. **EC2 → Target Groups**
2. **Chercher un Target Group qui contient `ganopa-dev-bot-svc`**
3. **Vérifier les targets** → Doit contenir les tasks de `ganopa-dev-bot-svc`

### Option 2: Utiliser un Path Différent

**Si vous voulez garder `/telegram/webhook` pour `agent_gateway`:**

1. **Créer une nouvelle règle ALB:**
   - **Condition:** `Path is /ganopa/webhook`
   - **Action:** `Forward to` → Target Group de `ganopa-dev-bot-svc`

2. **Reconfigurer le webhook Telegram:**
   ```bash
   curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://api.maisonganopa.com/ganopa/webhook",
       "secret_token": "<WEBHOOK_SECRET>"
     }'
   ```

3. **Modifier `main.py` pour utiliser `/ganopa/webhook`:**
   - Changer `@app.post("/telegram/webhook")` en `@app.post("/ganopa/webhook")`
   - Redéployer

### Option 3: Vérifier l'Ordre des Règles

**L'ordre des règles ALB est important:**

1. **Les règles sont évaluées dans l'ordre (de haut en bas)**
2. **La première règle qui correspond est utilisée**
3. **Assurez-vous que la règle pour `/telegram/webhook` est AVANT la règle par défaut**

**Ordre recommandé:**

1. **Règle 1:** `Path is /telegram/webhook` → `ganopa-dev-bot-svc` (si vous voulez que Ganopa réponde)
2. **Règle 2:** `Path is /telegram/webhook` → `agent_gateway` (si vous voulez que agent_gateway réponde)
3. **Règle par défaut:** `Forward to` → Autre service

**Note:** Vous ne pouvez avoir qu'UNE règle qui correspond à `/telegram/webhook`. La première qui correspond sera utilisée.

## 📊 Vérification Post-Correction

### 1. Tester l'Endpoint

```bash
curl -X GET https://api.maisonganopa.com/telegram/webhook
```

**Attendu:**
```json
{"ok": true, "hint": "Telegram webhook expects POST"}
```

**Si vous voyez ça:** ✅ Le routing pointe vers `ganopa-bot`

**Si vous voyez autre chose:** ❌ Le routing pointe encore vers un autre service

### 2. Tester le Bot Telegram

**Envoyer un message Telegram au bot**

**Attendu:**
- ✅ Réponse AI générée (pas d'écho)
- ✅ Pas de "✅ Reçu:"

**Si le bot échoit encore:** ❌ Le routing n'est pas correct ou le service n'a pas redémarré

### 3. Vérifier les Logs CloudWatch

**Dans CloudWatch → `/ecs/ganopa-dev-bot-task`:**

**Après avoir envoyé un message, chercher:**

- ✅ `telegram_update_received` → Le webhook arrive
- ✅ `telegram_message_processing` → Le message est traité
- ✅ `openai_request_start` → OpenAI est appelé
- ✅ `openai_request_done` → OpenAI a répondu

**Si tous ces logs sont présents:** ✅ Le routing est correct et le bot fonctionne

## 🚨 Action Immédiate

**Corrigez le routing ALB maintenant:**

1. **AWS Console → EC2 → Load Balancers**
2. **Sélectionner l'ALB qui sert `api.maisonganopa.com`**
3. **Listeners → HTTPS (443) → Rules**
4. **Modifier ou créer la règle pour `/telegram/webhook`**
5. **Forward to → Target Group de `ganopa-dev-bot-svc`**
6. **Sauvegarder**

**Puis testez le bot pour confirmer que ça fonctionne !**

