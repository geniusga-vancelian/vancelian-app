# Plan de Remédiation - Arquantix.com Production

**Date:** 2026-01-03  
**Status:** Audit complet, corrections à appliquer

---

## 📊 État Actuel (Diagramme)

```
Route53 (arquantix.com, www.arquantix.com)
    │
    │ A/AAAA → CloudFront Distribution
    ▼
CloudFront (EPJ3WQCO04UWW)
    │ Domain: d2gtzmv0zk47i6.cloudfront.net
    │ Certificate: ACM (us-east-1)
    │ Origin: <ALB_DNS> (à vérifier)
    │ Origin Path: "" (vide)
    │
    ▼
ALB (arquantix-prod-alb)
    │ DNS: arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com
    │ Scheme: internet-facing ✅
    │ Listeners:
    │   - Port 80: HTTP → Forward to TG ✅
    │   - Port 443: ❌ MANQUANT (HTTPS non configuré)
    │
    ▼
Target Group (arquantix-prod-tg)
    │ Port: 80 ⚠️ (devrait être 3000 ou traffic-port)
    │ Protocol: HTTP
    │ Health Check: /health, 200-399 ✅
    │ Targets: 172.31.31.39:3000 (UNHEALTHY)
    │
    ▼
ECS Service (arquantix-coming-soon)
    │ Task Definition: arquantix-coming-soon:3
    │ Container Port: 3000 ✅
    │ Env: PORT=3000, HOSTNAME=0.0.0.0 ✅
    │ Health Check Grace Period: 120s ⚠️ (devrait être 180s)
    │ Running: 1 task (révision 2, pas 3)
    │
    ▼
Container (Next.js)
    │ Port: 3000 ✅
    │ Bind: 0.0.0.0 ✅
    │ Health: /health endpoint ✅
```

---

## 🚨 Problèmes Critiques Identifiés

### 1. ALB: Listener HTTPS (443) Manquant ❌

**Problème:**
- Seul le listener HTTP (80) est configuré
- Pas de listener HTTPS (443) avec certificat
- CloudFront ne peut pas utiliser HTTPS vers l'ALB

**Impact:**
- CloudFront ne peut pas se connecter en HTTPS à l'ALB
- Le site n'est pas accessible en HTTPS

**Solution:**
Créer un listener 443 avec certificat ACM

### 2. Target Group: Port Configuration ⚠️

**Problème:**
- Target Group configuré sur port 80
- Containers écoutent sur port 3000
- Health check utilise "traffic-port" (3000) mais TG port = 80

**Impact:**
- Confusion dans la configuration
- Possible problème de routage

**Solution:**
Vérifier que le port mapping est correct (ALB 80 → Container 3000)

### 3. ECS: Health Check Grace Period ⚠️

**Problème:**
- Grace period: 120s
- Recommandé: 180s pour Next.js

**Impact:**
- Containers peuvent être arrêtés avant que l'app soit prête

**Solution:**
Augmenter à 180s

### 4. ECS: Erreurs ECR Timeout ⚠️

**Problème:**
- Erreurs "unable to pull registry auth from Amazon ECR"
- Timeout de connexion à ECR

**Impact:**
- Tasks ne peuvent pas démarrer
- Containers ne peuvent pas pull l'image

**Solution:**
Vérifier la configuration réseau (NAT Gateway, VPC endpoints)

### 5. CloudFront: Origin Configuration ⚠️

**Problème:**
- Origin doit pointer vers ALB DNS
- Origin path doit être vide
- Protocol policy doit être HTTPS Only

**Impact:**
- CloudFront ne peut pas atteindre l'ALB
- Site inaccessible

**Solution:**
Vérifier et corriger la configuration CloudFront

---

## 🔧 Changements AWS à Appliquer

### Changement 1: Créer Listener HTTPS sur ALB ❌ CRITIQUE

**Problème identifié:**
- CloudFront origin protocol: "http-only"
- ALB n'a pas de listener 443
- CloudFront ne peut pas se connecter en HTTPS

**Étape 1: Créer certificat ACM dans me-central-1 (si absent)**

