# Production Audit & Remediation - Arquantix.com

**Date:** 2026-01-03  
**Objectif:** Vérification end-to-end et plan de remédiation pour https://arquantix.com/

---

## 📊 Diagramme de l'État Actuel

```
┌─────────────────────────────────────────────────────────────────┐
│                         Route53                                   │
│  arquantix.com (A/AAAA) ────────────────────────┐              │
│  www.arquantix.com (A/AAAA) ───────────────────┤              │
└──────────────────────────────────────────────────┼──────────────┘
                                                  │
                                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CloudFront                                  │
│  Distribution ID: EPJ3WQCO04UWW                                 │
│  Domain: d*.cloudfront.net                                      │
│  Origin: <ALB_DNS> (Custom Origin)                             │
│  Origin Path: <empty>                                           │
│  Protocol: HTTPS Only                                           │
│  Certificate: ACM (us-east-1)                                   │
└──────────────────────────────────────────────────┼──────────────┘
                                                  │
                                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Application Load Balancer                    │
│  Name: arquantix-prod-alb                                      │
│  Scheme: internet-facing                                        │
│  DNS: *.elb.me-central-1.amazonaws.com                         │
│  Listeners:                                                     │
│    - Port 80: Redirect to 443                                  │
│    - Port 443: HTTPS with ACM cert                             │
│  Rules:                                                         │
│    - Default: Forward to arquantix-prod-tg                     │
└──────────────────────────────────────────────────┼──────────────┘
                                                  │
                                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Target Group                               │
│  Name: arquantix-prod-tg                                       │
│  Port: 3000                                                     │
│  Protocol: HTTP                                                │
│  Health Check:                                                  │
│    - Path: /health                                              │
│    - Interval: 30s                                             │
│    - Timeout: 10s                                               │
│    - Healthy: 2                                                 │
│    - Unhealthy: 5                                               │
│    - Matcher: 200-399                                           │
│  Targets: <IP>:3000 (Status: HEALTHY/UNHEALTHY)                │
└──────────────────────────────────────────────────┼──────────────┘
                                                  │
                                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ECS Service                                 │
│  Cluster: arquantix-cluster                                    │
│  Service: arquantix-coming-soon                                │
│  Task Definition: arquantix-coming-soon:N                      │
│  Desired Count: 1                                               │
│  Running Count: 1                                               │
│  Health Check Grace Period: 120s                                │
│  Container:                                                     │
│    - Image: ECR/arquantix-coming-soon:latest                   │
│    - Port: 3000                                                 │
│    - Env: PORT=3000, HOSTNAME=0.0.0.0                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Résultats de l'Audit

### 1. Route53 ✅/❌

**État actuel:**
- Zone hosted: `arquantix.com`
- Records: À vérifier

**Vérifications:**
- [ ] `arquantix.com` pointe vers CloudFront distribution
- [ ] `www.arquantix.com` pointe vers CloudFront distribution
- [ ] Pas de drift (records cohérents)

**Problèmes identifiés:**
- À compléter après vérification

---

### 2. CloudFront ✅/❌

**Distribution ID:** `EPJ3WQCO04UWW`

**État actuel:**
- Status: Deployed
- Origin Domain: À vérifier (doit être ALB DNS)
- Origin Path: À vérifier (doit être vide)
- Protocol Policy: À vérifier
- TLS Settings: À vérifier

**Vérifications:**
- [ ] Origin domain = ALB DNS (pas de loop)
- [ ] Origin path = "" (vide)
- [ ] Origin protocol = HTTPS Only
- [ ] HTTPS Port = 443
- [ ] Certificate ACM attaché (us-east-1)

**Problèmes identifiés:**
- À compléter après vérification

---

### 3. ALB ✅/❌

**État actuel:**
- Name: `arquantix-prod-alb`
- Scheme: À vérifier (doit être internet-facing)
- DNS: À vérifier

**Listeners:**
- [ ] Port 80: Redirect to 443
- [ ] Port 443: HTTPS avec certificat ACM
- [ ] Rules: Forward vers target group correct

**Vérifications:**
- [ ] Internet-facing (pas internal)
- [ ] Listener 80 → Redirect 443
- [ ] Listener 443 → Certificat ACM
- [ ] Default rule → arquantix-prod-tg
- [ ] Host header rules corrects (si présents)

**Problèmes identifiés:**
- À compléter après vérification

---

### 4. Target Group ✅/❌

**Target Group:** `arquantix-prod-tg`

**État actuel:**
- Port: 3000
- Protocol: HTTP
- Health Check Path: `/health`
- Health Check Interval: 30s
- Health Check Timeout: 10s
- Healthy Threshold: 2
- Unhealthy Threshold: 5
- Matcher: 200-399

**Targets:**
- [ ] Au moins 1 target HEALTHY
- [ ] Pas de targets "unused" (AZ non activée)
- [ ] Pas de targets "draining" permanents

**Problèmes identifiés:**
- À compléter après vérification

---

### 5. ECS Service ✅/❌

**Service:** `arquantix-coming-soon`

**État actuel:**
- Cluster: `arquantix-cluster`
- Desired Count: 1
- Running Count: À vérifier
- Task Definition: À vérifier
- Health Check Grace Period: 120s (doit être 180s)

**Task Definition:**
- [ ] Container Port: 3000
- [ ] Environment: PORT=3000
- [ ] Environment: HOSTNAME=0.0.0.0
- [ ] Image: Dernière version ECR

**Load Balancers:**
- [ ] Target Group attaché: arquantix-prod-tg
- [ ] Container Name: arquantix-coming-soon
- [ ] Container Port: 3000

**Tasks:**
- [ ] Au moins 1 task RUNNING
- [ ] Pas de crash loop (tasks qui redémarrent)
- [ ] Tasks stables (pas de "stopped" fréquents)

**Problèmes identifiés:**
- ✅ Health check grace period: 120s (recommandé: 180s - à mettre à jour)
- ⚠️ Targets peuvent être unhealthy (vérifier après déploiement)

---

### 6. Security Groups ✅/❌

**ALB Security Group:**
- [ ] INBOUND: Port 80 depuis 0.0.0.0/0
- [ ] INBOUND: Port 443 depuis 0.0.0.0/0
- [ ] OUTBOUND: All traffic

**ECS Security Group:**
- [ ] INBOUND: Port 3000 depuis ALB Security Group
- [ ] OUTBOUND: All traffic (pour logs, etc.)

**Problèmes identifiés:**
- À compléter après vérification

---

### 7. CloudWatch Logs ⚠️

**Log Group:** `/aws/ecs/arquantix-coming-soon`

**État:**
- Accès limité par permissions
- Logs nécessaires pour diagnostiquer les erreurs de démarrage

**Vérifications:**
- [ ] Logs accessibles
- [ ] Pas d'erreurs de démarrage
- [ ] Application démarre correctement
- [ ] Health check endpoint répond

**Problèmes identifiés:**
- Permissions insuffisantes pour accéder aux logs

---

## 🔧 Plan de Remédiation

### Changements AWS à Appliquer

#### 1. ECS Service - Health Check Grace Period
**Changement:**
```bash
aws ecs update-service \
  --cluster arquantix-cluster \
  --service arquantix-coming-soon \
  --health-check-grace-period-seconds 180 \
  --region me-central-1
