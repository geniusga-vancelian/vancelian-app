# Status Déploiement Arquantix - Coming Soon

**Date:** 2026-01-02  
**Status:** En cours

---

## ✅ Phase 1: Git - TERMINÉE

- [x] Code commité et poussé sur `main`
- [x] Workflow GitHub Actions créé: `.github/workflows/arquantix-coming-soon-deploy.yml`
- [x] Documentation créée

**Commit:** `93dec5f3`  
**Branch:** `main`  
**Remote:** https://github.com/geniusga-vancelian/vancelian-app

---

## 🔄 Phase 2: CI/CD - GitHub Actions → ECR

### Workflow déclenché

Le workflow `arquantix-coming-soon-deploy.yml` devrait s'être déclenché automatiquement après le push sur `main`.

**Vérifier:** https://github.com/geniusga-vancelian/vancelian-app/actions/workflows/arquantix-coming-soon-deploy.yml

### Secrets requis

Les secrets suivants doivent être configurés dans GitHub:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

**Vérifier:** GitHub → Settings → Secrets and variables → Actions

### Actions du workflow

1. Build Docker image depuis `services/arquantix/web/Dockerfile`
2. Push vers ECR: `411714852748.dkr.ecr.me-central-1.amazonaws.com/arquantix-coming-soon:latest`
3. Vérification image dans ECR
4. Déploiement ECS (si service existe)

### Vérification ECR

**Repository:** `arquantix-coming-soon` ✅ Existe  
**Région:** `me-central-1`  
**URI:** `411714852748.dkr.ecr.me-central-1.amazonaws.com/arquantix-coming-soon`

**Vérifier:** https://console.aws.amazon.com/ecr/repositories/private/411714852748/arquantix-coming-soon

---

## 🚀 Phase 3: ECS Fargate

### Status actuel

**⚠️ Permissions insuffisantes pour créer les ressources ECS directement.**

Le workflow GitHub Actions (avec les secrets AWS) devrait créer:
- Task Definition: `arquantix-coming-soon`
- Service ECS: `arquantix-coming-soon` (si cluster existe)

### Ressources nécessaires

1. **Cluster ECS:** `arquantix-cluster`
2. **Task Definition:** `arquantix-coming-soon`
   - Image: `411714852748.dkr.ecr.me-central-1.amazonaws.com/arquantix-coming-soon:latest`
   - CPU: 256 (0.25 vCPU)
   - Memory: 512 MB
   - Port: 3000
3. **Service ECS:** `arquantix-coming-soon`
   - Desired count: 1
   - Launch type: FARGATE
4. **ALB (optionnel):** Pour exposer le service

### Commandes (à exécuter avec permissions appropriées)

```bash
# 1. Créer Task Definition
aws ecs register-task-definition \
  --family arquantix-coming-soon \
  --cpu 256 \
  --memory 512 \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --container-definitions '[
    {
      "name": "arquantix-coming-soon",
      "image": "411714852748.dkr.ecr.me-central-1.amazonaws.com/arquantix-coming-soon:latest",
      "portMappings": [{"containerPort": 3000, "protocol": "tcp"}],
      "environment": [
        {"name": "NODE_ENV", "value": "production"},
        {"name": "PORT", "value": "3000"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/arquantix-coming-soon",
          "awslogs-region": "me-central-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]' \
  --region me-central-1

# 2. Créer Service ECS (remplacer subnet-xxx et sg-xxx)
aws ecs create-service \
  --cluster arquantix-cluster \
  --service-name arquantix-coming-soon \
  --task-definition arquantix-coming-soon \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --region me-central-1
```

**Lien ECS:** https://console.aws.amazon.com/ecs/v2/clusters

---

## 🌐 Phase 4: CloudFront + TLS

### Certificat ACM ✅

**Status:** Certificat existant et valide  
**ARN:** `arn:aws:acm:us-east-1:411714852748:certificate/7584c7ad-8090-4cbc-85e1-1f80c1530508`  
**Domaines:** `arquantix.com`, `www.arquantix.com`  
**Status:** ISSUED  
**Région:** us-east-1 ✅

**Lien:** https://console.aws.amazon.com/acm/home?region=us-east-1#/certificates

### Route53 ✅

**Zone:** `arquantix.com` ✅ Existe  
**Zone ID:** `Z08819812KDG05NSYVRFJ`

**Lien:** https://console.aws.amazon.com/route53/v2/hostedzones

### CloudFront

**Status:** À vérifier/créer

**Configuration requise:**
- Origin: ALB ou service ECS (selon architecture)
- Alternate Domain Names: `arquantix.com`, `www.arquantix.com`
- SSL Certificate: Certificat ACM us-east-1 (déjà créé)
- Viewer Protocol Policy: Redirect HTTP to HTTPS

**Lien:** https://console.aws.amazon.com/cloudfront/v3/home

### Actions CloudFront

1. **Créer/Configurer Distribution:**
   - Origin = ALB DNS ou IP publique ECS
   - CNAME: `arquantix.com`, `www.arquantix.com`
   - Certificat: `arn:aws:acm:us-east-1:411714852748:certificate/7584c7ad-8090-4cbc-85e1-1f80c1530508`

2. **Configurer Route53:**
   - Créer alias A records vers CloudFront Distribution
   - `arquantix.com` → CloudFront
   - `www.arquantix.com` → CloudFront

3. **Invalidation après déploiement:**
   ```bash
   aws cloudfront create-invalidation \
     --distribution-id <DISTRIBUTION-ID> \
     --paths "/*"
   ```

---

## 📋 Checklist Finale

### Automatique (workflow GitHub Actions)

- [x] Code poussé sur main
- [ ] Workflow déclenché (vérifier GitHub Actions)
- [ ] Image buildée et poussée sur ECR
- [ ] Déploiement ECS (si service existe)

### Manuel (AWS Console)

- [ ] Vérifier workflow GitHub Actions réussi
- [ ] Vérifier image dans ECR
- [ ] Créer/vérifier Cluster ECS `arquantix-cluster`
- [ ] Créer Task Definition `arquantix-coming-soon`
- [ ] Créer Service ECS `arquantix-coming-soon`
- [ ] Configurer ALB (si nécessaire)
- [ ] Créer/Configurer CloudFront Distribution
- [ ] Configurer Route53 (alias A records)
- [ ] Invalidation CloudFront
- [ ] Tester https://arquantix.com
- [ ] Tester https://www.arquantix.com

---

## 🔗 Liens Utiles

- **GitHub Actions:** https://github.com/geniusga-vancelian/vancelian-app/actions
- **ECR:** https://console.aws.amazon.com/ecr/repositories/private/411714852748/arquantix-coming-soon
- **ECS:** https://console.aws.amazon.com/ecs/v2/clusters
- **CloudFront:** https://console.aws.amazon.com/cloudfront/v3/home
- **Route53:** https://console.aws.amazon.com/route53/v2/hostedzones
- **ACM (us-east-1):** https://console.aws.amazon.com/acm/home?region=us-east-1#/certificates

---

**Prochaine étape:** Vérifier le workflow GitHub Actions et créer les ressources ECS si nécessaire.

