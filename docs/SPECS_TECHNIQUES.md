# Spécifications Techniques - Vancelian App

## TL;DR

Service FastAPI (`ganopa-bot`) déployé sur ECS Fargate, accessible via ALB. Webhook Telegram → BackgroundTasks → OpenAI → Telegram. Secrets via ECS Task Definition env vars. Observabilité via CloudWatch logs structurés. CI/CD via GitHub Actions (build Docker → ECR → update ECS).

---

## Ce qui est vrai aujourd'hui

### Architecture Runtime

```
Internet (HTTPS)
    │
    ▼
Route53 (api.maisonganopa.com)
    │
    ▼
ACM Certificate
    │
    ▼
ALB (Application Load Balancer)
    │ Listener 443
    │ Rule: Path is /telegram/webhook → Target Group
    ▼
Target Group (Type: IP, Port: 8000)
    │ Health Check: /health
    ▼
ECS Service (ganopa-dev-bot-svc)
    │ Fargate, Desired: 1
    ▼
ECS Task (Container: ganopa-bot)
    │ Port: 8000
    │ Image: ECR/{GITHUB_SHA}
    ▼
FastAPI (uvicorn app.main:app)
    │ --host 0.0.0.0 --port 8000
    │
    ├─→ BackgroundTasks (asynchrone)
    │   │
    │   ├─→ Parse update
    │   ├─→ Dedupe (cache 5min)
    │   ├─→ Guard (bots, empty)
    │   ├─→ Route command OR
    │   │   └─→ OpenAI API (gpt-4o-mini)
    │   ├─→ Truncate (3500 chars)
    │   └─→ Telegram API (sendMessage)
    │
    └─→ Réponse immédiate: {"ok": true}
```

---

## Endpoints

### GET /health

**Description:** Health check endpoint pour ALB et ECS.

**Méthode:** `GET`

**Path:** `/health`

**Headers de réponse:**
- `X-Ganopa-Build-Id`: Build ID
- `X-Ganopa-Version`: Version (hash)

**Codes retour:**
- `200 OK`: Service opérationnel
- `503 Service Unavailable`: Service indisponible (si health check échoue)

**Body de réponse:**
```json
{
  "status": "ok",
  "service": "ganopa-bot",
  "ts": "2025-12-29T12:00:00Z"
}
```

**Usage:**
- ALB health check
- ECS health check
- Monitoring externe

---

### GET /_meta

**Description:** Endpoint de vérification de version et configuration.

**Méthode:** `GET`

**Path:** `/_meta`

**Headers de réponse:**
- `X-Ganopa-Build-Id`: Build ID
- `X-Ganopa-Version`: Version (hash)

**Codes retour:**
- `200 OK`: Succès

**Body de réponse:**
```json
{
  "service": "ganopa-bot",
  "version": "ganopa-bot-7f22c89b",
  "build_id": "dev",
  "hostname": "ip-10-0-1-123",
  "openai_model": "gpt-4o-mini",
  "has_openai_key": true,
  "has_webhook_secret": true,
  "ts": "2025-12-29T12:00:00Z"
}
```

**Usage:**
- Vérification de version déployée
- Debug de configuration
- Proof-of-deploy

---

### GET /telegram/webhook

**Description:** Endpoint de vérification d'URL webhook (Telegram).

**Méthode:** `GET`

**Path:** `/telegram/webhook`

**Codes retour:**
- `200 OK`: Succès

**Body de réponse:**
```json
{
  "ok": true,
  "hint": "Telegram webhook expects POST"
}
```

**Usage:**
- Vérification manuelle de l'URL webhook
- Test de connectivité

---

### POST /telegram/webhook

**Description:** Endpoint webhook Telegram pour recevoir les updates.

**Méthode:** `POST`

**Path:** `/telegram/webhook`

**Headers requis:**
- `Content-Type: application/json`
- `X-Telegram-Bot-Api-Secret-Token`: Secret token (si `WEBHOOK_SECRET` configuré)

**Body (Telegram Update):**
```json
{
  "update_id": 123456789,
  "message": {
    "message_id": 1,
    "from": {
      "id": 123456,
      "is_bot": false,
      "first_name": "John"
    },
    "chat": {
      "id": 123456,
      "type": "private"
    },
    "date": 1234567890,
    "text": "Hello"
  }
}
```

**Codes retour:**
- `200 OK`: Webhook reçu, traitement en cours (réponse immédiate)
- `400 Bad Request`: JSON invalide
- `401 Unauthorized`: Secret token incorrect ou manquant

