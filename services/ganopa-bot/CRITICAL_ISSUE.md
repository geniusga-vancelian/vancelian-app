# 🚨 Problème Critique Identifié

## Observations des Logs CloudWatch

**Log Group:** `/ecs/ganopa-dev-bot-task`

**Logs visibles:**
- ✅ Uvicorn démarre sur port `8080` (pas `8000`)
- ❌ **AUCUN log `ganopa_bot_started`**
- ❌ **AUCUN log de health check**
- ❌ **AUCUN log d'application**

## 🔍 Diagnostic

### Problème 1: Port Incorrect

**Observé:** Uvicorn tourne sur `8080`  
**Attendu:** Port `8000` (selon Dockerfile)

**Cause probable:** Variable d'environnement `PORT=8080` dans la Task Definition ECS

**Impact:** Si l'ALB/Health check pointe vers `8000`, le service ne répondra pas.

### Problème 2: Code Python Ne Démarre Pas

**Observé:** Aucun log `ganopa_bot_started`  
**Attendu:** Log au démarrage avec `bot_build_id`

**Causes possibles:**
1. **Exception au démarrage** → Le code Python crash avant de logger
2. **ImportError** → Module manquant (`ai_service`, `ai_prompt`, etc.)
3. **SyntaxError** → Code invalide (merge conflict non résolu?)
4. **Ancienne version** → Code qui ne log pas `ganopa_bot_started`

## 🎯 Actions Immédiates

### 1. Vérifier les Erreurs de Démarrage

**Dans CloudWatch → `/ecs/ganopa-dev-bot-task`:**

Chercher dans les logs récents:
- `ERROR`
- `Exception`
- `Traceback`
- `ImportError`
- `SyntaxError`
- `ModuleNotFoundError`

**Si vous trouvez une erreur:**
→ C'est la cause du problème
→ Corriger l'erreur et redéployer

### 2. Vérifier la Configuration ECS

**Dans AWS Console → ECS → Task Definitions → `ganopa-dev-bot-svc` (dernière révision):**

**Container `ganopa-bot` → Environment variables:**

- [ ] `PORT` = `8000` (pas `8080`)
- [ ] `OPENAI_API_KEY` est présent et non vide
- [ ] `TELEGRAM_BOT_TOKEN` est présent et non vide
- [ ] `PYTHONUNBUFFERED` = `1` (pour voir les logs immédiatement)

**Container `ganopa-bot` → Log configuration:**

- [ ] Log driver: `awslogs`
- [ ] Log group: `/ecs/ganopa-dev-bot-task` (ou `/aws/ecs/ganopa-dev-bot`)
- [ ] Log stream prefix: `ganopa-bot`

### 3. Vérifier le Health Check

**Dans AWS Console → ECS → Services → `ganopa-dev-bot-svc`:**

**Health check:**
- [ ] Path: `/health`
- [ ] Port: `8000` (ou `8080` si PORT est surchargé)
- [ ] Interval: 30s
- [ ] Timeout: 5s
- [ ] Healthy threshold: 2
- [ ] Unhealthy threshold: 3

**Si le port est `8080` dans ECS mais `8000` dans le Dockerfile:**
→ Le health check échouera
→ Le service sera marqué comme unhealthy
→ Les requêtes ne seront pas routées vers ce service

### 4. Test Direct: Vérifier les Erreurs Python

**Option A: Via les logs CloudWatch**

Chercher spécifiquement les erreurs Python:
```bash
aws logs filter-log-events \
  --log-group-name /ecs/ganopa-dev-bot-task \
  --region me-central-1 \
  --filter-pattern "ERROR Exception Traceback ImportError SyntaxError" \
  --start-time $(date -u -v-24H +%s)000
```

**Option B: Via ECS Exec (si activé)**

```bash
aws ecs execute-command \
  --cluster vancelian-dev-api-cluster \
  --task <TASK_ID> \
  --container ganopa-bot \
  --command "/bin/sh" \
  --interactive
```

Puis dans le container:
```bash
python -c "from app.main import app; print('OK')"
```

## 🔧 Solutions

### Solution 1: Corriger le Port

**Si `PORT=8080` dans la Task Definition:**

1. ECS → Task Definitions → `ganopa-dev-bot-svc` (dernière révision)
2. Container `ganopa-bot` → Environment variables
3. Modifier `PORT` = `8000` (ou supprimer si le Dockerfile gère déjà)
4. Enregistrer nouvelle révision
5. Services → `ganopa-dev-bot-svc` → Update service → Sélectionner nouvelle révision

**OU:**

Modifier le Dockerfile pour utiliser `8080`:
```dockerfile
ENV PORT=8080
EXPOSE 8080
```

### Solution 2: Corriger les Erreurs Python

**Si vous trouvez une erreur dans les logs:**

1. Identifier l'erreur exacte
2. Corriger le code
3. Commit et push
4. Redéployer

**Erreurs communes:**
- `ImportError: No module named 'app.ai_service'` → Vérifier que `ai_service.py` existe
- `SyntaxError` → Vérifier qu'il n'y a pas de merge conflict
- `ModuleNotFoundError` → Vérifier `requirements.txt`

### Solution 3: Forcer un Nouveau Déploiement

**Si l'ancienne version tourne encore:**

1. ECS → Services → `ganopa-dev-bot-svc`
2. Update service
3. ✅ **Force new deployment**
4. Attendre stabilisation (2-3 minutes)
5. Vérifier les nouveaux logs

## 📊 Checklist Complète

- [ ] Logs CloudWatch montrent `ganopa_bot_started`
- [ ] Pas d'erreurs Python dans les logs
- [ ] Port ECS = Port Dockerfile (8000 ou 8080, mais cohérent)
- [ ] Health check pointe vers le bon port
- [ ] Health check réussit (status = healthy)
- [ ] Logs montrent des health checks (`GET /health`)
- [ ] Logs montrent `telegram_update_received` quand un message arrive

## 🚨 Action Immédiate

**Cherchez les erreurs Python dans CloudWatch maintenant:**

1. AWS Console → CloudWatch → Log Groups → `/ecs/ganopa-dev-bot-task`
2. Filtrer: `ERROR Exception Traceback`
3. Voir les logs des dernières 24 heures
4. **Partagez les erreurs trouvées**

**OU:**

1. Vérifier la Task Definition ECS
2. Vérifier que `PORT=8000` (ou corriger)
3. Vérifier que tous les modules Python sont présents
4. Forcer un nouveau déploiement

