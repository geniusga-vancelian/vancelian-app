# Cartographie Complète AWS - Arquantix

**Date:** 2026-01-03  
**Objectif:** Cartographier le flux complet DNS → CloudFront → ALB → ECS

---

## 📊 Schéma du Flux

```
Internet
  ↓
Route53 (arquantix.com, www.arquantix.com)
  ↓ (A/AAAA Alias)
CloudFront Distribution (EPJ3WQCO04UWW)
  ↓ (Origin)
ALB (arquantix-prod-alb)
  ↓ (Listener HTTP:80)
Target Group (arquantix-prod-tg)
  ↓ (Health Check)
ECS Service (arquantix-coming-soon)
  ↓ (Task)
Container Next.js (Port 3000)
```

---

## 1. Route53

### Hosted Zone
- **Zone ID:** `Z08819812KDG05NSYVRFJ`
- **Domain:** `arquantix.com`

### Records
- **arquantix.com (A):** Alias → CloudFront `d2gtzmv0zk47i6.cloudfront.net`
- **www.arquantix.com (A):** Alias → CloudFront `d2gtzmv0zk47i6.cloudfront.net`

---

## 2. CloudFront

### Distribution
- **ID:** `EPJ3WQCO04UWW`
- **Domain:** `d2gtzmv0zk47i6.cloudfront.net`
- **Status:** `Deployed`
- **Aliases:** `arquantix.com`, `www.arquantix.com`

### Origin
- **ID:** `S3-arquantix-coming-soon-dev`
- **Domain:** `arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com` (ALB DNS)
- **Path:** (vide)
- **Protocol:** `http-only` (CustomOriginConfig)
- **HTTPS Port:** `443`
- **HTTP Port:** `80`

---

## 3. ALB (Application Load Balancer)

### Load Balancer
- **Name:** `arquantix-prod-alb`
- **DNS:** `arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com`
- **Scheme:** `internet-facing`
- **Region:** `me-central-1`

### Listeners
- **HTTP:80:** Forward to Target Group `arquantix-prod-tg`
- **HTTPS:443:** (non configuré actuellement)

### Security Group
- **ID:** `sg-028cb5d34807b8248`
- **Inbound:** 
  - HTTP (80) from 0.0.0.0/0
  - HTTPS (443) from 0.0.0.0/0

---

## 4. Target Group

### Configuration
- **Name:** `arquantix-prod-tg`
- **ARN:** `arn:aws:elasticloadbalancing:me-central-1:411714852748:targetgroup/arquantix-prod-tg/89fe413e994d9f0f`
- **Port:** `3000` (traffic-port)
- **Protocol:** `HTTP`
- **VPC:** (défaut)

### Health Check
- **Path:** `/fr`
- **Port:** `traffic-port` (3000)
- **Protocol:** `HTTP`
- **Interval:** `30` secondes
- **Timeout:** `10` secondes
- **Healthy Threshold:** `5` checks
- **Unhealthy Threshold:** `2` checks
- **Success Codes:** `200`

### Targets
- **Target:** `172.31.5.199:3000` (IP privée ECS)
- **Health:** `unhealthy`
- **Reason:** `Target.FailedHealthChecks`

---

## 5. ECS

### Cluster
- **Name:** `arquantix-cluster`
- **Region:** `me-central-1`

### Service
- **Name:** `arquantix-coming-soon`
- **Task Definition:** `arquantix-coming-soon:1`
- **Desired:** `1`
- **Running:** `1`
- **Status:** `ACTIVE`

### Task Definition
- **Family:** `arquantix-coming-soon`
- **Revision:** `1`
- **Container:**
  - **Name:** `arquantix-web`
  - **Image:** `411714852748.dkr.ecr.me-central-1.amazonaws.com/arquantix-coming-soon:latest`
  - **Port Mappings:**
    - **Container Port:** `3000`
    - **Protocol:** `tcp`
  - **Environment:**
    - `NODE_ENV=production`
    - `PORT=3000`
    - `HOSTNAME=0.0.0.0`

### Network
- **Task IP:** `172.31.5.199` (privée)
- **Security Group:** `sg-0205603e4e671f752`

---

## 6. Security Groups

### ECS Security Group (`sg-0205603e4e671f752`)
**Inbound Rules:**
- **Port 3000 TCP** from Security Group `sg-028cb5d34807b8248` (ALB SG)
- ✅ Correctement configuré

### ALB Security Group (`sg-028cb5d34807b8248`)
**Inbound Rules:**
- **Port 80** from `0.0.0.0/0`
- **Port 443** from `0.0.0.0/0`
- ✅ Correctement configuré

---

## 🔍 Points de Vérification

### ✅ Configurations Correctes
1. Route53 → CloudFront: ✅ Alias configuré
2. CloudFront → ALB: ✅ Origin pointant vers ALB DNS
3. ALB → Target Group: ✅ Listener forward vers TG
4. Security Groups: ✅ ECS autorise ALB sur port 3000
5. Port Mapping: ✅ Container port 3000 = Target Group port 3000

### ⚠️ Problèmes Identifiés
1. **Health Check Path:** `/fr` (devrait être `/health`)
2. **Target Health:** `unhealthy` (FailedHealthChecks)
3. **CloudFront Origin Path:** Vide (correct, mais vérifier)

---

## 📋 Checklist de Validation

- [ ] Route53 records pointent vers CloudFront
- [ ] CloudFront origin pointe vers ALB DNS
- [ ] ALB listener forward vers Target Group
- [ ] Target Group port = Container port (3000)
- [ ] Security Group ECS autorise ALB
- [ ] Health check path existe et répond 200
- [ ] Container écoute sur `0.0.0.0:3000`

---

**Dernière mise à jour:** 2026-01-03

