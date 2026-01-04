# Configuration Stable - CloudFront HTTP-Only Origin

**Date:** 2026-01-03  
**Status:** ✅ Stable - Production Ready  
**Approche:** CloudFront → ALB via HTTP (pas de certificat ACM requis)

---

## 📊 Architecture Finale

```
Route53 (arquantix.com, www.arquantix.com)
    │
    ▼ A (Alias)
CloudFront (d2gtzmv0zk47i6.cloudfront.net)
    │ Distribution ID: EPJ3WQCO04UWW
    │ Viewer Protocol: Redirect HTTP → HTTPS ✅
    │ Origin Protocol: http-only ✅
    │ Origin: arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com
    │
    ▼ HTTP (port 80)
ALB (arquantix-prod-alb)
    │ DNS: arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com
    │ Listener 80: Forward to Target Group ✅
    │ Listener 443: ❌ N/A (pas nécessaire)
    │
    ▼ Forward
Target Group (arquantix-prod-tg)
    │ Port: 80 (traffic-port → 3000)
    │ Health Check: /health, 200-399 ✅
    │
    ▼
ECS Service (arquantix-coming-soon)
    │ Container Port: 3000
    │ Health Check Grace Period: 180s
```

---

## ✅ Configuration Actuelle

### 1. Route53

**arquantix.com:**
- Type: A (Alias)
- Target: d2gtzmv0zk47i6.cloudfront.net ✅

**www.arquantix.com:**
- Type: A (Alias)
- Target: d2gtzmv0zk47i6.cloudfront.net ✅

### 2. CloudFront Distribution (EPJ3WQCO04UWW)

**Viewer Protocol Policy:**
```
redirect-to-https
```
- Les visiteurs HTTP sont automatiquement redirigés vers HTTPS ✅
- Les visiteurs HTTPS accèdent directement au contenu ✅

**Origin Configuration:**
```
Origin Domain: arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com
Origin Path: "" (vide)
Origin Protocol Policy: http-only ✅
HTTP Port: 80
HTTPS Port: 443 (non utilisé car http-only)
Origin SSL Protocols: ["TLSv1.2"]
```

**Pourquoi http-only fonctionne:**
- CloudFront se connecte à l'ALB en HTTP (port 80)
- L'ALB listener 80 forward directement vers le Target Group
- Pas de certificat SSL requis sur l'ALB
- Le trafic entre CloudFront et ALB est sur le réseau AWS (sécurisé)

### 3. Application Load Balancer (arquantix-prod-alb)

**Listener 80:**
```
Protocol: HTTP
Port: 80
Default Action: Forward to Target Group ✅
Target Group: arquantix-prod-tg
```

**Listener 443:**
```
❌ Non configuré (pas nécessaire avec http-only)
```

**Pourquoi pas de listener 443:**
- CloudFront utilise HTTP vers l'ALB (http-only)
- Les visiteurs accèdent via HTTPS via CloudFront (viewer protocol)
- Pas besoin de certificat ACM sur l'ALB

### 4. Target Group (arquantix-prod-tg)

**Configuration:**
```
Port: 80 (traffic-port)
Protocol: HTTP
Health Check Path: /health ✅
Health Check Interval: 30s
Health Check Timeout: 10s
Healthy Threshold: 2
Unhealthy Threshold: 5
Matcher: 200-399 ✅
```

**Port Mapping:**
- Target Group port: 80
- Container port: 3000
- ALB fait le port mapping automatiquement (traffic-port)

### 5. ECS Service (arquantix-coming-soon)

**Configuration:**
```
Task Definition: arquantix-coming-soon:3
Container Port: 3000
Environment:
  - PORT=3000
  - HOSTNAME=0.0.0.0
  - HOST=0.0.0.0
Health Check Grace Period: 180s ✅
Load Balancer: arquantix-prod-tg (port 3000)
```

---

## 🔧 Changements Appliqués

### Changement 1: Listener 80 - Redirect → Forward ✅

**Avant:**
```
Listener 80: Redirect to HTTPS:443
```

**Après:**
```
Listener 80: Forward to Target Group (arquantix-prod-tg)
```

**Commande:**
```bash
aws elbv2 modify-listener \
  --listener-arn <LISTENER_80_ARN> \
  --default-actions Type=forward,TargetGroupArn=<TG_ARN> \
  --region me-central-1
```

**Raison:** Éviter les redirect loops. CloudFront utilise HTTP vers l'ALB, donc le listener 80 doit forward, pas redirect.

### Changement 2: Target Group Health Check ✅

**Vérifié:**
- Path: `/health` ✅
- Matcher: `200-399` ✅

**Pas de changement nécessaire** - Déjà correctement configuré.

### Changement 3: CloudFront (Aucun changement) ✅

**Vérifié:**
- Viewer Protocol Policy: `redirect-to-https` ✅
- Origin Protocol Policy: `http-only` ✅

**Pas de changement nécessaire** - Déjà correctement configuré.

---

## 🧪 Tests de Preuve

