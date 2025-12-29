# ✅ Checklist de Déploiement - Ganopa Bot

## 🎯 Objectif

Vérifier que le bot Ganopa est correctement déployé et fonctionne avec OpenAI.

---

## 1. Vérification de la Version Déployée

### Via Endpoint `/_meta`

```bash
# Test de l'endpoint /_meta
curl -s https://api.maisonganopa.com/_meta | jq

# Vérifier les headers
curl -s -I https://api.maisonganopa.com/_meta | grep -i "x-ganopa"
```

**Attendu:**
```json
{
  "service": "ganopa-bot",
  "version": "ganopa-bot-{hash}",
  "build_id": "...",
  "hostname": "...",
  "openai_model": "gpt-4o-mini",
  "has_openai_key": true,
  "has_webhook_secret": true,
  "ts": "2025-12-29T..."
}
```

**Headers attendus:**
```
X-Ganopa-Build-Id: ...
X-Ganopa-Version: ganopa-bot-{hash}
```

### Vérifier la Version Spécifique

```bash
# Remplacer par la version attendue (ex: ganopa-bot-7f22c89b)
VERSION_ATTENDUE="ganopa-bot-7f22c89b"
VERSION_ACTUELLE=$(curl -s https://api.maisonganopa.com/_meta | jq -r '.version')

if [ "${VERSION_ACTUELLE}" = "${VERSION_ATTENDUE}" ]; then
  echo "✅ Version correcte: ${VERSION_ACTUELLE}"
else
  echo "❌ Version incorrecte:"
  echo "  Attendu: ${VERSION_ATTENDUE}"
  echo "  Actuel: ${VERSION_ACTUELLE}"
fi
```

---

## 2. Vérification du Health Check

```bash
# Test de l'endpoint /health
curl -s https://api.maisonganopa.com/health | jq

# Vérifier les headers
curl -s -I https://api.maisonganopa.com/health | grep -i "x-ganopa"
```

**Attendu:**
```json
{
  "status": "ok",
  "service": "ganopa-bot",
  "ts": "2025-12-29T..."
}
```

---

## 3. Test du Webhook Telegram

### Test GET (vérification URL)

```bash
curl -s https://api.maisonganopa.com/telegram/webhook
```

**Attendu:**
```json
{
  "ok": true,
  "hint": "Telegram webhook expects POST"
}
```

### Test POST (simulation)

```bash
# Test avec un payload Telegram sample
curl -X POST https://api.maisonganopa.com/telegram/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: Azerty0334" \
  -d '{
    "update_id": 123456789,
    "message": {
      "message_id": 1,
      "from": {
        "id": 123456,
        "is_bot": false,
        "first_name": "Test"
      },
      "chat": {
        "id": 123456,
        "type": "private"
      },
      "date": 1234567890,
      "text": "Hello"
    }
  }'
```

**Attendu:**
```json
{
  "ok": true
}
```

---

## 4. Vérification des Logs CloudWatch

### Localisation des Logs

**Log Group:** `/ecs/ganopa-dev-bot-task` (ou similaire selon votre configuration)

### Commandes AWS CLI

```bash
# Voir les logs récents (10 dernières minutes)
aws logs tail /ecs/ganopa-dev-bot-task \
  --region me-central-1 \
  --since 10m \
  --format short

# Filtrer les logs spécifiques
aws logs tail /ecs/ganopa-dev-bot-task \
  --region me-central-1 \
  --since 10m \
  --format short \
  --filter-pattern "webhook_received OR openai_called OR telegram_sent"
```

### Logs à Vérifier

Après avoir envoyé un message Telegram, vous devriez voir dans l'ordre:

1. **`ganopa_bot_started`** (au démarrage du service)
   - `service`: "ganopa-bot"
   - `version`: hash unique
   - `has_openai_key`: true
   - `has_webhook_secret`: true

2. **`webhook_received`** (réception du webhook)
   - `correlation_id`: identifiant unique
   - `path`: "/telegram/webhook"

3. **`secret_ok`** (vérification du secret)
   - `correlation_id`: même que ci-dessus
   - `header_present`: true
   - `secret_ok`: true

4. **`update_parsed`** (parsing du JSON)
   - `correlation_id`: même que ci-dessus
   - `update_id`: ID Telegram

5. **`message_extracted`** (extraction du message)
   - `correlation_id`: même que ci-dessus
   - `chat_id`: ID du chat
   - `text_len`: longueur du texte
   - `text_preview`: aperçu du texte