```
**Raison:** 120s peut être insuffisant pour Next.js. 180s donne plus de marge.

#### 2. Vérifier et Corriger Route53
**Si nécessaire:**
- S'assurer que les records pointent vers CloudFront
- Vérifier qu'il n'y a pas de drift

#### 3. Vérifier et Corriger CloudFront Origin
**Si nécessaire:**
- S'assurer que l'origin est l'ALB DNS
- Vérifier que l'origin path est vide
- Vérifier le protocol policy

#### 4. Vérifier et Corriger ALB Rules
**Si nécessaire:**
- S'assurer que les règles pointent vers le bon target group
- Vérifier les Host headers si présents

---

## 🧪 Tests de Preuve

### Test 1: Health Check via CloudFront
```bash
curl -I https://arquantix.com/health
# Attendu: HTTP/2 200
# Headers: content-type: text/plain
```

### Test 2: Page Principale via CloudFront
```bash
curl -I https://arquantix.com/
# Attendu: HTTP/2 200
```

### Test 3: ALB Direct (avec Host header)
```bash
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --region me-central-1 \
  --query 'LoadBalancers[?contains(LoadBalancerName, `arquantix`)].DNSName' \
  --output text)

curl -I -H "Host: arquantix.com" http://$ALB_DNS/health
# Attendu: HTTP/1.1 200
```

### Test 4: Target Group Health
```bash
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:me-central-1:411714852748:targetgroup/arquantix-prod-tg/89fe413e994d9f0f \
  --region me-central-1 \
  --query 'TargetHealthDescriptions[*].{Target:Target.Id,Health:TargetHealth.State}'
# Attendu: Au moins 1 target avec Health: "healthy"
```

### Test 5: ECS Tasks Stables
```bash
aws ecs describe-services \
  --cluster arquantix-cluster \
  --services arquantix-coming-soon \
  --region me-central-1 \
  --query 'services[0].{RunningCount:runningCount,DesiredCount:desiredCount}'
# Attendu: RunningCount == DesiredCount == 1
```

---

## 🔄 Plan de Rollback

### Rollback 1: Task Definition
```bash
# Revenir à la révision précédente
aws ecs update-service \
  --cluster arquantix-cluster \
  --service arquantix-coming-soon \
  --task-definition arquantix-coming-soon:2 \
  --region me-central-1
```

### Rollback 2: Health Check Grace Period
```bash
# Revenir à 120s
aws ecs update-service \
  --cluster arquantix-cluster \
  --service arquantix-coming-soon \
  --health-check-grace-period-seconds 120 \
  --region me-central-1
```

### Rollback 3: Target Group Health Check
```bash
# Revenir aux paramètres précédents
aws elbv2 modify-target-group \
  --target-group-arn arn:aws:elasticloadbalancing:me-central-1:411714852748:targetgroup/arquantix-prod-tg/89fe413e994d9f0f \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 5 \
  --unhealthy-threshold-count 2 \
  --matcher HttpCode=200 \
  --region me-central-1
```

### Rollback 4: Code Application
```bash
# Revenir au commit précédent
git revert HEAD
git push origin main
```

---

## 📋 Checklist de Validation Finale

- [ ] Route53 records pointent vers CloudFront
- [ ] CloudFront origin = ALB DNS, path vide
- [ ] ALB internet-facing, listeners 80/443 configurés
- [ ] Target Group: Au moins 1 target HEALTHY
- [ ] ECS Service: 1 task RUNNING, stable
- [ ] Security Groups: Règles correctes
- [ ] Health check: `curl -I https://arquantix.com/health` → 200
- [ ] Page principale: `curl -I https://arquantix.com/` → 200

---

**Dernière mise à jour:** 2026-01-03

