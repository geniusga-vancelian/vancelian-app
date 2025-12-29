# Architecture - Vancelian App

## TL;DR

Repo monorepo avec service principal `ganopa-bot` (FastAPI) déployé sur AWS ECS Fargate. Webhook Telegram via ALB → Target Group → ECS tasks (port 8000). Réponses générées par OpenAI. CI/CD via GitHub Actions (build Docker → ECR → update ECS service).

---

## Ce qui est vrai aujourd'hui

### Structure du Repo

```
vancelian-app/
├── services/
│   └── ganopa-bot/          # Service principal (FastAPI)
│       ├── app/
│       │   ├── main.py      # FastAPI app, webhook handler
│       │   ├── config.py    # Env vars management
│       │   └── telegram_handlers.py  # Command routing
│       ├── Dockerfile        # Python 3.12-slim, uvicorn
│       └── requirements.txt  # fastapi, uvicorn, httpx
├── agent_gateway/           # Service secondaire (commandes GitHub)
├── .github/workflows/
│   └── deploy-ganopa-bot.yml  # CI/CD ECS Fargate
└── docs/                    # Documentation (ce dossier)
```

### Flux de Traitement

```
Telegram User
    │
    │ POST /telegram/webhook
    ▼
Route53 (api.maisonganopa.com)
    │
    ▼
ACM Certificate (HTTPS)
    │
    ▼
ALB (Application Load Balancer)
    │
    │ Listener 443 → Rule: Path is /telegram/webhook
    ▼
Target Group (ganopa-dev-bot-tg)
    │
    │ Type: IP, Port: 8000, Health: /health
    ▼
ECS Service (ganopa-dev-bot-svc)
    │
    │ Task Definition → Container: ganopa-bot:8000
    ▼
ECS Task (Fargate)
    │
    │ FastAPI (uvicorn app.main:app --host 0.0.0.0 --port 8000)
    ▼
Background Task (FastAPI BackgroundTasks)
    │
    │ 1. Parse update → chat_id, text, user_id, is_bot
    │ 2. Dedupe (cache 5min)
    │ 3. Guard: ignore bots, empty messages
    │ 4. Route: /start, /help, /status → handler
    │    OU call OpenAI → response
    │ 5. Truncate (max 3500 chars)
    │ 6. Send to Telegram
    ▼
Telegram API (sendMessage)
    │
    ▼
Telegram User (réponse avec prefix 🤖)
```

### Ports et Paths

| Port | Path | Méthode | Description |
|------|------|---------|-------------|
| 8000 | `/health` | GET | Health check (ALB + ECS) |
| 8000 | `/_meta` | GET | Version + config (proof-of-deploy) |
| 8000 | `/telegram/webhook` | GET | Webhook verification |
| 8000 | `/telegram/webhook` | POST | Webhook Telegram (avec secret header) |

### Observabilité

**CloudWatch Logs:**
- Log Group: `/ecs/ganopa-dev-bot-task` (ou similaire selon config)
- Format: Structured logs avec `correlation_id`, `update_id`, `chat_id`
- Events clés:
  - `ganopa_bot_started` (version, build_id, has_openai_key)
  - `webhook_received` → `secret_ok` → `update_parsed`
  - `message_extracted` → `openai_called` → `openai_ok` → `telegram_sent`
  - `command_start`, `command_help`, `command_status`
  - `update_ignored_bot`, `update_ignored_empty`, `update_duplicate`

**Corrélation:**
- Tous les logs d'un même update partagent le même `correlation_id` (format: `upd-{update_id}`)

**Version Tracking:**
- Endpoint `/_meta` retourne `version` (hash basé sur SERVICE_NAME + BUILD_ID)
- Headers HTTP: `X-Ganopa-Build-Id`, `X-Ganopa-Version`

### Infrastructure AWS

**Réseau:**
- Route53: `api.maisonganopa.com` → ALB DNS
- ACM: Certificate pour HTTPS
- ALB: Listener 443 (HTTPS) avec règles de routing
- Security Groups:
  - ALB SG: Inbound 443 (HTTPS) depuis Internet
  - Tasks SG: Inbound 8000 depuis ALB SG

**Compute:**
- ECS Cluster: `vancelian-dev-api-cluster`
- ECS Service: `ganopa-dev-bot-svc`
- Launch Type: Fargate
- Desired Count: 1
- Task Definition: `ganopa-bot:XX` (révision)

**Load Balancing:**
- Target Group: `ganopa-dev-bot-tg` (ou similaire)
- Type: IP (pas Instance)
- Protocol: HTTP
- Port: 8000
- Health Check: `/health` sur port 8000
- Targets: IPs des tasks ECS (enregistrées automatiquement)