### Test 1: Health Check via CloudFront
```bash
curl -I https://arquantix.com/health
```

**Attendu:**
```
HTTP/2 200
content-type: text/plain
```

**Résultat:** ✅ 200 OK

### Test 2: Page Principale via CloudFront
```bash
curl -I https://arquantix.com/
```

**Attendu:**
```
HTTP/2 200
content-type: text/html
```

**Résultat:** ✅ 200 OK

### Test 3: ALB Direct (HTTP avec Host header)
```bash
ALB_DNS="arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com"
curl -I -H "Host: arquantix.com" "http://$ALB_DNS/health"
```

**Attendu:**
```
HTTP/1.1 200 OK
```

**Résultat:** ✅ 200 OK

### Test 4: Target Group Health
```bash
aws elbv2 describe-target-health \
  --target-group-arn <TG_ARN> \
  --region me-central-1
```

**Attendu:**
```
Au moins 1 target avec Health: "healthy"
```

**Résultat:** ✅ Targets HEALTHY

---

## 📋 Checklist de Validation

- [x] Route53 pointe vers CloudFront ✅
- [x] CloudFront Viewer Protocol = redirect-to-https ✅
- [x] CloudFront Origin Protocol = http-only ✅
- [x] ALB Listener 80 = Forward to Target Group ✅
- [x] Target Group Health Check = /health, 200-399 ✅
- [x] ECS Service Health Check Grace Period = 180s ✅
- [x] `curl -I https://arquantix.com/health` → 200 ✅
- [x] `curl -I https://arquantix.com/` → 200 ✅

---

## 🔍 Pourquoi Cette Configuration Fonctionne

### Sécurité
1. **Visiteurs → CloudFront:** HTTPS (via CloudFront certificate)
2. **CloudFront → ALB:** HTTP (sur réseau AWS privé, sécurisé)
3. **ALB → ECS:** HTTP (sur réseau VPC privé)

### Performance
- Pas de double SSL termination
- Moins de latence (pas de handshake SSL entre CloudFront et ALB)
- Moins de CPU utilisé sur l'ALB

### Simplicité
- Pas besoin de certificat ACM dans me-central-1
- Pas besoin de listener 443 sur l'ALB
- Configuration plus simple à maintenir

---

## 🚨 Points d'Attention

### 1. CloudFront Cache
- Les invalidation CloudFront peuvent prendre quelques minutes
- Après modification, invalider si nécessaire: `/*`

### 2. Health Checks
- Le Target Group utilise `/health` avec matcher 200-399
- L'endpoint `/health` doit retourner 200 OK instantanément
- Pas de redirect, pas de middleware, réponse texte brut

### 3. Monitoring
- Surveiller les métriques CloudFront (erreurs 502/504)
- Surveiller les métriques ALB (target health)
- Surveiller les métriques ECS (task stability)

---

## 🔄 Rollback Plan

Si nécessaire de revenir au redirect:

```bash
# Revenir au redirect (si listener 443 créé plus tard)
aws elbv2 modify-listener \
  --listener-arn <LISTENER_80_ARN> \
  --default-actions Type=redirect,RedirectConfig='{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}' \
  --region me-central-1
```

**Note:** Ne pas faire ce rollback tant qu'il n'y a pas de listener 443 configuré.

---

## 📝 Commandes de Vérification

### Vérifier CloudFront Origin Protocol
```bash
aws cloudfront get-distribution-config \
  --id EPJ3WQCO04UWW \
  --region me-central-1 \
  --query 'DistributionConfig.Origins.Items[0].CustomOriginConfig.OriginProtocolPolicy' \
  --output text
# Attendu: http-only
```

### Vérifier ALB Listener 80
```bash
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --region me-central-1 \
  --query 'LoadBalancers[?contains(LoadBalancerName, `arquantix`)].LoadBalancerArn' \
  --output text)

LISTENER_80=$(aws elbv2 describe-listeners \
  --load-balancer-arn "$ALB_ARN" \
  --region me-central-1 \
  --query 'Listeners[?Port==`80`].ListenerArn' \
  --output text)

aws elbv2 describe-listeners \
  --listener-arns "$LISTENER_80" \
  --region me-central-1 \
  --query 'Listeners[0].DefaultActions[0].Type' \
  --output text
# Attendu: forward
```

### Vérifier Target Group Health
```bash
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:me-central-1:411714852748:targetgroup/arquantix-prod-tg/89fe413e994d9f0f \
  --region me-central-1 \
  --query 'TargetHealthDescriptions[*].TargetHealth.State' \
  --output text
# Attendu: healthy
```

---

## ✅ Status Final

**Configuration:** ✅ Stable  
**Tests:** ✅ Tous passent  
**Production:** ✅ Opérationnel

**Site accessible:**
- ✅ https://arquantix.com/health → 200 OK
- ✅ https://arquantix.com/ → 200 OK
- ✅ https://www.arquantix.com/ → 200 OK

---

**Dernière mise à jour:** 2026-01-03  
**Configuration validée:** ✅

