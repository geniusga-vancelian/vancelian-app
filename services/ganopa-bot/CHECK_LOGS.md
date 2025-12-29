# 🔍 Vérification des Logs CloudWatch

## ✅ Diagnostic des Endpoints

**Tests effectués:**
- ✅ `/health` → `ganopa-bot` répond correctement
- ✅ `/telegram/webhook` (GET) → `ganopa-bot` répond correctement
- ❌ `/version` → Not Found (pas encore déployé, normal)

**Conclusion:** Le routing ALB est correct. Le webhook Telegram pointe bien vers `ganopa-bot`.

## 🎯 Prochaine Étape: Vérifier les Logs CloudWatch

Puisque le routing est correct mais que le bot échoit encore, le problème est probablement:

1. **OpenAI API Key manquante ou invalide** → OpenAI échoue silencieusement
2. **Exception dans `process_telegram_update`** → Le code crash avant d'appeler OpenAI
3. **Ancien code tourne encore** → Le commit `c78b569` n'est pas vraiment déployé

## 📊 Commandes AWS CLI pour Vérifier les Logs

### 1. Vérifier les logs récents (30 dernières minutes)

```bash
aws logs tail /aws/ecs/ganopa-dev-bot \
  --region me-central-1 \
  --since 30m \
  --format short
```

### 2. Chercher spécifiquement `telegram_update_received`

```bash
aws logs filter-log-events \
  --log-group-name /aws/ecs/ganopa-dev-bot \
  --region me-central-1 \
  --filter-pattern "telegram_update_received" \
  --start-time $(date -u -v-1H +%s)000
```

### 3. Chercher `openai_request_start`

```bash
aws logs filter-log-events \
  --log-group-name /aws/ecs/ganopa-dev-bot \
  --region me-central-1 \
  --filter-pattern "openai_request_start" \
  --start-time $(date -u -v-1H +%s)000
```

### 4. Chercher toutes les erreurs

```bash
aws logs filter-log-events \
  --log-group-name /aws/ecs/ganopa-dev-bot \
  --region me-central-1 \
  --filter-pattern "ERROR" \
  --start-time $(date -u -v-1H +%s)000
```

## 🔍 Ce qu'il faut chercher dans les logs

### Scénario 1: Aucun `telegram_update_received`
- **Problème:** Les webhooks n'arrivent pas au service
- **Solution:** Vérifier la configuration Telegram webhook

### Scénario 2: `telegram_update_received` présent mais pas `openai_request_start`
- **Problème:** Exception dans `process_telegram_update` avant l'appel OpenAI
- **Solution:** Chercher `telegram_update_processing_failed` ou `ERROR` dans les logs

### Scénario 3: `openai_request_start` présent mais `openai_request_error`
- **Problème:** OpenAI API Key manquante ou invalide
- **Solution:** Vérifier `OPENAI_API_KEY` dans la Task Definition ECS

### Scénario 4: `openai_request_done` présent mais le bot échoit quand même
- **Problème:** Le message retourné par OpenAI est l'écho (peu probable)
- **Solution:** Vérifier le contenu de `openai_response_text` dans les logs

## 🚨 Action Immédiate

**Dans AWS Console → CloudWatch → Log Groups → `/aws/ecs/ganopa-dev-bot`:**

1. **Filtrer les logs des 30 dernières minutes**
2. **Chercher:**
   - `telegram_update_received` → Confirme que le webhook arrive
   - `telegram_message_processing` → Confirme que le message est traité
   - `openai_request_start` → Confirme qu'OpenAI est appelé
   - `openai_request_error` → Si présent, voir l'erreur
   - `telegram_send_done` → Confirme que la réponse est envoyée

**Partagez les logs trouvés pour que je puisse identifier le problème exact.**

