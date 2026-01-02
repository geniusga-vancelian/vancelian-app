# Checklist de Déploiement Arquantix - Coming Soon

**Date:** 2026-01-02  
**Version:** Coming Soon v1  
**URLs cibles:** https://arquantix.com, https://www.arquantix.com

---

## ✅ Phase 1: Git - TERMINÉ

- [x] Code commité sur branche `arquantix-coming-soon`
- [x] Workflow GitHub Actions créé: `.github/workflows/arquantix-coming-soon-deploy.yml`
- [x] Push effectué sur GitHub

**Prochaine étape:** Créer une PR vers `main` ou merger directement selon workflow.

---

## 🔄 Phase 2: CI/CD - GitHub Actions → ECR

### Secrets GitHub requis

Vérifier que ces secrets sont configurés dans GitHub (Settings → Secrets and variables → Actions):

- `AWS_ACCESS_KEY_ID` - Clé d'accès AWS
- `AWS_SECRET_ACCESS_KEY` - Clé secrète AWS
- `AWS_REGION` - Région AWS (me-central-1)

### Workflow déclenchement

Le workflow `.github/workflows/arquantix-coming-soon-deploy.yml` se déclenche automatiquement sur:
- Push vers `main` ou `arquantix-coming-soon` avec changements dans `services/arquantix/web/**`
- `workflow_dispatch` (manuel depuis GitHub Actions)

### Actions du workflow

1. ✅ Build Docker image depuis `services/arquantix/web/Dockerfile`
2. ✅ Push vers ECR: `411714852748.dkr.ecr.me-central-1.amazonaws.com/arquantix-coming-soon:latest`
3. ✅ Vérification image dans ECR
4. ⚠️ Déploiement ECS (si service existe)

**Vérification:**
- Aller sur GitHub Actions: https://github.com/geniusga-vancelian/vancelian-app/actions
- Vérifier que le workflow `Arquantix Coming Soon - Deploy to ECR & ECS` a réussi
- Vérifier dans AWS Console ECR que l'image est présente

---

## 🚀 Phase 3: ECS Fargate - Déploiement

### Ressources AWS à vérifier/créer

#### 1. ECR Repository
- **Nom:** `arquantix-coming-soon`
- **Région:** `me-central-1`
- **Status:** ✅ Confirmé existant

#### 2. ECS Cluster
- **Nom attendu:** `arquantix-cluster`
- **Vérifier existence:** AWS Console → ECS → Clusters

#### 3. Task Definition
- **Nom attendu:** `arquantix-coming-soon`
- **Image:** `411714852748.dkr.ecr.me-central-1.amazonaws.com/arquantix-coming-soon:latest`
- **Port:** 3000 (Next.js)
- **CPU:** 256 (0.25 vCPU) minimum
- **Memory:** 512 MB minimum
- **Variables d'environnement:**
  - `NODE_ENV=production`
  - `PORT=3000`

#### 4. ECS Service
- **Nom attendu:** `arquantix-coming-soon`
- **Cluster:** `arquantix-cluster`
- **Task Definition:** `arquantix-coming-soon`
- **Desired count:** 1 (minimum)
- **Load Balancer:** ALB (si configuré) ou service direct

#### 5. ALB (Application Load Balancer)
- **Target Group:** Port 3000
- **Health Check:** `/` (200 OK)
- **Listener:** Port 80 (HTTP) et/ou 443 (HTTPS)

### Commandes de déploiement manuel

Si le service ECS n'existe pas encore:

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

# 2. Créer Service ECS
aws ecs create-service \
  --cluster arquantix-cluster \
  --service-name arquantix-coming-soon \
  --task-definition arquantix-coming-soon \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --region me-central-1

# 3. Forcer nouveau déploiement (si service existe)
aws ecs update-service \
  --cluster arquantix-cluster \
  --service arquantix-coming-soon \
  --force-new-deployment \
  --region me-central-1
