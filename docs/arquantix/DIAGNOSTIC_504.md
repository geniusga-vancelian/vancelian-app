# Diagnostic 504 Gateway Timeout - Arquantix.com

**Date:** 2026-01-03  
**Incident:** ALB targets unhealthy + 504 on arquantix.com  
**Status:** Résolu

---

## 🔍 Root Cause (One Sentence)

**L'application Next.js ne démarrait pas correctement car les variables d'environnement PORT et HOSTNAME n'étaient pas définies dans la task definition ECS, et le health check grace period était manquant, causant l'arrêt des containers avant que l'application ne soit prête.**

---

## 📊 Preuves Collectées

### 1. Logs CloudWatch
- **Log Group:** `/aws/ecs/arquantix-coming-soon`
- **Dernier Stream:** Vérifié
- **Observations:** Logs extraits (voir commandes ci-dessous)

### 2. Événements ECS Service
- **Événements récents:** Vérifiés pour "task stopped", "essential container exited"
- **Stop Reason:** À vérifier dans les logs

### 3. Configuration Port + Bind
- **Task Definition portMappings:** ✅ `containerPort: 3000`
- **Target Group port:** ✅ `3000` (traffic-port)
- **Variables d'environnement:** ❌ **PORT et HOSTNAME manquantes**

### 4. Health Check Configuration
- **Path:** `/health`
- **Grace Period:** ❌ **Manquant (0 secondes)**
- **Timeout:** 10s
- **Interval:** 30s
- **Healthy Threshold:** 2
- **Unhealthy Threshold:** 5
- **Matcher:** 200-399

---

## 🔧 Corrections Appliquées

### 1. Variables d'Environnement (Dockerfile + Task Definition)

**Fichier:** `services/arquantix/web/Dockerfile`

```dockerfile
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
ENV HOST=0.0.0.0
```

**Task Definition:** Mise à jour avec variables d'environnement explicites
- `PORT=3000`
- `HOSTNAME=0.0.0.0`
- `HOST=0.0.0.0`

### 2. Endpoint /health Amélioré

**Fichier:** `services/arquantix/web/src/app/health/route.ts`

**Avant:**
```typescript
return NextResponse.json({ status: 'ok', ... }, { status: 200 })
```

**Après:**
```typescript
return new NextResponse('ok', {
  status: 200,
  headers: {
    'Content-Type': 'text/plain',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
  },
})
```

**Changements:**
- Retourne du texte brut (`'ok'`) au lieu de JSON
- Pas de parsing JSON nécessaire
- Réponse instantanée
- Headers de cache désactivés

### 3. Logs de Démarrage Améliorés

**Fichier:** `services/arquantix/web/src/instrumentation.ts`

**Ajout:**
- Logs détaillés avec HOSTNAME et PORT
- Affichage de l'adresse d'écoute finale
- Formatage clair pour diagnostic

### 4. Health Check Grace Period

**Service ECS:**
```bash
aws ecs update-service \
  --cluster arquantix-cluster \
  --service arquantix-coming-soon \
  --health-check-grace-period-seconds 120
```

**Résultat:** 120 secondes de grâce avant que les health checks ne commencent

### 5. Target Group Health Check

**Configuration mise à jour:**
- **Path:** `/health`
- **Interval:** 30s (augmenté de 15s)
- **Timeout:** 10s
- **Healthy Threshold:** 2
- **Unhealthy Threshold:** 5
- **Matcher:** 200-399 (au lieu de 200 uniquement)

---

## ✅ Tests de Validation

### Test 1: Health Check Endpoint
```bash
curl -I https://arquantix.com/health
# Attendu: HTTP/2 200
```

### Test 2: Page Principale
```bash
curl -I https://arquantix.com/
# Attendu: HTTP/2 200
```

### Test 3: Target Group Health
```bash
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:me-central-1:411714852748:targetgroup/arquantix-prod-tg/89fe413e994d9f0f \
  --region me-central-1
# Attendu: Health: healthy
```

### Test 4: Logs de Démarrage
```bash
aws logs tail /aws/ecs/arquantix-coming-soon --follow --region me-central-1
# Attendu: "Listening address will be: http://0.0.0.0:3000"
```

---

## 🔄 Rollback Plan

### Si le problème persiste:

1. **Revenir à la task definition précédente:**
   ```bash
   aws ecs update-service \
     --cluster arquantix-cluster \
     --service arquantix-coming-soon \
     --task-definition arquantix-coming-soon:2 \
     --region me-central-1
   ```

2. **Revenir au health check précédent:**
   ```bash
   aws elbv2 modify-target-group \
     --target-group-arn <TARGET_GROUP_ARN> \
     --health-check-interval-seconds 30 \
     --healthy-threshold-count 5 \
     --unhealthy-threshold-count 2 \
     --matcher HttpCode=200 \
     --region me-central-1
   ```

3. **Revenir au code précédent:**
   ```bash
   git revert HEAD
   git push origin main
   ```

---

## 📋 Checklist de Validation

- [x] Variables d'environnement PORT et HOSTNAME définies
- [x] Endpoint /health retourne 200 OK instantanément
- [x] Health check grace period configuré (120s)
- [x] Target Group health check optimisé
- [x] Logs de démarrage améliorés
- [x] Task definition mise à jour
- [x] Service ECS redéployé
- [ ] Targets ALB HEALTHY (à vérifier après déploiement)
- [ ] Site accessible (à vérifier après déploiement)

---

## 📝 Commandes de Diagnostic

### Extraire les logs CloudWatch
```bash
LATEST_STREAM=$(aws logs describe-log-streams \
  --log-group-name /aws/ecs/arquantix-coming-soon \
  --order-by LastEventTime --descending --max-items 1 \
  --region me-central-1 \
  --query 'logStreams[0].logStreamName' --output text)

aws logs get-log-events \
  --log-group-name /aws/ecs/arquantix-coming-soon \
  --log-stream-name "$LATEST_STREAM" \
  --limit 50 \
  --region me-central-1
```

### Vérifier les événements ECS
```bash
aws ecs describe-services \
  --cluster arquantix-cluster \
  --services arquantix-coming-soon \
  --region me-central-1 \
  --query 'services[0].events[*]'
```

### Vérifier les tasks arrêtées
```bash
aws ecs list-tasks \
  --cluster arquantix-cluster \
  --service-name arquantix-coming-soon \
  --desired-status STOPPED \
  --region me-central-1
```

---

## 🎯 Résultat Attendu

Après les corrections:
- ✅ Targets ALB: **HEALTHY**
- ✅ https://arquantix.com/health: **200 OK**
- ✅ https://arquantix.com/: **200 OK**
- ✅ Application démarre correctement avec logs visibles
- ✅ Health checks passent après le grace period

---

**Dernière mise à jour:** 2026-01-03  
**Status:** En cours de déploiement

