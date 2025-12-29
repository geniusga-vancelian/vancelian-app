# Checklist - Vancelian App

## TL;DR

Checklists actionnables pour pré-commit, pré-deploy, et post-deploy. Format: cases à cocher avec commandes exactes.

---

## Ce qui est vrai aujourd'hui

### Checklist Pré-Commit

**Avant de committer du code dans `services/ganopa-bot/`:**

- [ ] **Formatage Python:**
  ```bash
  cd services/ganopa-bot
  python3 -m compileall app -q
  ```
  - ✅ Pas d'erreur de compilation

- [ ] **Vérification des imports:**
  ```bash
  cd services/ganopa-bot
  python3 -c "from app.main import app; from app.config import SERVICE_NAME; print('OK')"
  ```
  - ✅ Pas d'erreur d'import

- [ ] **Tests locaux (optionnel mais recommandé):**
  ```bash
  cd services/ganopa-bot
  export TELEGRAM_BOT_TOKEN=test
  export OPENAI_API_KEY=test
  export WEBHOOK_SECRET=test
  ./lint_python.sh
  ```
  - ✅ Lint passe

- [ ] **Vérification des secrets:**
  - ✅ Aucun secret hardcodé dans le code
  - ✅ Seulement des booléens dans les logs (`has_openai_key`, pas la valeur)
  - ✅ Variables d'environnement utilisées (`getenv()`, `getenv_required()`)

- [ ] **Vérification des logs:**
  - ✅ Tous les logs ont `correlation_id`
  - ✅ Tous les logs ont `update_id` et `chat_id` (si disponibles)
  - ✅ Noms de logs clairs (`webhook_received`, `openai_called`, etc.)

- [ ] **Vérification du code:**
  - ✅ Pas de code "echo fallback" (`return f"✅ Reçu: {text}"`)
  - ✅ Prefix "🤖" sur toutes les réponses OpenAI
  - ✅ Garde-fous: ignore bots, empty messages, limite taille

---

### Checklist Pré-Deploy

**Avant de merger sur `main` (qui déclenche le déploiement):**

- [ ] **Variables d'environnement ECS:**
  - ✅ `TELEGRAM_BOT_TOKEN` (required)
  - ✅ `OPENAI_API_KEY` (required pour réponses IA)
  - ✅ `WEBHOOK_SECRET` (optional, mais recommandé)
  - ✅ `OPENAI_MODEL` (default: "gpt-4o-mini")
  - ✅ `BUILD_ID` (optionnel, default: "dev")
  - ✅ `PORT` (optionnel, default: "8000")

