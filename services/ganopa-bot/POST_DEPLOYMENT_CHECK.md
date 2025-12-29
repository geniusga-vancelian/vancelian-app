# ✅ Vérification Post-Déploiement

## 🎯 Checklist de Vérification

### 1. Vérifier que le Service Démarre Correctement

**Dans CloudWatch → Log Groups → `/ecs/ganopa-dev-bot-task` (ou `/aws/ecs/ganopa-dev-bot`):**

Chercher les logs récents (dernières 30 minutes) pour:

#### ✅ Log de Démarrage
```
[INFO] ganopa-bot: ganopa_bot_started {
  "service": "ganopa-bot",
  "bot_build_id": "build-YYYYMMDD-HHMMSS",
  "openai_model": "gpt-4o-mini",
  "has_openai_key": true,
  "has_webhook_secret": false,
  "signature_test_mode": false
}
```

**Si présent:** ✅ Le service démarre correctement avec le nouveau code

**Si absent:** ❌ Le code Python ne démarre pas (chercher les erreurs)

#### ✅ Health Checks
```
INFO: 127.0.0.1:XXXXX - "GET /health HTTP/1.1" 200 OK
```

**Si présent:** ✅ Le service répond aux health checks

**Si absent:** ⚠️ Vérifier la configuration du health check ECS

### 2. Tester l'Endpoint /version

```bash
curl https://api.maisonganopa.com/version
```

**Attendu:**
```json
{
  "service": "ganopa-bot",
  "bot_build_id": "build-YYYYMMDD-HHMMSS",
  "openai_model": "gpt-4o-mini",
  "has_openai_key": true,
  "has_webhook_secret": false,
  "signature_test_mode": false,
  "git_sha": "c78b569",
  "ts": "2025-12-29T..."
}
```

**Si vous voyez ça:** ✅ Le nouveau code tourne

**Si 404:** ⚠️ Vérifier le routing ALB

### 3. Tester le Bot Telegram

**Envoyer un message Telegram au bot**

**Attendu:**
- ✅ Réponse AI générée (pas d'écho)
- ✅ Réponse en français (ou dans la langue de l'utilisateur)
- ✅ Réponse concise (< 200 mots)

**Si le bot échoit encore:** ❌ Vérifier les logs CloudWatch (voir ci-dessous)

### 4. Vérifier les Logs de Webhook

**Dans CloudWatch, chercher après avoir envoyé un message:**

#### ✅ Webhook Reçu
```
[INFO] ganopa-bot: telegram_update_received {
  "update_id": 123456,
  "has_message": true,
  ...
}
```

**Si présent:** ✅ Le webhook arrive au service

**Si absent:** ❌ Le webhook ne pointe pas vers le bon service

#### ✅ Message Traité
```
[INFO] ganopa-bot: telegram_message_processing {
  "update_id": 123456,
  "chat_id": 789,
  "text_len": 50,
  "text_preview": "...",
  ...
}
```

**Si présent:** ✅ Le message est traité

**Si absent:** ❌ Exception dans `process_telegram_update`

#### ✅ OpenAI Appelé
```
[INFO] ganopa-bot: openai_request_start {
  "update_id": 123456,
  "chat_id": 789,
  "text_preview": "...",
  ...
}
```

**Si présent:** ✅ OpenAI est appelé

**Si absent:** ❌ Exception avant l'appel OpenAI (chercher les erreurs)

#### ✅ OpenAI Réponse
```
[INFO] ganopa-bot: openai_request_done {
  "update_id": 123456,
  "chat_id": 789,
  "model": "gpt-4o-mini",
  "response_len": 150,
  "reply_preview": "...",
  "tokens_used": 200,
  "latency_ms": 1500
}
```

**Si présent:** ✅ OpenAI a répondu avec succès

**Si absent:** Chercher `openai_request_error` ou `openai_http_error`

#### ✅ Message Envoyé
```
[INFO] ganopa-bot: telegram_send_done {
  "update_id": 123456,
  "chat_id": 789,
  "message_id": 999,
  "response_len": 150
}
```

**Si présent:** ✅ La réponse a été envoyée

**Si absent:** ❌ Erreur lors de l'envoi (chercher `telegram_send_failed`)

### 5. Vérifier les Erreurs

**Dans CloudWatch, chercher:**
- `ERROR` → Erreur quelconque
- `Exception` → Exception Python
- `Traceback` → Stack trace complet
- `openai_request_error` → Erreur OpenAI
- `telegram_send_failed` → Erreur envoi Telegram

**Si des erreurs sont présentes:** Voir la section Troubleshooting ci-dessous

## 🔧 Troubleshooting

### Problème: Le bot échoit encore

**Vérifier:**
1. Les logs montrent `ganopa_bot_started` avec un `bot_build_id` récent
2. Les logs montrent `openai_request_start` quand vous envoyez un message
3. Les logs montrent `openai_request_done` (succès) ou `openai_request_error` (échec)

**Si `openai_request_error` est présent:**
- Vérifier `OPENAI_API_KEY` dans la Task Definition ECS
- Vérifier le message d'erreur exact dans les logs

**Si `openai_request_start` est absent:**
- Chercher `telegram_update_processing_failed` ou `ERROR` dans les logs
- Vérifier qu'il n'y a pas d'exception dans `process_telegram_update`

### Problème: Aucun log `telegram_update_received`

**Vérifier:**
1. Le webhook Telegram pointe vers `https://api.maisonganopa.com/telegram/webhook`
2. L'ALB route `/telegram/webhook` vers `ganopa-dev-bot-svc`
3. Le service ECS est "healthy" (health checks réussissent)

**Solution:**
- Vérifier la configuration Telegram webhook
- Vérifier le routing ALB
- Vérifier le statut du service ECS

### Problème: `openai_request_error` avec status 401

**Cause:** `OPENAI_API_KEY` manquant ou invalide

**Solution:**
1. ECS → Task Definitions → `ganopa-dev-bot-svc` (dernière révision)
2. Container `ganopa-bot` → Environment variables
3. Vérifier que `OPENAI_API_KEY` est présent et non vide
4. Si absent, l'ajouter depuis AWS Secrets Manager ou directement
5. Enregistrer nouvelle révision
6. Services → `ganopa-dev-bot-svc` → Update service → Sélectionner nouvelle révision

## 📊 Résumé

**Si tous les logs sont présents:**
- ✅ Le service fonctionne correctement
- ✅ Le bot devrait répondre avec des réponses AI
- ✅ Pas d'écho

**Si des logs manquent:**
- ❌ Identifier quel log manque
- ❌ Suivre le troubleshooting correspondant
- ❌ Vérifier les erreurs dans CloudWatch

## 🎯 Test Rapide

**Pour vérifier rapidement que tout fonctionne:**

1. **Envoyer un message Telegram:** "Bonjour"
2. **Vérifier la réponse:** Doit être une réponse AI (pas "Bonjour")
3. **Vérifier les logs CloudWatch:** Doit voir `telegram_update_received`, `openai_request_start`, `openai_request_done`, `telegram_send_done`

**Si tout est présent:** ✅ Le bot fonctionne correctement !

