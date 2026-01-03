# Vérification Déploiement Arquantix Coming Soon

**Date:** 2026-01-03  
**Objectif:** Vérifier que tout est correctement connecté

---

## ✅ Checklist de Vérification

### 1. Service ECS

- [ ] Service `arquantix-coming-soon` existe
- [ ] Status: ACTIVE
- [ ] Running: 1/1 tasks
- [ ] Task Definition: `arquantix-coming-soon:1` (ou dernière révision)
- [ ] Image: `arquantix-coming-soon:latest`

### 2. Task ECS

- [ ] LastStatus: RUNNING
- [ ] HealthStatus: (UNKNOWN est normal pour Fargate)
- [ ] Image correspond à la dernière version

### 3. Target Group

- [ ] Target enregistré: IP privée du service ECS
- [ ] Health: HEALTHY
- [ ] Port: 3000
- [ ] Health Check Path: `/fr`

### 4. ALB

- [ ] ALB existe: `arquantix-prod-alb`
- [ ] DNS accessible
- [ ] Listener configuré (HTTP:80 → Target Group)

### 5. CloudFront

- [ ] Distribution: `EPJ3WQCO04UWW`
- [ ] Status: Deployed
- [ ] Origin: ALB (pas S3!)
- [ ] Origin Domain: DNS de l'ALB
- [ ] Aliases: `arquantix.com`, `www.arquantix.com`

### 6. Route53

- [ ] Zone: `arquantix.com`
- [ ] Records A: `arquantix.com` → CloudFront
- [ ] Records A: `www.arquantix.com` → CloudFront

### 7. Security Groups

- [ ] ECS Security Group autorise le trafic depuis ALB SG
- [ ] Port: 3000
- [ ] Protocol: TCP

### 8. Tests Fonctionnels

- [ ] ALB répond sur `/fr`
- [ ] CloudFront répond sur `https://www.arquantix.com`
- [ ] Contenu affiché: Nouvelle version Next.js (pas l'ancienne S3)

---

## 🔍 Commandes de Vérification

### Service ECS

```bash
aws ecs describe-services \
  --cluster arquantix-cluster \
  --services arquantix-coming-soon \
  --region me-central-1 \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}'
```

### Target Group Health

```bash
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:me-central-1:411714852748:targetgroup/arquantix-prod-tg/89fe413e994d9f0f \
  --region me-central-1
```

### CloudFront Origin

```bash
aws cloudfront get-distribution-config \
  --id EPJ3WQCO04UWW \
  --query 'DistributionConfig.Origins.Items[0].DomainName'
```

### Test ALB

```bash
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --region me-central-1 \
  --query 'LoadBalancers[?LoadBalancerName==`arquantix-prod-alb`].DNSName' \
  --output text)

curl -I http://$ALB_DNS/fr
```

### Test CloudFront

```bash
curl -I https://www.arquantix.com
curl -s https://www.arquantix.com | grep -i "FRACTIONAL"
```

---

## 🚨 Problèmes Potentiels

### Target Group Unhealthy

**Symptômes:**
- Health: unhealthy
- Reason: Target.Timeout ou Target.ResponseCodeMismatch

**Solutions:**
1. Vérifier Security Group (ALB → ECS port 3000)
2. Vérifier Health Check Path (`/fr`)
3. Vérifier les logs du service ECS

### CloudFront pointe vers S3

**Symptômes:**
- Origin Domain: `*.s3.*.amazonaws.com`
- Contenu: Ancienne version HTML statique

**Solution:**
- Mettre à jour CloudFront origin vers ALB DNS

### Service ECS ne démarre pas

**Symptômes:**
- Running: 0/1
- StoppedReason: (erreur)

**Solutions:**
1. Vérifier les logs CloudWatch
2. Vérifier Task Definition
3. Vérifier image ECR existe

---

## 📋 Architecture Attendue

```
Route53
  arquantix.com → CloudFront
  www.arquantix.com → CloudFront

CloudFront (EPJ3WQCO04UWW)
  Origin: ALB DNS

ALB (arquantix-prod-alb)
  Listener: HTTP:80 → Target Group

Target Group (arquantix-prod-tg)
  Health Check: /fr
  Target: ECS IP:3000 (HEALTHY)

Service ECS (arquantix-coming-soon)
  Image: arquantix-coming-soon:latest
  Status: RUNNING (1/1)
  Port: 3000
```

---

## 🔗 Liens de Vérification

- **ECS:** https://console.aws.amazon.com/ecs/v2/clusters/arquantix-cluster/services
- **Target Group:** https://console.aws.amazon.com/ec2/v2/home#TargetGroups:
- **ALB:** https://console.aws.amazon.com/ec2/v2/home#LoadBalancers:
- **CloudFront:** https://console.aws.amazon.com/cloudfront/v3/home#/distributions/EPJ3WQCO04UWW
- **Route53:** https://console.aws.amazon.com/route53/v2/hostedzones/Z08819812KDG05NSYVRFJ
- **Logs ECS:** https://console.aws.amazon.com/cloudwatch/home?region=me-central-1#logsV2:log-groups/log-group/$252Fecs$252Farquantix-coming-soon

---

**Date de vérification:** À compléter  
**Résultat:** À compléter

