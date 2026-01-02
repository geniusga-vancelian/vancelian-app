# Diagnostic Déploiement Arquantix

**Date:** 2026-01-03  
**Problème:** Site non visible sur https://arquantix.com

---

## 🔍 Vérifications Effectuées

### 1. URLs Production

- **https://arquantix.com** : À vérifier
- **https://www.arquantix.com** : À vérifier

### 2. CloudFront

- **Distribution ID:** `EPJ3WQCO04UWW`
- **Status:** À vérifier
- **Origin:** Actuellement S3 (`arquantix-coming-soon-dev.s3.me-central-1.amazonaws.com`)
- **Aliases:** `arquantix.com`, `www.arquantix.com`

**⚠️ PROBLÈME IDENTIFIÉ:** CloudFront pointe vers S3, pas vers ECS/ALB.

### 3. ECR

- **Repository:** `arquantix-coming-soon`
- **Dernière image:** À vérifier
- **Tag:** `latest`

### 4. ECS Fargate

- **Cluster:** `arquantix-cluster`
- **Service:** `arquantix-coming-soon`
- **Status:** À vérifier (permissions limitées)

### 5. Route53

- **Zone:** `arquantix.com` (Z08819812KDG05NSYVRFJ)
- **Enregistrements A:** 
  - `arquantix.com` → CloudFront ✅
  - `www.arquantix.com` → CloudFront ✅

---

## 🚨 Problèmes Identifiés

### Problème Principal: CloudFront Origin = S3

**Symptôme:** Le site affiche l'ancienne version statique (S3), pas la nouvelle application Next.js.

**Cause:** CloudFront pointe vers S3 au lieu de ECS/ALB.

**Solution:** Mettre à jour l'origine CloudFront pour pointer vers:
1. **Option A:** ALB (si service ECS existe avec ALB)
2. **Option B:** IP publique du service ECS (si service ECS existe sans ALB)
3. **Option C:** Créer le service ECS + ALB si non existant

---

## ✅ Actions Requises

### 1. Vérifier Service ECS

```bash
# Vérifier si le service existe
aws ecs describe-services \
  --cluster arquantix-cluster \
  --services arquantix-coming-soon \
  --region me-central-1

# Si le service n'existe pas, le créer (voir DEPLOYMENT_CHECKLIST.md)
```

### 2. Obtenir Endpoint ECS/ALB

```bash
# Si ALB existe
aws elbv2 describe-load-balancers \
  --region me-central-1 \
  --query 'LoadBalancers[?contains(LoadBalancerName, `arquantix`)].DNSName'

# Si service ECS avec IP publique
aws ecs list-tasks \
  --cluster arquantix-cluster \
  --service-name arquantix-coming-soon \
  --region me-central-1
```

### 3. Mettre à jour CloudFront Origin

1. Aller sur: https://console.aws.amazon.com/cloudfront/v3/home#/distributions/EPJ3WQCO04UWW
2. Edit distribution
3. Origins → Edit origin `S3-arquantix-coming-soon-dev`
4. Changer:
   - **Origin domain:** DNS ALB ou IP publique ECS
   - **Origin protocol:** HTTP ou HTTPS
   - **Origin path:** `/` (ou vide)
5. Save changes
6. Wait for deployment (5-15 minutes)

### 4. Invalidation CloudFront

```bash
aws cloudfront create-invalidation \
  --distribution-id EPJ3WQCO04UWW \
  --paths "/*"
```

---

## 🔗 Liens Utiles

- **CloudFront:** https://console.aws.amazon.com/cloudfront/v3/home#/distributions/EPJ3WQCO04UWW
- **ECS:** https://console.aws.amazon.com/ecs/v2/clusters
- **ECR:** https://console.aws.amazon.com/ecr/repositories/private/411714852748/arquantix-coming-soon
- **Route53:** https://console.aws.amazon.com/route53/v2/hostedzones/Z08819812KDG05NSYVRFJ

---

## 📋 Checklist

- [ ] Vérifier workflow GitHub Actions (build réussi?)
- [ ] Vérifier image ECR (dernière version?)
- [ ] Vérifier service ECS (existe et running?)
- [ ] Obtenir endpoint ECS/ALB
- [ ] Mettre à jour CloudFront origin
- [ ] Invalidation CloudFront
- [ ] Tester https://arquantix.com
- [ ] Tester https://www.arquantix.com

---

**Status:** En attente de vérification ECS et mise à jour CloudFront origin.