**Body de réponse:**
```json
{
  "ok": true
}
```

**Comportement:**
- Réponse immédiate (`{"ok": true}`) dans les 5 secondes (requis par Telegram)
- Traitement asynchrone en BackgroundTasks
- Pas de réponse de traitement dans le body (traitement en arrière-plan)

**Usage:**
- Webhook Telegram officiel
- Tests manuels avec `curl`

---

## Variables d'Environnement

### Requises

| Variable | Description | Exemple | Où configurer |
|---------|------------|---------|---------------|
| `TELEGRAM_BOT_TOKEN` | Token du bot Telegram | `123456:ABC-DEF...` | ECS Task Definition |
| `OPENAI_API_KEY` | Clé API OpenAI | `sk-...` | ECS Task Definition |

### Optionnelles

| Variable | Description | Default | Où configurer |
|----------|-------------|---------|---------------|
| `WEBHOOK_SECRET` | Secret token pour webhook | `""` (désactivé) | ECS Task Definition |
| `OPENAI_MODEL` | Modèle OpenAI à utiliser | `"gpt-4o-mini"` | ECS Task Definition |
| `BUILD_ID` | Identifiant de build | `"dev"` | ECS Task Definition |
| `PORT` | Port d'écoute | `"8000"` | ECS Task Definition |
| `BOT_SIGNATURE_TEST` | Mode test (réponse fixe) | `false` | ECS Task Definition |

**Format:**
- Toutes les variables sont des strings
- `BOT_SIGNATURE_TEST`: `"1"` ou `"true"` pour activer, sinon `"0"` ou `"false"`

**Sécurité:**
- Secrets stockés dans ECS Task Definition (env vars)
- Pas de secrets dans le code
- Pas de secrets dans les logs (seulement booléens)

---

## Sécurité

### Telegram Secret Header

**Protection:** Header `X-Telegram-Bot-Api-Secret-Token`

**Configuration:**
- Variable d'environnement: `WEBHOOK_SECRET`
- Si configuré, le header est vérifié à chaque webhook
- Si non configuré, le webhook accepte tous les appels (mode dev)

**Comportement:**
- Secret correct → Traitement normal
- Secret incorrect ou manquant → HTTP 401, message ignoré

**Référence:**
- Code: `services/ganopa-bot/app/main.py` → `_verify_webhook_secret()`

---

### Stockage des Secrets

**Actuel (MVP):**
- Secrets dans ECS Task Definition → Environment variables
- Pas de rotation automatique
- Accès via AWS Console ou CLI

**Futur (recommandé):**
- Migration vers AWS Secrets Manager
- Rotation automatique
- Audit des accès

**Référence:**
- ADR-0002: Secrets via ECS Task Definition env vars (`docs/DECISIONS.md`)

---

## Observabilité

### Logs Structurés

**Format:**
- Log group: `/ecs/ganopa-dev-bot-task` (ou similaire)
- Format: Structured logs avec `extra={}` (key-value pairs)
- Pas de secrets dans les logs (seulement booléens)

**Events clés:**
- `ganopa_bot_started`: Démarrage du service (version, build_id, config)
- `webhook_received`: Réception webhook (correlation_id, path)
- `secret_ok`: Vérification secret (correlation_id, secret_ok)
- `update_parsed`: Parsing JSON (correlation_id, update_id)
- `message_extracted`: Extraction message (correlation_id, chat_id, text_preview)
- `openai_called`: Appel OpenAI (correlation_id, model, text_len)
- `openai_ok`: Succès OpenAI (correlation_id, response_len, tokens_used, latency_ms)
- `openai_error`: Erreur OpenAI (correlation_id, error, error_type)
- `telegram_sent`: Envoi Telegram (correlation_id, status_code)
- `command_start`, `command_help`, `command_status`: Commandes Telegram

**Corrélation:**
- Tous les logs d'un même update partagent le même `correlation_id` (format: `upd-{update_id}`)

**Référence:**
- Code: `services/ganopa-bot/app/main.py` → Tous les `logger.info/error()` avec `extra={}`

---

### Endpoint /_meta

**Usage:**
- Vérification de version déployée
- Debug de configuration
- Proof-of-deploy

**Référence:**
- Code: `services/ganopa-bot/app/main.py` → `@app.get("/_meta")`
- ADR-0003: Proof-of-deploy via /_meta (`docs/DECISIONS.md`)