```bash
# Créer le certificat
CERT_ARN=$(aws acm request-certificate \
  --domain-name arquantix.com \
  --subject-alternative-names www.arquantix.com \
  --validation-method DNS \
  --region me-central-1 \
  --query 'CertificateArn' --output text)

# Récupérer les CNAME de validation
aws acm describe-certificate \
  --certificate-arn "$CERT_ARN" \
  --region me-central-1 \
  --query 'Certificate.DomainValidationOptions[*].ResourceRecord'

# Ajouter les CNAME dans Route53 pour validation
ZONE_ID=$(aws route53 list-hosted-zones \
  --query "HostedZones[?Name=='arquantix.com.'].Id" \
  --output text | sed 's|/hostedzone/||')

# Créer les records de validation (voir script complet dans la doc)
# Attendre la validation (peut prendre 5-30 minutes)
```

**Status:** ✅ Certificat créé, validation en cours

**Étape 2: Créer le listener 443**

```bash
# Récupérer le certificat ACM validé
CERT_ARN=$(aws acm list-certificates \
  --region me-central-1 \
  --query 'CertificateSummaryList[?contains(DomainName, `arquantix`) && Status==`ISSUED`].CertificateArn' \
  --output text | head -1)

# Récupérer l'ALB ARN
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --region me-central-1 \
  --query 'LoadBalancers[?contains(LoadBalancerName, `arquantix`)].LoadBalancerArn' \
  --output text)

TG_ARN="arn:aws:elasticloadbalancing:me-central-1:411714852748:targetgroup/arquantix-prod-tg/89fe413e994d9f0f"

# Créer le listener 443
aws elbv2 create-listener \
  --load-balancer-arn "$ALB_ARN" \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn="$CERT_ARN" \
  --default-actions Type=forward,TargetGroupArn="$TG_ARN" \
  --region me-central-1
```

**Raison:** CloudFront nécessite HTTPS vers l'ALB. Actuellement, CloudFront est configuré en "http-only" mais essaie de se connecter en HTTPS (port 443) qui n'existe pas.

### Changement 2: Mettre à jour Listener 80 pour Redirect vers 443

```bash
LISTENER_80=$(aws elbv2 describe-listeners \
  --load-balancer-arn "$ALB_ARN" \
  --region me-central-1 \
  --query 'Listeners[?Port==`80`].ListenerArn' \
  --output text)

aws elbv2 modify-listener \
  --listener-arn "$LISTENER_80" \
  --default-actions Type=redirect,RedirectConfig='{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}' \
  --region me-central-1
```

**Raison:** Forcer HTTPS pour toutes les requêtes

### Changement 3: Augmenter Health Check Grace Period

```bash
aws ecs update-service \
  --cluster arquantix-cluster \
  --service arquantix-coming-soon \
  --health-check-grace-period-seconds 180 \
  --region me-central-1
```

**Raison:** Donner plus de temps à Next.js pour démarrer

### Changement 4: Mettre à jour CloudFront Origin Protocol ⚠️

**État actuel:**
- Origin Domain: ✅ ALB DNS (correct)
- Origin Path: ✅ "" (vide, correct)
- Protocol Policy: ❌ "http-only" (doit être "https-only")

**Changement:**
```bash
# Récupérer la config CloudFront
aws cloudfront get-distribution-config \
  --id EPJ3WQCO04UWW \
  --region me-central-1 > /tmp/cf-config.json

# Extraire l'ETag
ETAG=$(cat /tmp/cf-config.json | python3 -c "import sys, json; print(json.load(sys.stdin)['ETag'])")

# Modifier le protocol policy
python3 << 'EOF'
import json

with open('/tmp/cf-config.json', 'r') as f:
    config = json.load(f)['DistributionConfig']

# Modifier le protocol policy
config['Origins']['Items'][0]['CustomOriginConfig']['OriginProtocolPolicy'] = 'https-only'

# Sauvegarder
with open('/tmp/cf-config-updated.json', 'w') as f:
    json.dump({'DistributionConfig': config}, f, indent=2)

print("✅ Config mise à jour: https-only")
EOF

# Appliquer la mise à jour
aws cloudfront update-distribution \
  --id EPJ3WQCO04UWW \
  --if-match "$ETAG" \
  --distribution-config file:///tmp/cf-config-updated.json \
  --region me-central-1
```

