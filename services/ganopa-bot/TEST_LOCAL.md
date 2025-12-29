# 🧪 Tests Locaux

## Prérequis

```bash
cd services/ganopa-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Variables d'Environnement

```bash
export TELEGRAM_BOT_TOKEN="your_token"
export OPENAI_API_KEY="your_key"  # Optional
export OPENAI_MODEL="gpt-4o-mini"  # Optional
export WEBHOOK_SECRET="your_secret"  # Optional
export BUILD_ID="local-test"  # Optional
export PORT="8000"  # Optional
```

## Lancer le Service

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --reload
```

## Tests avec curl

### 1. Health Check

```bash
curl -v http://localhost:8000/health
```

**Attendu:**
- Status: `200 OK`
- Header: `X-Ganopa-Build-Id: local-test` (ou valeur de BUILD_ID)
- Body: `{"status": "ok", "service": "ganopa-bot", "ts": "..."}`

### 2. Meta Endpoint

```bash
curl -v http://localhost:8000/_meta | jq
```

**Attendu:**
- Status: `200 OK`
- Header: `X-Ganopa-Build-Id: local-test`
- Body:
```json
{
  "service": "ganopa-bot",
  "build_id": "local-test",
  "openai_model": "gpt-4o-mini",
  "has_openai_key": true,
  "has_webhook_secret": false,
  "ts": "2025-12-29T..."
}
```

### 3. Telegram Webhook (GET)

```bash
curl -v http://localhost:8000/telegram/webhook
```

**Attendu:**
- Status: `200 OK`
- Body: `{"ok": true, "hint": "Telegram webhook expects POST"}`

### 4. Telegram Webhook (POST) - Test Minimal

```bash
curl -X POST http://localhost:8000/telegram/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 123456,
    "message": {
      "message_id": 1,
      "from": {"id": 789, "is_bot": false, "first_name": "Test"},
      "chat": {"id": 789, "type": "private"},
      "date": 1735492800,
      "text": "Hello"
    }
  }'
```

**Attendu:**
- Status: `200 OK` (immédiat)
- Body: `{"ok": true}`
- Le traitement se fait en background (vérifier les logs)

**Vérifier les logs:**
- `telegram_webhook_post` avec `update_id`, `chat_id`, `text_len`
- `telegram_message_processing`
- `openai_request_start` (si OPENAI_API_KEY est défini)
- `telegram_send_start` avec `reply_len`
- `telegram_send_success` ou `telegram_send_failed`

### 5. Telegram Webhook avec Secret Header

```bash
curl -X POST http://localhost:8000/telegram/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: your_secret" \
  -d '{
    "update_id": 123457,
    "message": {
      "message_id": 2,
      "from": {"id": 789, "is_bot": false, "first_name": "Test"},
      "chat": {"id": 789, "type": "private"},
      "date": 1735492801,
      "text": "Test with secret"
    }
  }'
```

**Vérifier les logs:**
- `header_secret_present: true`
- `header_secret_ok: true` (si WEBHOOK_SECRET correspond)

## Vérification des Logs

**Les logs doivent contenir:**

1. **Au démarrage:**
   ```
   ganopa_bot_started {
     "service": "ganopa-bot",
     "build_id": "local-test",
     "openai_model": "gpt-4o-mini",
     "has_openai_key": true,
     "has_webhook_secret": false
   }
   ```

2. **Au webhook POST:**
   ```
   telegram_webhook_post {
     "update_id": 123456,
     "chat_id": 789,
     "text_len": 5,
     "header_secret_present": false,
     "header_secret_ok": true
   }
   ```

3. **Avant OpenAI:**
   ```
   openai_request_start {
     "update_id": 123456,
     "chat_id": 789,
     "model": "gpt-4o-mini",
     "text_len": 5,
     "text_preview": "Hello"
   }
   ```

4. **Après OpenAI (succès):**
   ```
   openai_request_success {
     "update_id": 123456,
     "chat_id": 789,
     "model": "gpt-4o-mini",
     "response_len": 50,
     "tokens_used": 100,
     "latency_ms": 1500
   }
   ```

5. **Avant send Telegram:**
   ```
   telegram_send_start {
     "update_id": 123456,
     "chat_id": 789,
     "reply_len": 50
   }
   ```

6. **Après send Telegram:**
   ```
   telegram_send_success {
     "update_id": 123456,
     "chat_id": 789,
     "status_code": 200
   }
   ```

## Test sans OPENAI_API_KEY

**Si OPENAI_API_KEY n'est pas défini:**

```bash
unset OPENAI_API_KEY
# Redémarrer le service
```

**Envoyer un message:**
- Le bot doit répondre: `⚠️ OPENAI_API_KEY manquante (backend config).`
- Les logs doivent montrer: `openai_missing_api_key`

## Test avec Timeout

**Pour tester les timeouts, vous pouvez:**

1. **Simuler un timeout OpenAI** (nécessite un proxy ou mock)
2. **Vérifier que les timeouts sont bien configurés:**
   - OpenAI: 25s
   - Telegram: 10s

