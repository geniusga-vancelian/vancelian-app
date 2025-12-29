# Debug: Bot qui échoit malgré le déploiement

## ✅ État Confirmé
- Commit `c78b569` est déployé
- Code dans `main.py` est correct (pas de logique d'écho)

## 🔍 Diagnostic: Pourquoi "✅ Reçu:" apparaît encore?

### Hypothèse 1: Mauvais Service ECS répond

**Le webhook Telegram pointe peut-être vers le mauvais service.**

**Vérifier:**
1. Quel service ECS écoute sur `https://api.maisonganopa.com/telegram/webhook`?
2. Est-ce `ganopa-dev-bot-svc` ou `vancelian-dev-api-svc`?

**Comment vérifier:**
- AWS Console → ECS → Clusters → `vancelian-dev-api-cluster`
- Services → Lister tous les services
- Pour chaque service, vérifier:
  - Target Group → Health check path
  - Load Balancer → Rules → Path `/telegram/webhook`

**Solution:**
- Si le webhook pointe vers `vancelian-dev-api-svc` → Rediriger vers `ganopa-dev-bot-svc`
- Ou vérifier l'ALB routing rules

### Hypothèse 2: OpenAI échoue et retourne un message d'erreur qui ressemble à un écho

**Vérifier dans CloudWatch:**
- Chercher `openai_request_start` (doit être présent)
- Chercher `openai_request_error` ou `openai_request_done`
- Vérifier le message d'erreur retourné

**Si OpenAI échoue:**
- Vérifier `OPENAI_API_KEY` dans la Task Definition
- Vérifier les logs pour voir l'erreur exacte

### Hypothèse 3: Exception silencieuse dans process_telegram_update

**Vérifier dans CloudWatch:**
- Chercher `telegram_update_processing_failed`
- Vérifier l'erreur

**Si exception:**
- Le code crash avant d'appeler OpenAI
- Vérifier les logs pour l'erreur exacte

### Hypothèse 4: Ancien code dans un autre endpoint

**Vérifier:**
- Y a-t-il un autre endpoint `/telegram/webhook` ailleurs?
- Dans `agent_gateway` par exemple?

## 🎯 Test Définitif: Mode Signature

**Pour prouver quelle version tourne:**

1. **Activer le mode test dans ECS:**
   - Task Definition → `ganopa-dev-bot-svc` (dernière révision)
   - Container `ganopa-bot` → Environment variables
   - Ajouter: `BOT_SIGNATURE_TEST=1`
   - Enregistrer nouvelle révision

2. **Mettre à jour le service:**
   - Services → `ganopa-dev-bot-svc` → Update service
   - Sélectionner nouvelle révision
   - Force new deployment
   - Attendre stabilisation

3. **Tester:**
   - Envoyer message Telegram
   - **Attendu:** `✅ VERSION-TEST-123 | build-YYYYMMDD-HHMMSS`

4. **Résultats possibles:**

   **A) Vous voyez `✅ VERSION-TEST-123 | build-...`:**
   - ✅ Le nouveau code tourne
   - Le problème est ailleurs (OpenAI API key, etc.)
   - Désactiver le mode test et vérifier OpenAI

   **B) Vous voyez toujours "✅ Reçu:":**
   - ❌ L'ancien code tourne encore
   - Vérifier que le bon service ECS est mis à jour
   - Vérifier l'IMAGE URI de la task

   **C) Pas de réponse ou autre message:**
   - ❌ Le mauvais service répond
   - Vérifier le routing ALB

## 📊 Checklist de Vérification

### 1. Vérifier le Service ECS qui répond

**Question:** Quel service ECS est derrière `https://api.maisonganopa.com/telegram/webhook`?

**Comment trouver:**
- AWS Console → EC2 → Load Balancers
- Chercher l'ALB qui sert `api.maisonganopa.com`
- Voir les Target Groups
- Vérifier quel service ECS est dans le target group pour `/telegram/webhook`

### 2. Vérifier les Logs CloudWatch

**Chercher dans `/aws/ecs/ganopa-dev-bot`:**

```bash
# Logs récents
aws logs tail /aws/ecs/ganopa-dev-bot \
  --region me-central-1 \
  --since 30m \
  --format short
```

**Chercher spécifiquement:**
- `ganopa_bot_started` → Confirme que le service démarre
- `telegram_update_received` → Confirme que le webhook arrive
- `telegram_message_processing` → Confirme que le message est traité
- `openai_request_start` → Confirme qu'OpenAI est appelé
- `openai_request_error` → Si présent, voir l'erreur
- `telegram_send_done` → Confirme que la réponse est envoyée

### 3. Vérifier l'Image Déployée

**Dans AWS Console:**
- ECS → Services → `ganopa-dev-bot-svc`
- Tasks → Cliquer sur task RUNNING
- Containers → Voir IMAGE URI
- Extraire le tag (après `:`)

**Comparer avec:**
```bash
git rev-parse HEAD
# Doit être: c78b569deb97e4924b66d3d8fb6054dbf69cdb9f
```

**Si différent:**
- L'ancienne image tourne encore
- Forcer un nouveau déploiement

### 4. Test Direct: Endpoint /health

**Tester:**
```bash
curl https://api.maisonganopa.com/health
```

**Attendu:**
```json
{
  "status": "ok",
  "service": "ganopa-bot",
  "ts": "..."
}
```

**Si vous voyez un autre service:**
- Le mauvais service répond
- Vérifier le routing ALB

## 🚨 Action Immédiate

**Testez le mode signature maintenant:**

1. AWS Console → ECS → Task Definitions
2. Chercher `ganopa-dev-bot-svc` (dernière révision)
3. Container `ganopa-bot` → Environment variables
4. Ajouter: `BOT_SIGNATURE_TEST` = `1`
5. Enregistrer nouvelle révision
6. Services → `ganopa-dev-bot-svc` → Update service
7. Sélectionner nouvelle révision + Force new deployment
8. Attendre 2-3 minutes
9. Envoyer message Telegram

**Résultat attendu:** `✅ VERSION-TEST-123 | build-YYYYMMDD-HHMMSS`

**Si vous voyez ça:** Le nouveau code tourne, le problème est ailleurs (probablement OpenAI API key manquante ou invalide).

**Si vous voyez toujours "✅ Reçu:":** Le mauvais service répond ou l'ancienne image tourne encore.