**Raison:** CloudFront doit utiliser HTTPS vers l'ALB une fois le listener 443 créé.
**Note:** À faire APRÈS la création du listener 443.

### Changement 5: Corriger Target Group Port (si nécessaire)

Si le Target Group doit être sur port 3000:

```bash
# Note: On ne peut pas modifier le port d'un Target Group existant
# Il faut créer un nouveau Target Group sur port 3000
# Puis mettre à jour l'ALB pour utiliser le nouveau TG
```

**Raison:** Aligner le port du Target Group avec le container

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

### Test 3: ALB Direct (HTTP avec Host header)
```bash
ALB_DNS="arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com"
curl -I -H "Host: arquantix.com" "http://$ALB_DNS/health"
# Attendu: HTTP/1.1 200 (ou 301 redirect si listener 80 modifié)
```

### Test 4: ALB Direct (HTTPS avec Host header)
```bash
ALB_DNS="arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com"
curl -I -k -H "Host: arquantix.com" "https://$ALB_DNS/health"
# Attendu: HTTP/1.1 200 (après création du listener 443)
```

### Test 5: Target Group Health
```bash
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:me-central-1:411714852748:targetgroup/arquantix-prod-tg/89fe413e994d9f0f \
  --region me-central-1 \
  --query 'TargetHealthDescriptions[*].{Target:Target.Id,Health:TargetHealth.State}'
# Attendu: Au moins 1 target avec Health: "healthy"
```

### Test 6: ECS Tasks Stables
```bash
aws ecs describe-services \
  --cluster arquantix-cluster \
  --services arquantix-coming-soon \
  --region me-central-1 \
  --query 'services[0].{RunningCount:runningCount,DesiredCount:desiredCount,Deployments:deployments[*].{Status:status,TaskDefinition:taskDefinition}}'
# Attendu: RunningCount == DesiredCount == 1, PRIMARY deployment avec révision 3
```

---

## 🔄 Plan de Rollback

### Rollback 1: Supprimer Listener 443
```bash
LISTENER_443=$(aws elbv2 describe-listeners \
  --load-balancer-arn "$ALB_ARN" \
  --region me-central-1 \
  --query 'Listeners[?Port==`443`].ListenerArn' \
  --output text)

aws elbv2 delete-listener \
  --listener-arn "$LISTENER_443" \
  --region me-central-1
```

### Rollback 2: Restaurer Listener 80
```bash
LISTENER_80=$(aws elbv2 describe-listeners \
  --load-balancer-arn "$ALB_ARN" \
  --region me-central-1 \
  --query 'Listeners[?Port==`80`].ListenerArn' \
  --output text)

TG_ARN="arn:aws:elasticloadbalancing:me-central-1:411714852748:targetgroup/arquantix-prod-tg/89fe413e994d9f0f"

aws elbv2 modify-listener \
  --listener-arn "$LISTENER_80" \
  --default-actions Type=forward,TargetGroupArn="$TG_ARN" \
  --region me-central-1
```

### Rollback 3: Health Check Grace Period
```bash
aws ecs update-service \
  --cluster arquantix-cluster \
  --service arquantix-coming-soon \
  --health-check-grace-period-seconds 120 \
  --region me-central-1
```

### Rollback 4: Task Definition
```bash
aws ecs update-service \
  --cluster arquantix-cluster \
  --service arquantix-coming-soon \
  --task-definition arquantix-coming-soon:2 \
  --region me-central-1
```

---

## 📋 Checklist de Validation Finale

- [ ] Route53: arquantix.com et www → CloudFront ✅
- [ ] CloudFront: Origin = ALB DNS, Path = "", Protocol = HTTPS Only
- [ ] ALB: Listener 80 → Redirect 443, Listener 443 → Forward TG
- [ ] Target Group: Au moins 1 target HEALTHY
- [ ] ECS Service: 1 task RUNNING stable (révision 3)
- [ ] Security Groups: Règles correctes ✅
- [ ] Health check: `curl -I https://arquantix.com/health` → 200
- [ ] Page principale: `curl -I https://arquantix.com/` → 200

---

**Dernière mise à jour:** 2026-01-03