---

### Corrélation par Version

**Mécanisme:**
- Constante `VERSION` générée au démarrage (hash basé sur SERVICE_NAME + BUILD_ID)
- Loggé dans `ganopa_bot_started`
- Retourné dans `/_meta`
- Header HTTP `X-Ganopa-Version` sur `/health` et `/_meta`

**Usage:**
- Identifier rapidement la version déployée
- Vérifier que le bon code tourne
- Debug de problèmes de déploiement

---

## CI/CD

### Build & Push ECR

**Workflow:** `.github/workflows/deploy-ganopa-bot.yml`

**Étapes:**
1. Checkout code (ref: `${{ github.sha }}`)
2. Configure AWS credentials (OIDC)
3. Resolve env → ECS names
4. Sanity check: ECS service exists
5. Ensure ECR repository exists
6. Login to ECR
7. Build Docker image (`--no-cache`) + verify files
8. Push to ECR (tag: `{GITHUB_SHA}`)

**Image URI:**
- Format: `411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:{GITHUB_SHA}`
- Tag: Commit hash (ex: `a35db8b`)

**Référence:**
- Workflow: `.github/workflows/deploy-ganopa-bot.yml` → Step "Build & push Docker image"

---

### Update Service ECS

**Workflow:** `.github/workflows/deploy-ganopa-bot.yml`

**Étapes:**
1. Fetch current task definition ARN
2. Download task definition JSON
3. Patch task definition (container image)
4. Register new task definition revision
5. Wait for service to be ACTIVE (si INACTIVE)
6. Update ECS service (force new deployment)
7. Wait for service to stabilize
8. Print service status

**Référence:**
- Workflow: `.github/workflows/deploy-ganopa-bot.yml` → Steps "Register new task definition" → "Update ECS service"

---

## Risques Connus + Mitigations

### Risque 1: Timeout Telegram

**Risque:** Telegram requiert une réponse dans les 5 secondes, mais OpenAI peut prendre jusqu'à 20 secondes.

**Mitigation:**
- ✅ Réponse immédiate avec `{"ok": true}` (BackgroundTasks)
- ✅ Traitement asynchrone en arrière-plan

**Référence:**
- ADR-0001: Webhook Telegram via ALB + ECS (BackgroundTasks) (`docs/DECISIONS.md`)

---

### Risque 2: Secrets dans Task Definition

**Risque:** Secrets visibles dans la Task Definition (bien que sécurisée par AWS).

**Mitigation:**
- ✅ Pas de secrets dans le code
- ✅ Pas de secrets dans les logs
- 🔄 Migration future vers AWS Secrets Manager

**Référence:**
- ADR-0002: Secrets via ECS Task Definition env vars (`docs/DECISIONS.md`)

---

### Risque 3: Cache Deduplication Perdu au Redémarrage

**Risque:** Cache en mémoire perdu si le container redémarre, possibilité de traiter le même update deux fois.

**Mitigation:**
- ✅ TTL de 5 minutes (Telegram ne renvoie généralement pas après 5 min)
- ⚠️ Acceptable pour MVP
- 🔄 Migration future vers Redis/DynamoDB si besoin

**Référence:**
- ADR-0004: Deduplication in-memory (5min TTL) (`docs/DECISIONS.md`)

---

### Risque 4: Pas de Retry Automatique

**Risque:** Si le BackgroundTask échoue, pas de retry automatique.

**Mitigation:**
- ✅ Logs complets pour diagnostic
- ✅ Gestion d'erreurs complète dans `process_telegram_update_safe()`
- ⚠️ Acceptable pour MVP
- 🔄 Migration future vers queue (SQS) avec retry si besoin

---

## À vérifier quand ça casse

### Un endpoint ne répond pas

1. Vérifier le routing ALB (règle pour le path)
2. Vérifier le Target Group (targets healthy)
3. Vérifier le service ECS (running count >= 1)
4. Vérifier les logs CloudWatch pour erreurs

### Les logs ne sont pas structurés

1. Vérifier la version déployée (`/_meta`)
2. Vérifier que le code contient les nouveaux logs
3. Vérifier les permissions IAM du task role (CloudWatch)

### Le déploiement échoue

1. Vérifier le workflow GitHub Actions (logs)
2. Vérifier les permissions OIDC (GitHub → AWS)
3. Vérifier que l'ECR repository existe
4. Vérifier que le service ECS existe

---

**Dernière mise à jour:** 2025-12-29

