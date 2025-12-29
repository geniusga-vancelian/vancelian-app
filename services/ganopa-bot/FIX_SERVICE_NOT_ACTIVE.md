# 🔧 Fix: ServiceNotActiveException

## Problème

Le workflow GitHub Actions échoue avec:
```
ServiceNotActiveException: Service was not ACTIVE
```

**Cause:** Le service ECS `ganopa-dev-bot-svc` n'est pas dans l'état ACTIVE.

## 🎯 Solutions

### Solution 1: Vérifier l'État du Service dans AWS Console

**Dans AWS Console → ECS → Services → `ganopa-dev-bot-svc`:**

1. **Voir le statut du service:**
   - **ACTIVE** → Le service est actif, le problème est ailleurs
   - **INACTIVE** → Le service est inactif, il faut le réactiver
   - **DRAINING** → Le service est en cours de drainage
   - **Autre** → Voir les événements pour comprendre

2. **Si le service est INACTIVE:**
   - **Actions → Update service**
   - Sélectionner la dernière révision de la Task Definition
   - **Desired count:** 1 (ou plus)
   - **Update service**
   - Attendre que le service devienne ACTIVE

### Solution 2: Attendre que le Service Devienne ACTIVE

**Le workflow peut être modifié pour attendre que le service soit ACTIVE avant de le mettre à jour:**

Ajouter une étape avant "Update ECS service" pour vérifier l'état du service.

### Solution 3: Forcer la Réactivation du Service

**Si le service est INACTIVE:**

1. **ECS → Services → `ganopa-dev-bot-svc`**
2. **Actions → Update service**
3. **Task Definition:** Sélectionner la dernière révision
4. **Desired count:** 1
5. **Update service**
6. Attendre que le service devienne ACTIVE (2-3 minutes)

## 🔧 Modification du Workflow (Optionnel)

**Pour éviter ce problème à l'avenir, ajouter une vérification dans le workflow:**

```yaml
- name: Wait for service to be ACTIVE
  shell: bash
  run: |
    set -euo pipefail
    MAX_WAIT=300  # 5 minutes
    ELAPSED=0
    while [ $ELAPSED -lt $MAX_WAIT ]; do
      STATUS=$(aws ecs describe-services \
        --region "$AWS_REGION" \
        --cluster "$CLUSTER" \
        --services "$SERVICE" \
        --query 'services[0].status' \
        --output text)
      
      if [ "$STATUS" = "ACTIVE" ]; then
        echo "✅ Service is ACTIVE"
        exit 0
      fi
      
      echo "⏳ Service status: $STATUS (waiting...)"
      sleep 10
      ELAPSED=$((ELAPSED + 10))
    done
    
    echo "❌ Service did not become ACTIVE within $MAX_WAIT seconds"
    exit 1
```

## 🚨 Action Immédiate

**Vérifiez l'état du service dans AWS Console:**

1. **ECS → Services → `ganopa-dev-bot-svc`**
2. **Voir le statut**
3. **Si INACTIVE:** Réactiver le service (Solution 1)
4. **Si ACTIVE:** Le problème est ailleurs, vérifier les événements

**Puis relancer le workflow GitHub Actions.**

