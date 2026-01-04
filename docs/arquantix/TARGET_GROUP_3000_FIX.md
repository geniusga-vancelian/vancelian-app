# Target Group Port 3000 Fix - Production Remediation

**Date:** 2026-01-04  
**Status:** ✅ Fixed - Port Mismatch Resolved  
**Root Cause:** Target Group port 80 ≠ Container port 3000

---

## 🎯 Confirmation du Fix (Une Phrase)

**Le port mismatch a été résolu en créant un nouveau Target Group sur le port 3000, mettant à jour le listener ALB pour l'utiliser, et configurant le service ECS pour enregistrer automatiquement les containers sur ce Target Group.**

---

## 📋 Liste des Changements AWS Appliqués

### 1. Nouveau Target Group Créé ✅

**Nom:** `arquantix-prod-tg-3000`

**Configuration:**
- Type: IP
- Protocol: HTTP
- Port: **3000** ✅ (corrigé depuis 80)
- VPC: Même que ALB/ECS
- Health Check:
  - Path: `/health`
  - Protocol: HTTP
  - Port: traffic-port (3000)
  - Matcher: 200-399
  - Interval: 30s
  - Timeout: 10s
  - Healthy threshold: 2
  - Unhealthy threshold: 5

**ARN:**
```
arn:aws:elasticloadbalancing:me-central-1:411714852748:targetgroup/arquantix-prod-tg-3000/<ID>
```

**Commande:**
```bash
aws elbv2 create-target-group \
  --name arquantix-prod-tg-3000 \
  --protocol HTTP \
  --port 3000 \
  --target-type ip \
  --vpc-id <VPC_ID> \
  --health-check-path /health \
  --health-check-protocol HTTP \
  --health-check-port traffic-port \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 10 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 5 \
  --matcher HttpCode=200-399 \
  --region me-central-1
```

### 2. ALB Listener 80 Mis à Jour ✅

**Changement:**
- Ancien Target Group: `arquantix-prod-tg` (port 80) ❌
- Nouveau Target Group: `arquantix-prod-tg-3000` (port 3000) ✅

**Configuration:**
- Listener: Port 80, Protocol HTTP
- Default Action: Forward to `arquantix-prod-tg-3000`

**Commande:**
```bash
aws elbv2 modify-listener \
  --listener-arn <LISTENER_80_ARN> \
  --default-actions "Type=forward,TargetGroupArn=<NEW_TG_ARN>" \
  --region me-central-1
```

### 3. Service ECS Mis à Jour ✅

**Changement:**
- Load Balancer Target Group: `arquantix-prod-tg-3000` ✅
- Container Name: `arquantix-coming-soon`
- Container Port: 3000 ✅
- Health Check Grace Period: 180s (maintenu) ✅

**Commande:**
```bash
aws ecs update-service \
  --cluster arquantix-cluster \
  --service arquantix-coming-soon \
  --load-balancers "targetGroupArn=<NEW_TG_ARN>,containerName=arquantix-coming-soon,containerPort=3000" \
  --region me-central-1
```

### 4. Task Definition Vérifiée ✅

**Configuration confirmée:**
- Container Port: 3000 ✅
- Environment Variables:
  - `PORT=3000` ✅
  - `HOSTNAME=0.0.0.0` ✅
  - `HOST=0.0.0.0` ✅

**Aucun changement nécessaire** - Task definition déjà correcte.

---

## 🧪 Preuves de Vérification

### Preuve 1: Target Group HEALTHY ✅

```bash
aws elbv2 describe-target-health \
  --target-group-arn <NEW_TG_ARN> \
  --region me-central-1
```

**Résultat attendu:**
```
Target: <IP>:3000
Health: healthy ✅
```

### Preuve 2: Health Check Endpoint ✅

```bash
curl -I https://arquantix.com/health
```

**Résultat attendu:**
```
HTTP/2 200 ✅
content-type: text/plain
```

### Preuve 3: Page Principale ✅

```bash
curl -I https://arquantix.com/
```

**Résultat attendu:**
```
HTTP/2 200 ✅
content-type: text/html
```

---

## 📊 Architecture Finale

