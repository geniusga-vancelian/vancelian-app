# Contrats API - Vancelian App

## TL;DR

Contrats d'API pour tous les endpoints (webhook Telegram, `/health`, `/_meta`). Format: Request/Response avec exemples JSON. Headers, codes retour, erreurs.

---

## Ce qui est vrai aujourd'hui

### Endpoints Disponibles

| Méthode | Path | Description | Auth |
|---------|------|-------------|------|
| `GET` | `/health` | Health check | Aucune |
| `GET` | `/_meta` | Version + config | Aucune |
| `GET` | `/telegram/webhook` | Webhook verification | Aucune |
| `POST` | `/telegram/webhook` | Webhook Telegram | Secret header (optionnel) |

---

## GET /health

### Request

**Méthode:** `GET`

**Path:** `/health`

**Headers:**
- Aucun requis

**Query Parameters:**
- Aucun

**Body:**
- Aucun

### Response

**Codes retour:**
- `200 OK`: Service opérationnel

**Headers:**
```
X-Ganopa-Build-Id: dev
X-Ganopa-Version: ganopa-bot-7f22c89b
Content-Type: application/json
```

**Body:**
```json
{
  "status": "ok",
  "service": "ganopa-bot",
  "ts": "2025-12-29T12:00:00Z"
}
```

### Exemple

```bash
curl -v https://api.maisonganopa.com/health
```

**Réponse attendue:**
```
HTTP/1.1 200 OK
X-Ganopa-Build-Id: dev
X-Ganopa-Version: ganopa-bot-7f22c89b
Content-Type: application/json

{
  "status": "ok",
  "service": "ganopa-bot",
  "ts": "2025-12-29T12:00:00Z"
}
```

---

## GET /_meta

### Request

**Méthode:** `GET`

**Path:** `/_meta`

**Headers:**
- Aucun requis

**Query Parameters:**
- Aucun

**Body:**
- Aucun

### Response

**Codes retour:**
- `200 OK`: Succès

**Headers:**
```
X-Ganopa-Build-Id: dev
X-Ganopa-Version: ganopa-bot-7f22c89b
Content-Type: application/json
```

**Body:**
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

**Champs:**
- `service` (string): Nom du service ("ganopa-bot")
- `version` (string): Version hash (ex: "ganopa-bot-7f22c89b")
- `build_id` (string): Build ID depuis env var (default: "dev")
- `hostname` (string): Hostname du container
- `openai_model` (string): Modèle OpenAI configuré (default: "gpt-4o-mini")
- `has_openai_key` (boolean): True si OPENAI_API_KEY configurée
- `has_webhook_secret` (boolean): True si WEBHOOK_SECRET configuré
- `ts` (string): Timestamp ISO 8601 UTC

### Exemple

```bash
curl -s https://api.maisonganopa.com/_meta | jq
```

**Réponse attendue:**
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

---

## GET /telegram/webhook

### Request

**Méthode:** `GET`

**Path:** `/telegram/webhook`

**Headers:**
- Aucun requis

**Query Parameters:**
- Aucun

**Body:**
- Aucun

### Response

**Codes retour:**
- `200 OK`: Succès

**Body:**
```json
{
  "ok": true,
  "hint": "Telegram webhook expects POST"
}
```

### Exemple

```bash
curl -s https://api.maisonganopa.com/telegram/webhook
```

**Réponse attendue:**
```json
{
  "ok": true,
  "hint": "Telegram webhook expects POST"
}
```

---

## POST /telegram/webhook

### Request

**Méthode:** `POST`

**Path:** `/telegram/webhook`

**Headers:**
```
Content-Type: application/json
X-Telegram-Bot-Api-Secret-Token: Azerty0334  # Optionnel si WEBHOOK_SECRET configuré
```

**Query Parameters:**
- Aucun

**Body (Telegram Update):**
```json
{
  "update_id": 123456789,
  "message": {
    "message_id": 1,
    "from": {
      "id": 123456,
      "is_bot": false,
      "first_name": "John",
      "last_name": "Doe",
      "username": "johndoe"
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

**Structure minimale:**
```json
{
  "update_id": 123456789,
  "message": {
    "message_id": 1,
    "from": {
      "id": 123456,
      "is_bot": false
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

### Response

**Codes retour:**
- `200 OK`: Webhook reçu, traitement en cours (réponse immédiate)
- `400 Bad Request`: JSON invalide
- `401 Unauthorized`: Secret token incorrect ou manquant

**Headers:**
```
Content-Type: application/json
```

**Body (succès):**
```json
{
  "ok": true
}
```

**Body (erreur 400):**
```json
{
  "detail": "Invalid JSON payload"
}
```

**Body (erreur 401):**
```json
{
  "detail": "Invalid Telegram secret token"
}
```

### Comportement

1. **Réponse immédiate:** Le bot répond `{"ok": true}` dans les 5 secondes (requis par Telegram)
2. **Traitement asynchrone:** Le traitement (parse → OpenAI → sendMessage) se fait en BackgroundTasks
3. **Pas de réponse de traitement:** Le body ne contient pas le résultat du traitement (traitement en arrière-plan)

### Exemple

```bash
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

**Réponse attendue:**
```json
{
  "ok": true
}
```

**Note:** Le traitement (appel OpenAI, envoi Telegram) se fait en arrière-plan. Vérifier les logs CloudWatch pour le résultat.

---

## Erreurs Communes

### 400 Bad Request

**Cause:** JSON invalide ou malformé.

**Exemple:**
```json
{
  "detail": "Invalid JSON payload"
}
```

**Fix:**
- Vérifier que le body est du JSON valide
- Vérifier que `Content-Type: application/json` est présent

---

### 401 Unauthorized

**Cause:** Secret token incorrect ou manquant (si `WEBHOOK_SECRET` configuré).

**Exemple:**
```json
{
  "detail": "Invalid Telegram secret token"
}
```

**Fix:**
- Vérifier que le header `X-Telegram-Bot-Api-Secret-Token` est présent
- Vérifier que la valeur correspond à `WEBHOOK_SECRET` dans ECS Task Definition
- Si `WEBHOOK_SECRET` n'est pas configuré, le header n'est pas requis

---

### 503 Service Unavailable

**Cause:** Aucun target healthy dans le Target Group (ALB ne peut pas forward).

**Fix:**
- Vérifier le Target Group (au moins 1 target healthy)
- Vérifier le service ECS (running count >= 1)
- Vérifier les Security Groups (ALB → Tasks)

**Référence:**
- `docs/RUNBOOK.md` → Runbook 2: /telegram/webhook renvoie 503/504

---

## Endpoints Internes (TBD)

### Agent Gateway (Futur)

**Description:** Endpoint interne pour communication entre services.

**Status:** ❌ Non implémenté

**À compléter quand ajouté:**
- Path
- Méthode
- Auth (si nécessaire)
- Request/Response format

---

## À vérifier quand ça casse

### Un contrat ne correspond pas à l'implémentation

1. Vérifier le code (`services/ganopa-bot/app/main.py`)
2. Tester l'endpoint avec `curl`
3. Mettre à jour ce document avec le contrat réel

### Un nouvel endpoint est ajouté

1. Ajouter le contrat dans ce fichier
2. Documenter Request/Response avec exemples
3. Tester l'endpoint

---

**Dernière mise à jour:** 2025-12-29