**Container Registry:**
- ECR: `411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot`
- Image Tag: `{GITHUB_SHA}` (commit hash)

### CI/CD

**GitHub Actions Workflow:** `.github/workflows/deploy-ganopa-bot.yml`

**Flow:**
1. Trigger: Push sur `main` avec changements dans `services/ganopa-bot/**`
2. Checkout code (ref: `${{ github.sha }}`)
3. Configure AWS credentials (OIDC)
4. Resolve env → ECS names (dev/staging/prod)
5. Sanity check: ECS service exists
6. Ensure ECR repo exists
7. Login to ECR
8. Build Docker image (--no-cache) + verify files
9. Push to ECR (tag: `{GITHUB_SHA}`)
10. Fetch current task definition
11. Patch task definition (container image)
12. Register new task definition revision
13. Wait for service to be ACTIVE (si INACTIVE)
14. Update ECS service (force new deployment)
15. Wait for service to stabilize
16. Print service status

**OIDC:**
- Role: `arn:aws:iam::411714852748:role/GitHubDeployRole`
- Region: `me-central-1`

---

## À vérifier quand ça casse

### Le webhook ne répond pas (503/504)

1. **ALB Routing:**
   - Vérifier que la règle ALB pour `/telegram/webhook` existe
   - Vérifier que la règle forward vers le bon Target Group
   - Vérifier l'ordre des règles (la première qui correspond est utilisée)

2. **Target Group:**
   - Vérifier qu'il y a au moins 1 target healthy
   - Vérifier que les targets sont enregistrés (IPs des tasks)
   - Vérifier le health check path (`/health`) et port (8000)

3. **ECS Service:**
   - Vérifier que le service est ACTIVE (pas INACTIVE)
   - Vérifier que `runningCount >= 1`
   - Vérifier que le service est attaché au Target Group

4. **Security Groups:**
   - Vérifier que le Tasks SG autorise le trafic depuis ALB SG sur port 8000
   - Vérifier que l'ALB SG autorise le trafic HTTPS (443) depuis Internet

### Le bot répond en echo (au lieu de l'IA)

1. **Code déployé:**
   - Vérifier `/_meta` pour confirmer la version
   - Vérifier que l'image Docker tag correspond au dernier commit
   - Vérifier que le service ECS utilise la bonne Task Definition revision

2. **Routing ALB:**
   - Vérifier que `/telegram/webhook` pointe vers `ganopa-dev-bot-svc` (pas `agent_gateway`)

3. **Logs CloudWatch:**
   - Vérifier que `openai_called` est présent (pas seulement `message_extracted`)
   - Vérifier que `openai_ok` est présent (pas `openai_error`)

### Les logs ne sont pas structurés

1. **Version déployée:**
   - Vérifier que le code contient les nouveaux logs (`correlation_id`, etc.)
   - Vérifier `/_meta` pour confirmer la version

2. **CloudWatch:**
   - Vérifier que le log group existe
   - Vérifier les permissions IAM du task role

---

## Schéma ASCII Complet

```
┌─────────────────┐
│ Telegram User   │
└────────┬────────┘
         │ POST /telegram/webhook
         │ (X-Telegram-Bot-Api-Secret-Token)
         ▼
┌─────────────────┐
│ Route53         │ api.maisonganopa.com
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ACM Certificate │ HTTPS
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ALB             │ Listener 443
│                 │ Rule: Path is /telegram/webhook
└────────┬────────┘
         │ Forward to Target Group
         ▼
┌─────────────────┐
│ Target Group    │ ganopa-dev-bot-tg
│ (Type: IP)      │ Port: 8000
│ Health: /health │
└────────┬────────┘
         │ Registered IPs (auto by ECS)
         ▼
┌─────────────────┐
│ ECS Service     │ ganopa-dev-bot-svc
│ (Fargate)       │ Desired: 1
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ECS Task        │ Container: ganopa-bot
│ Port: 8000      │ Image: ECR/{GITHUB_SHA}
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ FastAPI         │ uvicorn app.main:app
│ (Background)    │ --host 0.0.0.0 --port 8000
└────────┬────────┘
         │
         ├─→ Parse update
         ├─→ Dedupe (cache 5min)
         ├─→ Guard (bots, empty)
         ├─→ Route command OR
         │   └─→ OpenAI API (gpt-4o-mini)
         ├─→ Truncate (3500 chars)
         └─→ Send to Telegram
         │
         ▼
┌─────────────────┐
│ Telegram API    │ sendMessage
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Telegram User   │ Réponse avec prefix 🤖
└─────────────────┘
```

---

**Dernière mise à jour:** 2025-12-29

