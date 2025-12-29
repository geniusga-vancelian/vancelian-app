# 🔍 Audit Complet du Projet Vancelian-App

**Date:** 2025-12-29  
**Objectif:** Diagnostic complet de l'architecture, du code, et de la configuration AWS

---

## 📊 1. ÉTAT GIT

### ✅ État Actuel
- **Branch:** `main`
- **Status:** À jour avec `origin/main`
- **Dernier commit:** `7425fda` - "fix: add wait step for service to be ACTIVE before update"
- **Pas de rebase en cours** ✅
- **Pas de conflits de merge** ✅

### ⚠️ Fichiers Non Commités
- `services/ganopa-bot/CODE_VERIFICATION.md` (modifié)
- `services/ganopa-bot/FIX_OLD_IMAGE.md` (modifié)
- `product/brainstorms/` (non tracké)
- `product/plans/` (non tracké)
- Plusieurs fichiers de documentation dans `services/ganopa-bot/` (non trackés)

**Recommandation:** Commiter ou ajouter à `.gitignore` les fichiers de documentation temporaires.

---

## 🏗️ 2. ARCHITECTURE DU PROJET

### Structure Principale

```
vancelian-app/
├── agent/                    # Agent principal (non utilisé actuellement)
├── agent_gateway/            # Service FastAPI pour commandes Telegram
├── services/
│   └── ganopa-bot/           # Service FastAPI pour bot AI Telegram
│       └── app/
│           ├── main.py       # Point d'entrée FastAPI
│           ├── config.py      # Configuration (env vars)
│           ├── ai_service.py # Service OpenAI
│           └── ai_prompt.py   # Prompts système
└── .github/workflows/        # CI/CD GitHub Actions
```

### Services Identifiés

#### A. `agent_gateway` (Service de Commandes)
- **Rôle:** Gestion des commandes Telegram (`/brainstorm`, `/plan`, `/qa`, `/ops`, `/deploy`)
- **Endpoint:** `/telegram/webhook` (conflit potentiel avec ganopa-bot)
- **Status:** Actif, répond sur `/health`

#### B. `ganopa-bot` (Service AI)
- **Rôle:** Bot Telegram avec réponses AI via OpenAI
- **Endpoint:** `/telegram/webhook` (conflit avec agent_gateway)
- **Status:** Déployé mais 503 sur `/telegram/webhook`

---

## 🔴 3. PROBLÈMES IDENTIFIÉS

### A. PROBLÈME CRITIQUE: Conflit de Routing ALB

**Symptôme:**
- ✅ `GET /health` → 200 (uvicorn) → Un service répond
- ❌ `GET /telegram/webhook` → 503 (awselb) → Pas de cibles saines

**Cause Racine:**
1. **Deux services utilisent le même endpoint `/telegram/webhook`:**
   - `agent_gateway` → `/telegram/webhook`
   - `ganopa-bot` → `/telegram/webhook`

2. **Configuration ALB incorrecte:**
   - La règle ALB pour `/telegram/webhook` pointe vers un Target Group vide ou incorrect
   - Le Target Group n'a pas de cibles enregistrées (0 targets)
   - Le service ECS `ganopa-dev-bot-svc` n'est pas attaché au Target Group

3. **Pattern ECS Fargate non respecté:**
   - Pour ECS Fargate, les Target Groups doivent être de type **IP**
   - Les IPs des tasks doivent être **enregistrées automatiquement** par ECS (via service attachment)
   - **NE PAS** enregistrer manuellement des IPs dans le Target Group

### B. PROBLÈME: Service ECS Potentiellement INACTIVE

**Symptôme:**
- Erreur `ServiceNotActiveException` dans le workflow GitHub Actions

**Cause:**
- Le service ECS `ganopa-dev-bot-svc` peut être dans l'état INACTIVE
- Un service INACTIVE ne peut pas être mis à jour

**Solution Appliquée:**
- ✅ Workflow modifié pour attendre que le service soit ACTIVE avant update

### C. PROBLÈME: Documentation Proliférante

**Observation:**
- 20+ fichiers de documentation dans `services/ganopa-bot/`
- Beaucoup de fichiers redondants ou obsolètes

**Recommandation:**
- Nettoyer et consolider la documentation
- Garder uniquement les guides essentiels

---

## 📝 4. ANALYSE DU CODE

### A. `services/ganopa-bot/app/main.py`

#### ✅ Points Positifs
- ✅ Code propre, pas de conflits de merge
- ✅ Utilisation correcte de `BackgroundTasks` pour traitement asynchrone
- ✅ Réponse immédiate au webhook Telegram (`{"ok": true}`)
- ✅ Logs structurés avec `extra={}`
- ✅ Protection contre les secrets logués (seulement booléens)
- ✅ Endpoints `/health` et `/_meta` pour debug
- ✅ Header `X-Ganopa-Build-Id` pour identification
- ✅ Timeouts explicites (OpenAI: 25s, Telegram: 10s)
- ✅ Gestion d'erreur si `OPENAI_API_KEY` manquante