```

**⚠️ Remplacez:**
- `subnet-xxx` par vos subnets VPC
- `sg-xxx` par votre security group (port 3000 ouvert)

---

## 🌐 Phase 4: CloudFront + TLS (HTTPS)

### 1. Certificat ACM (us-east-1)

**⚠️ IMPORTANT:** CloudFront nécessite un certificat dans `us-east-1` (N. Virginia)

**Actions manuelles requises:**

1. Aller sur AWS Console → Certificate Manager (us-east-1)
2. Demander un certificat public:
   - Domaines: `arquantix.com`, `www.arquantix.com`
   - Validation: DNS
3. Créer les enregistrements CNAME dans Route53 (validation automatique si zone Route53)
4. Attendre validation (quelques minutes)

**Lien direct:** https://console.aws.amazon.com/acm/home?region=us-east-1#/certificates

### 2. CloudFront Distribution

**Configuration:**

- **Origin:**
  - Si ALB: `alb-dns-name.elb.me-central-1.amazonaws.com`
  - Si service direct: IP publique du service ECS (non recommandé)
- **Origin Protocol:** HTTP (CloudFront gère HTTPS)
- **Behaviors:**
  - Default: `/*`
  - Viewer Protocol Policy: Redirect HTTP to HTTPS
  - Compress: Yes
  - Cache Policy: CachingOptimized
- **Alternate Domain Names (CNAME):**
  - `arquantix.com`
  - `www.arquantix.com`
- **SSL Certificate:** Sélectionner le certificat ACM créé en us-east-1
- **Default Root Object:** `/` (ou laisser vide)

**Commandes:**

```bash
# Créer distribution CloudFront (exemple)
aws cloudfront create-distribution \
  --origin-domain-name <ALB-DNS-NAME> \
  --aliases arquantix.com www.arquantix.com \
  --viewer-certificate Certificate=<ACM-CERT-ARN> \
  --default-root-object "/" \
  --enabled
```

**Lien direct:** https://console.aws.amazon.com/cloudfront/v3/home

### 3. Route53 DNS

**Actions manuelles requises:**

1. Aller sur Route53 → Hosted Zones → `arquantix.com`
2. Créer deux enregistrements Alias:
   - **Type A (IPv4):**
     - Nom: `arquantix.com` (ou vide pour apex)
     - Alias: Oui
     - Alias Target: CloudFront Distribution (sélectionner depuis liste)
   - **Type A (IPv4):**
     - Nom: `www.arquantix.com`
     - Alias: Oui
     - Alias Target: CloudFront Distribution

**Lien direct:** https://console.aws.amazon.com/route53/v2/hostedzones

### 4. Invalidation CloudFront

Après chaque déploiement:

```bash
aws cloudfront create-invalidation \
  --distribution-id <DISTRIBUTION-ID> \
  --paths "/*"
```

**Lien direct:** CloudFront Console → Distribution → Invalidations → Create Invalidation

---

## ✅ Phase 5: Vérification finale

### Tests à effectuer

1. **HTTPS:**
   ```bash
   curl -I https://arquantix.com
   curl -I https://www.arquantix.com
   ```
   - Attendu: `200 OK`, `HTTP/2 200`

2. **Contenu:**
   - Ouvrir https://arquantix.com dans navigateur
   - Vérifier: Navbar (logo + Coming soon), Hero carousel, Footer

3. **Headers:**
   ```bash
   curl -I https://arquantix.com | grep -E "HTTP|Server|X-"
   ```

4. **Performance:**
   - CloudFront cache fonctionne
   - Images se chargent correctement

### Documentation à mettre à jour

- [ ] `docs/arquantix/STATE.md` - URLs prod, méthode de redeploy
- [ ] `docs/arquantix/DEPLOYMENT.md` - Processus complet

---

## 📋 Checklist Actionnable pour Gaël

### ✅ Automatique (fait par workflow)

- [x] Build Docker image
- [x] Push vers ECR
- [x] Déploiement ECS (si service existe)

### ⚠️ Manuel (à faire dans AWS Console)

1. **Vérifier/Créer ECS Service:**
   - Lien: https://console.aws.amazon.com/ecs/v2/clusters/arquantix-cluster/services
   - Vérifier que le service `arquantix-coming-soon` existe
   - Si non, créer avec Task Definition (voir commandes Phase 3)

2. **Créer Certificat ACM (us-east-1):**
   - Lien: https://console.aws.amazon.com/acm/home?region=us-east-1#/certificates
   - Domaines: `arquantix.com`, `www.arquantix.com`
   - Validation DNS (automatique si Route53)

3. **Créer/Configurer CloudFront:**
   - Lien: https://console.aws.amazon.com/cloudfront/v3/home
   - Origin = ALB ou service ECS
   - CNAME: `arquantix.com`, `www.arquantix.com`
   - Certificat ACM us-east-1

4. **Configurer Route53:**
   - Lien: https://console.aws.amazon.com/route53/v2/hostedzones
   - Alias A records vers CloudFront

5. **Invalidation CloudFront après déploiement:**
   - CloudFront Console → Invalidations → Create → `/*`

---

## 🔗 Liens Utiles

- **GitHub Actions:** https://github.com/geniusga-vancelian/vancelian-app/actions
- **ECR:** https://console.aws.amazon.com/ecr/repositories/private/411714852748/arquantix-coming-soon
- **ECS:** https://console.aws.amazon.com/ecs/v2/clusters
- **CloudFront:** https://console.aws.amazon.com/cloudfront/v3/home
- **Route53:** https://console.aws.amazon.com/route53/v2/hostedzones
- **ACM (us-east-1):** https://console.aws.amazon.com/acm/home?region=us-east-1#/certificates

---

**Status actuel:** Phase 1 terminée, Phase 2 en attente de déclenchement workflow