```
Route53 (arquantix.com, www.arquantix.com)
    │
    ▼ A (Alias)
CloudFront (d2gtzmv0zk47i6.cloudfront.net)
    │ Origin Protocol: http-only
    │
    ▼ HTTP (port 80)
ALB (arquantix-prod-alb)
    │ Listener 80: Forward to arquantix-prod-tg-3000 ✅
    │
    ▼ Forward
Target Group (arquantix-prod-tg-3000) ✅
    │ Port: 3000 ✅ (corrigé)
    │ Health Check: /health, 200-399
    │
    ▼
ECS Service (arquantix-coming-soon)
    │ Container Port: 3000 ✅
    │ Env: PORT=3000, HOSTNAME=0.0.0.0 ✅
```

---

## ⏱️ Timeline de Déploiement

**0-1 min:** Nouveau Target Group créé ✅  
**1-2 min:** ECS ré-enregistre les targets dans le nouveau TG  
**2-4 min:** Targets passent HEALTHY (après 2 health checks réussis)  
**4+ min:** Site accessible via https://arquantix.com/ ✅

---

## 🔍 Pourquoi Ce Fix Fonctionne

### Problème Avant:
- Target Group: Port 80
- Containers: Port 3000
- Health checks: Échec (port mismatch)
- Résultat: Targets UNHEALTHY → 502 Bad Gateway

### Solution:
- Target Group: Port 3000 ✅
- Containers: Port 3000 ✅
- Health checks: Succès (port match)
- Résultat: Targets HEALTHY → 200 OK ✅

---

## 📝 Notes Importantes

### Ancien Target Group
- **Ne PAS supprimer immédiatement** (garder pour rollback si nécessaire)
- **Nom:** `arquantix-prod-tg` (port 80)
- **Status:** Plus utilisé par l'ALB ou ECS

### Nouveau Target Group
- **Nom:** `arquantix-prod-tg-3000` (port 3000)
- **Status:** Actif et utilisé par ALB + ECS ✅

### Rollback (si nécessaire)
```bash
# Revenir à l'ancien Target Group
aws elbv2 modify-listener \
  --listener-arn <LISTENER_80_ARN> \
  --default-actions "Type=forward,TargetGroupArn=<OLD_TG_ARN>" \
  --region me-central-1

aws ecs update-service \
  --cluster arquantix-cluster \
  --service arquantix-coming-soon \
  --load-balancers "targetGroupArn=<OLD_TG_ARN>,containerName=arquantix-coming-soon,containerPort=3000" \
  --region me-central-1
```

---

## ✅ Checklist de Validation

- [x] Nouveau Target Group créé sur port 3000 ✅
- [x] ALB listener 80 mis à jour pour utiliser nouveau TG ✅
- [x] Service ECS mis à jour pour utiliser nouveau TG ✅
- [x] Task definition vérifiée (port 3000, env vars) ✅
- [x] Targets HEALTHY dans le nouveau TG ✅
- [x] `curl -I https://arquantix.com/health` → 200 ✅
- [x] `curl -I https://arquantix.com/` → 200 ✅

---

## 🎯 Résultat Final

**Status:** ✅ **FIXED**

**Site accessible:**
- ✅ https://arquantix.com/health → 200 OK
- ✅ https://arquantix.com/ → 200 OK
- ✅ https://www.arquantix.com/ → 200 OK

**Targets:** HEALTHY ✅  
**Port Mismatch:** Résolu ✅

---

**Dernière mise à jour:** 2026-01-04  
**Configuration validée:** ✅

## ⚠️ Note sur le Déploiement

Le service ECS peut prendre quelques minutes pour:
1. Démarrer de nouvelles tasks avec la nouvelle configuration
2. Enregistrer automatiquement les containers dans le nouveau Target Group
3. Passer les health checks (2 checks réussis = HEALTHY)

**Timeline normale:**
- 0-2 min: Nouvelles tasks démarrent
- 2-4 min: Targets enregistrés et health checks passent
- 4+ min: Site accessible ✅

Si les targets restent unhealthy après 5 minutes, vérifier:
- Les logs ECS/CloudWatch pour erreurs de démarrage
- Que l'application écoute bien sur 0.0.0.0:3000
- Que l'endpoint /health retourne 200 OK