#### ⚠️ Points d'Attention
- ⚠️ Pas de validation stricte du payload Telegram
- ⚠️ Pas de rate limiting
- ⚠️ Pas de retry logic pour OpenAI/Telegram

#### 🔍 Code Clé

```python
# Réponse immédiate au webhook
@app.post("/telegram/webhook")
async def telegram_webhook(...):
    # ... validation ...
    background_tasks.add_task(process_telegram_update_safe, update)
    return JSONResponse({"ok": True})  # ✅ Immédiat

# Traitement asynchrone
def process_telegram_update_safe(update: Dict[str, Any]) -> None:
    # ... traitement OpenAI ...
    send_telegram_message(chat_id, reply)
```

### B. `services/ganopa-bot/app/config.py`

#### ✅ Points Positifs
- ✅ Pas de `load_dotenv()` en production
- ✅ Variables d'environnement bien structurées
- ✅ `BUILD_ID` pour identification de version
- ✅ `SERVICE_NAME` pour logs

#### ⚠️ Points d'Attention
- ⚠️ `OPENAI_API_KEY` est optionnel (peut causer des erreurs silencieuses)
- ⚠️ Pas de validation des valeurs (ex: PORT doit être un nombre)

### C. `services/ganopa-bot/Dockerfile`

#### ✅ Points Positifs
- ✅ Vérification des fichiers Python dans l'image
- ✅ Utilisation de `$PORT` avec fallback
- ✅ `--host 0.0.0.0` pour écouter sur toutes les interfaces

#### ⚠️ Points d'Attention
- ⚠️ Pas de healthcheck explicite dans Dockerfile (mais ECS peut en avoir un)

---

## 🚀 5. WORKFLOW GITHUB ACTIONS

### A. `deploy-ganopa-bot.yml`

#### ✅ Points Positifs
- ✅ Trigger automatique sur push vers `services/ganopa-bot/**`
- ✅ Vérification des fichiers Python avant build
- ✅ Build sans cache (`--no-cache`) pour garantir le code à jour
- ✅ Vérification des fichiers dans l'image Docker
- ✅ Gestion du service INACTIVE (attente ACTIVE)
- ✅ Debug info si le service ne se stabilise pas

#### ⚠️ Points d'Attention
- ⚠️ Pas de rollback automatique en cas d'échec
- ⚠️ Pas de notification en cas d'échec

---

## 🔧 6. CONFIGURATION AWS (À VÉRIFIER)

### A. ALB (Application Load Balancer)

**À Vérifier:**
1. **Listener HTTPS (443):**
   - Règle pour `/telegram/webhook` → Quel Target Group?
   - Ordre des règles (la première qui correspond est utilisée)

2. **Target Groups:**
   - Quel Target Group est utilisé pour `/telegram/webhook`?
   - Combien de targets sont enregistrés?
   - Status des targets (healthy/unhealthy)?
   - Health check path et port?

### B. ECS Service `ganopa-dev-bot-svc`

**À Vérifier:**
1. **Status du service:**
   - ACTIVE / INACTIVE / DRAINING?

2. **Load Balancer:**
   - Le service est-il attaché à un Load Balancer?
   - Quel Target Group est utilisé?
   - Les tasks sont-elles enregistrées automatiquement dans le TG?

3. **Task Definition:**
   - Port mapping: 8000?
   - Health check configuré?
   - Variables d'environnement (OPENAI_API_KEY, TELEGRAM_BOT_TOKEN, etc.)?

4. **Tasks:**
   - Desired count: 1?
   - Running count: 1?
   - Status des tasks (RUNNING / STOPPED)?

### C. Target Group

**Pattern Correct pour ECS Fargate:**
1. **Type:** IP (pas Instance)
2. **Protocol:** HTTP
3. **Port:** 8000 (ou le port du container)
4. **Health Check:**
   - Path: `/health`
   - Port: 8000
   - Protocol: HTTP
5. **Registration:**
   - **AUTOMATIQUE** via ECS Service (pas manuel)
   - Les IPs des tasks sont enregistrées automatiquement quand le service est attaché au TG

---

## 🎯 7. PLAN D'ACTION PRIORITAIRE

### Étape 1: Vérifier l'État AWS (URGENT)

**Commandes AWS CLI:**