- [ ] **Dockerfile:**
  - ✅ Port exposé: `EXPOSE 8000`
  - ✅ CMD: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT}`
  - ✅ Fichiers Python copiés: `COPY app/ ./app/`
  - ✅ Vérification des fichiers: `test -f app/main.py`

- [ ] **Routes ALB:**
  - ✅ Règle pour `/telegram/webhook` → Target Group de `ganopa-dev-bot-svc`
  - ✅ Règle pour `/_meta` → Target Group de `ganopa-dev-bot-svc` (ou default)
  - ✅ Règle pour `/health` → Target Group de `ganopa-dev-bot-svc` (ou default)

- [ ] **GitHub Actions Workflow:**
  - ✅ Trigger: `paths: services/ganopa-bot/**`
  - ✅ Build sans cache: `--no-cache`
  - ✅ Vérification des fichiers avant build
  - ✅ Vérification des fichiers dans l'image

- [ ] **Code Review:**
  - ✅ Pas de secrets dans le code
  - ✅ Logs structurés
  - ✅ Gestion d'erreurs complète
  - ✅ Tests manuels effectués (si applicable)

---

### Checklist Post-Deploy

**Après le déploiement (workflow GitHub Actions terminé):**

- [ ] **Vérification de la version:**
  ```bash
  curl -s https://api.maisonganopa.com/_meta | jq '{service,version,build_id,has_openai_key}'
  ```
  - ✅ `service`: "ganopa-bot"
  - ✅ `version`: hash unique (ex: "ganopa-bot-7f22c89b")
  - ✅ `has_openai_key`: true
  - ✅ Headers `X-Ganopa-Build-Id` et `X-Ganopa-Version` présents

- [ ] **Health check:**
  ```bash
  curl -s https://api.maisonganopa.com/health | jq
  ```
  - ✅ Status: 200 OK
  - ✅ Body: `{"status": "ok", "service": "ganopa-bot"}`

- [ ] **Webhook GET:**
  ```bash
  curl -s https://api.maisonganopa.com/telegram/webhook
  ```
  - ✅ Status: 200 OK
  - ✅ Body: `{"ok": true, "hint": "Telegram webhook expects POST"}`

- [ ] **Test message Telegram:**
  - Envoyer "Hello" au bot
  - ✅ Réponse commence par "🤖" (preuve OpenAI)
  - ✅ Réponse différente de "Hello" (pas d'echo)

- [ ] **Logs CloudWatch:**
  ```bash
  aws logs tail /ecs/ganopa-dev-bot-task --region me-central-1 --since 5m \
    --format short --filter-pattern "ganopa_bot_started"
  ```
  - ✅ `ganopa_bot_started` avec `version` et `build_id`
  - ✅ Après message Telegram:
    - `webhook_received` → `secret_ok` → `update_parsed`
    - `message_extracted`
    - `openai_called` → `openai_ok` (ou `openai_error` si problème)
    - `telegram_sent`

- [ ] **Target Group:**
  ```bash
  TG_ARN=$(aws elbv2 describe-target-groups --region me-central-1 \
    --query 'TargetGroups[?contains(TargetGroupName, `ganopa`)].TargetGroupArn' --output text | head -1)
  aws elbv2 describe-target-health --region me-central-1 --target-group-arn "${TG_ARN}" \
    --query 'TargetHealthDescriptions[*].TargetHealth.State' --output text
  ```
  - ✅ Au moins 1 target "healthy"

- [ ] **ECS Service:**
  ```bash
  aws ecs describe-services --region me-central-1 \
    --cluster vancelian-dev-api-cluster --services ganopa-dev-bot-svc \
    --query 'services[0].{status:status,running:runningCount,desired:desiredCount}' \
    --output json | jq
  ```
  - ✅ `status`: "ACTIVE"
  - ✅ `running`: >= 1
  - ✅ `desired`: 1

- [ ] **Commandes Telegram:**
  - `/start` → Message d'accueil avec version
  - `/help` → Aide complète
  - `/status` → État du service

---

### Checklist de Validation Complète

**Checklist exhaustive pour validation complète du déploiement:**

- [ ] **Infrastructure:**
  - [ ] Route53: `api.maisonganopa.com` → ALB DNS
  - [ ] ACM: Certificate valide et attaché au listener 443
  - [ ] ALB: Listener 443 configuré
  - [ ] ALB Rules: `/telegram/webhook` → Target Group correct
  - [ ] Target Group: Type IP, Port 8000, Health `/health`
  - [ ] Target Group: Au moins 1 target healthy
  - [ ] Security Groups: ALB → Tasks (port 8000)
  - [ ] ECS Service: ACTIVE, running >= 1
  - [ ] ECS Service: Attaché au Target Group

- [ ] **Application:**
  - [ ] Endpoint `/health`: 200 OK
  - [ ] Endpoint `/_meta`: 200 OK avec version
  - [ ] Endpoint `/telegram/webhook` (GET): 200 OK
  - [ ] Endpoint `/telegram/webhook` (POST): 200 OK avec `{"ok": true}`
  - [ ] Message Telegram: Réponse avec prefix "🤖"
  - [ ] Commandes: `/start`, `/help`, `/status` fonctionnent

- [ ] **Observabilité:**
  - [ ] CloudWatch Logs: Log group existe
  - [ ] CloudWatch Logs: Logs structurés avec `correlation_id`
  - [ ] CloudWatch Logs: Tous les événements présents
  - [ ] Aucun secret dans les logs

- [ ] **Sécurité:**
  - [ ] Webhook secret configuré (`WEBHOOK_SECRET`)
  - [ ] Secrets dans Task Definition (pas dans le code)
  - [ ] Security Groups restrictifs

---

## À vérifier quand ça casse

### Une checklist ne couvre pas un cas

1. Ajouter une nouvelle case dans la checklist appropriée
2. Documenter la commande ou la procédure
3. Tester la checklist

### Une checklist est obsolète

1. Vérifier si les commandes fonctionnent encore
2. Mettre à jour avec les nouvelles commandes
3. Tester la checklist complète

---

**Dernière mise à jour:** 2025-12-29

