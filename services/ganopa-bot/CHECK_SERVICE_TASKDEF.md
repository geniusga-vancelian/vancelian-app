# 🔍 Vérifier que le Service Utilise la Bonne Task Definition

## État Actuel

✅ **Task Definition:** `ganopa-dev-bot-task:22`
✅ **Image URI:** `...ganopa-bot:329d64b416cd3d322f02f8a49ffee91340b7d23a`
✅ **Commit correspond:** `329d64b` (dernier commit)

## ⚠️ Problème Potentiel

Le service ECS pourrait ne pas utiliser cette révision de la task definition. Il faut vérifier.

## 🎯 Vérification

### 1. Vérifier quelle Task Definition le Service Utilise

**Dans AWS Console → ECS → Services → `ganopa-dev-bot-svc`:**

1. **Onglet "Configuration"** ou **"Détails"**
2. **Chercher "Task Definition"** ou **"Définition de la tâche"**
3. **Voir la révision utilisée**

**Attendu:**
- `ganopa-dev-bot-task:22` (ou plus récent)

**Si différent:**
- ❌ Le service utilise une ancienne révision
- Solution: Mettre à jour le service pour utiliser la révision 22

### 2. Vérifier les Tasks en Cours

**Dans AWS Console → ECS → Services → `ganopa-dev-bot-svc`:**

1. **Onglet "Tasks"**
2. **Cliquer sur une task RUNNING**
3. **Onglet "Configuration"**
4. **Voir "Définition de la tâche : révision"**

**Attendu:**
- `ganopa-dev-bot-task:22` (ou plus récent)

**Si différent:**
- ❌ Les tasks utilisent une ancienne révision
- Solution: Forcer un nouveau déploiement

### 3. Forcer un Nouveau Déploiement

**Si le service n'utilise pas la révision 22:**

1. **ECS → Services → `ganopa-dev-bot-svc`**
2. **Update service**
3. **Task Definition:** Sélectionner `ganopa-dev-bot-task:22`
4. **Update service**
5. ✅ **Force new deployment** (si disponible)
6. Attendre stabilisation (2-3 minutes)

## 🔍 Vérification Alternative: Via AWS CLI

```bash
# Vérifier quelle task definition le service utilise
aws ecs describe-services \
  --cluster vancelian-dev-api-cluster \
  --services ganopa-dev-bot-svc \
  --region me-central-1 \
  --query 'services[0].taskDefinition' \
  --output text

# Doit retourner: arn:aws:ecs:me-central-1:411714852748:task-definition/ganopa-dev-bot-task:22
```

## 📊 Checklist

- [ ] Service ECS utilise `ganopa-dev-bot-task:22` (ou plus récent)
- [ ] Tasks RUNNING utilisent `ganopa-dev-bot-task:22` (ou plus récent)
- [ ] IMAGE URI dans les tasks = `...ganopa-bot:329d64b...`
- [ ] Service a été mis à jour récemment (Events tab)

## 🚨 Action Immédiate

**Vérifiez quelle task definition le service utilise:**

1. AWS Console → ECS → Services → `ganopa-dev-bot-svc`
2. Voir la task definition utilisée
3. Si ce n'est pas `ganopa-dev-bot-task:22`, mettre à jour le service

**OU**

**Vérifiez directement dans les tasks:**

1. AWS Console → ECS → Services → `ganopa-dev-bot-svc`
2. Tasks → Cliquer sur une task RUNNING
3. Configuration → Voir "Définition de la tâche : révision"
4. Si ce n'est pas `ganopa-dev-bot-task:22`, forcer un nouveau déploiement