```bash
# 1. Vérifier le service ECS
aws ecs describe-services \
  --region me-central-1 \
  --cluster vancelian-dev-api-cluster \
  --services ganopa-dev-bot-svc \
  --query 'services[0].{status:status,desired:desiredCount,running:runningCount,loadBalancers:loadBalancers,taskDef:taskDefinition}'

# 2. Lister les Target Groups
aws elbv2 describe-target-groups \
  --region me-central-1 \
  --query 'TargetGroups[?contains(TargetGroupName, `ganopa`) || contains(TargetGroupName, `bot`)].{name:TargetGroupName,arn:TargetGroupArn,port:Port,protocol:Protocol,healthCheck:HealthCheckPath}'

# 3. Vérifier les targets d'un Target Group
aws elbv2 describe-target-health \
  --region me-central-1 \
  --target-group-arn <TG_ARN> \
  --query 'TargetHealthDescriptions[*].{target:Target.Id,port:Target.Port,health:TargetHealth.State}'

# 4. Vérifier les règles ALB
aws elbv2 describe-listeners \
  --region me-central-1 \
  --load-balancer-arn <ALB_ARN> \
  --query 'Listeners[?Port==`443`].Rules[*].{conditions:Conditions,actions:Actions}'
```

### Étape 2: Corriger le Routing ALB

**Option A: Utiliser un Path Différent (Recommandé)**

1. **Modifier `ganopa-bot` pour utiliser `/ganopa/webhook`:**
   ```python
   @app.post("/ganopa/webhook")
   ```

2. **Créer une règle ALB:**
   - Path: `/ganopa/webhook`
   - Forward to: Target Group de `ganopa-dev-bot-svc`

3. **Reconfigurer le webhook Telegram:**
   ```bash
   curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://api.maisonganopa.com/ganopa/webhook"}'
   ```

**Option B: Remplacer `agent_gateway` par `ganopa-bot`**

1. **Modifier la règle ALB pour `/telegram/webhook`:**
   - Forward to: Target Group de `ganopa-dev-bot-svc`

2. **Déplacer les commandes de `agent_gateway` vers `ganopa-bot`** (si nécessaire)

### Étape 3: Vérifier l'Attachement ECS → Target Group

**Si le service ECS n'est pas attaché au Target Group:**

1. **ECS → Services → `ganopa-dev-bot-svc`**
2. **Update service**
3. **Load balancing:**
   - Ajouter un Load Balancer
   - Sélectionner le Target Group correct
   - Container name: `ganopa-bot`
   - Container port: 8000

**Important:** ECS enregistrera automatiquement les IPs des tasks dans le Target Group.

### Étape 4: Nettoyer la Documentation

```bash
# Créer un dossier archive
mkdir -p services/ganopa-bot/docs-archive

# Déplacer les fichiers obsolètes
mv services/ganopa-bot/*.md services/ganopa-bot/docs-archive/ 2>/dev/null || true

# Garder uniquement les fichiers essentiels
# (à définir selon les besoins)
```

---

## 📋 8. CHECKLIST DE VÉRIFICATION

### Git
- [x] Pas de rebase en cours
- [x] Pas de conflits de merge
- [x] Branch à jour avec origin/main
- [ ] Nettoyer les fichiers non trackés

### Code
- [x] `main.py` sans conflits
- [x] `config.py` correct
- [x] Dockerfile correct
- [x] Workflow GitHub Actions correct

### AWS - ECS
- [ ] Service `ganopa-dev-bot-svc` existe
- [ ] Service status: ACTIVE
- [ ] Desired count: 1
- [ ] Running count: 1
- [ ] Task Definition avec bonne image
- [ ] Variables d'environnement configurées

### AWS - Target Group
- [ ] Target Group existe pour `ganopa-bot`
- [ ] Type: IP (pas Instance)
- [ ] Port: 8000
- [ ] Health check: `/health`
- [ ] Targets enregistrés automatiquement par ECS
- [ ] Targets status: healthy

### AWS - ALB
- [ ] Règle pour `/telegram/webhook` (ou `/ganopa/webhook`)
- [ ] Règle pointe vers le bon Target Group
- [ ] Ordre des règles correct

### Tests
- [ ] `curl https://api.maisonganopa.com/health` → 200
- [ ] `curl https://api.maisonganopa.com/_meta` → 200 avec build_id
- [ ] `curl https://api.maisonganopa.com/telegram/webhook` → 200 (ou 405 si GET)
- [ ] Envoyer message Telegram → Réponse AI (pas d'écho)

---

## 🎯 CONCLUSION

### Problème Principal
**Le routing ALB est incorrect:** `/telegram/webhook` ne pointe pas vers un Target Group avec des cibles saines.

### Solution Immédiate
1. **Vérifier l'état AWS** (service ECS, Target Group, ALB rules)
2. **Corriger le routing ALB** (soit changer le path, soit changer le Target Group)
3. **Vérifier l'attachement ECS → Target Group** (enregistrement automatique des IPs)

### Problèmes Secondaires
- Documentation proliférante (nettoyage recommandé)
- Pas de rollback automatique (amélioration future)

---

## 📞 PROCHAINES ÉTAPES

1. **Exécuter les commandes AWS CLI** pour diagnostiquer l'état actuel
2. **Prendre des captures d'écran** de:
   - ECS Service → Load Balancer
   - Target Group → Targets
   - ALB → Listener Rules
3. **Appliquer la correction** selon le diagnostic
4. **Tester** les endpoints après correction