6. **`openai_called`** (appel OpenAI)
   - `correlation_id`: même que ci-dessus
   - `model`: "gpt-4o-mini"
   - `text_len`: longueur du texte

7. **`openai_ok`** (succès OpenAI) OU **`openai_error`** (erreur)
   - `correlation_id`: même que ci-dessus
   - `response_len`: longueur de la réponse
   - `tokens_used`: tokens utilisés
   - `latency_ms`: latence en millisecondes

8. **`telegram_send_start`** (début envoi Telegram)
   - `correlation_id`: même que ci-dessus
   - `reply_len`: longueur de la réponse

9. **`telegram_sent`** (succès envoi Telegram)
   - `correlation_id`: même que ci-dessus
   - `status_code`: 200

### Vérification du Correlation ID

Tous les logs d'un même update doivent avoir le même `correlation_id` (format: `upd-{update_id}`).

---

## 5. Test End-to-End avec Telegram

### Envoyer un Message

1. Ouvrir Telegram
2. Envoyer un message au bot (ex: "Hello")
3. Vérifier que la réponse commence par "🤖" (preuve OpenAI, pas echo)

### Vérifier les Logs

```bash
# Voir les logs après avoir envoyé un message
aws logs tail /ecs/ganopa-dev-bot-task \
  --region me-central-1 \
  --since 5m \
  --format short \
  --filter-pattern "correlation_id"
```

**À vérifier:**
- Tous les logs ont le même `correlation_id`
- La séquence complète est présente (webhook_received → telegram_sent)
- `openai_ok` est présent (pas `openai_error`)
- La réponse contient `response_len` > 0

---

## 6. Vérification des Protections

### Anti-Loop (Messages de Bots)

Si un bot envoie un message, vous devriez voir:
```
update_ignored_bot
  correlation_id: upd-{update_id}
  from_user_id: {id}
```

### Deduplication

Si le même `update_id` est traité deux fois, vous devriez voir:
```
update_duplicate
  correlation_id: upd-{update_id}
  update_id: {update_id}
```

---

## 7. Checklist de Validation

- [ ] `/_meta` renvoie la VERSION attendue
- [ ] Headers `X-Ganopa-Version` et `X-Ganopa-Build-Id` présents
- [ ] `/health` retourne `{"status": "ok"}`
- [ ] `/telegram/webhook` (GET) retourne `{"ok": true, "hint": ...}`
- [ ] `/telegram/webhook` (POST) retourne `{"ok": true}`
- [ ] Logs CloudWatch contiennent tous les événements attendus
- [ ] `correlation_id` est présent dans tous les logs d'un même update
- [ ] Envoi d'un message Telegram génère une réponse avec prefix "🤖"
- [ ] Aucun secret n'est logué (OPENAI_API_KEY, TELEGRAM_BOT_TOKEN)

---

## 8. Commandes Rapides (One-liner)

```bash
# Vérification complète en une commande
echo "=== /_meta ===" && \
curl -s https://api.maisonganopa.com/_meta | jq '{service,version,has_openai_key}' && \
echo "=== /health ===" && \
curl -s https://api.maisonganopa.com/health | jq && \
echo "=== Headers ===" && \
curl -s -I https://api.maisonganopa.com/_meta | grep -i "x-ganopa" && \
echo "=== Logs récents ===" && \
aws logs tail /ecs/ganopa-dev-bot-task --region me-central-1 --since 5m --format short --filter-pattern "ganopa_bot_started" | tail -5
```

---

## 🚨 Dépannage

### Problème: Version incorrecte

**Solution:**
1. Vérifier que le workflow GitHub Actions a réussi
2. Vérifier que l'image Docker tag correspond au dernier commit
3. Vérifier que le service ECS utilise la bonne Task Definition

### Problème: Logs manquants

**Solution:**
1. Vérifier que le log group existe: `/ecs/ganopa-dev-bot-task`
2. Vérifier que les logs sont envoyés depuis le container
3. Vérifier les permissions IAM du task role

### Problème: Réponse sans prefix "🤖"

**Solution:**
1. Vérifier que `openai_ok` est présent dans les logs (pas `openai_error`)
2. Vérifier que `OPENAI_API_KEY` est configurée dans la Task Definition
3. Vérifier que le code déployé contient le prefix "🤖"

---

**Date de création:** 2025-12-29  
**Dernière mise à jour:** 2025-12-29

