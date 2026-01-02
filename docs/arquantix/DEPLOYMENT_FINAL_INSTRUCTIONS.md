# Instructions Finales - Déploiement Arquantix Coming Soon

**Date:** 2026-01-02  
**Status:** Phase 1 terminée (Git), Phases 2-5 à compléter manuellement

---

## ✅ Phase 1: Git - TERMINÉ

- [x] Code commité sur branche `arquantix-coming-soon-clean`
- [x] Workflow GitHub Actions créé: `.github/workflows/arquantix-coming-soon-deploy.yml`
- [x] Documentation créée: `docs/arquantix/DEPLOYMENT_CHECKLIST.md`

**⚠️ Action requise:** Les fichiers Arquantix ne sont pas encore trackés dans Git. Vous devez:

```bash
# Depuis la racine du repo
git add services/arquantix/web/src/ services/arquantix/web/public/ services/arquantix/web/tailwind.config.ts services/arquantix/web/src/styles/ services/arquantix/web/next.config.js services/arquantix/web/package.json services/arquantix/web/Dockerfile
git add .github/workflows/arquantix-coming-soon-deploy.yml
git add docs/arquantix/DEPLOYMENT_CHECKLIST.md
git commit -m "Arquantix: coming soon page + hero carousel + minimal layout"
git push origin arquantix-coming-soon-clean
```

**Lien PR:** https://github.com/geniusga-vancelian/vancelian-app/pull/new/arquantix-coming-soon-clean

---

## 🔄 Phase 2: CI/CD - GitHub Actions → ECR

### Secrets GitHub requis

**Vérifier dans:** GitHub → Settings → Secrets and variables → Actions

- [ ] `AWS_ACCESS_KEY_ID` - Clé d'accès AWS
- [ ] `AWS_SECRET_ACCESS_KEY` - Clé secrète AWS

**Note:** `AWS_REGION` est défini dans le workflow (me-central-1), pas besoin de secret.

### Déclencher le workflow

1. **Option A - Automatique:** Merger la branche `arquantix-coming-soon-clean` dans `main`
2. **Option B - Manuel:** Aller sur GitHub Actions → "Arquantix Coming Soon - Deploy to ECR & ECS" → Run workflow

**Lien:** https://github.com/geniusga-vancelian/vancelian-app/actions

### Vérification

- [ ] Workflow réussi (build + push ECR)
- [ ] Image visible dans ECR: `411714852748.dkr.ecr.me-central-1.amazonaws.com/arquantix-coming-soon:latest`

**Lien ECR:** https://console.aws.amazon.com/ecr/repositories/private/411714852748/arquantix-coming-soon

---

## 🚀 Phase 3: ECS Fargate - Déploiement

### Ressources à créer/vérifier

#### 1. ECR Repository ✅
- **Nom:** `arquantix-coming-soon`
- **Status:** Confirmé existant

#### 2. ECS Cluster
- **Nom attendu:** `arquantix-cluster`
- **Action:** Vérifier existence ou créer

**Lien:** https://console.aws.amazon.com/ecs/v2/clusters

#### 3. Task Definition
- **Nom:** `arquantix-coming-soon`
- **Image:** `411714852748.dkr.ecr.me-central-1.amazonaws.com/arquantix-coming-soon:latest`
- **CPU:** 256 (0.25 vCPU)
- **Memory:** 512 MB
- **Port:** 3000
- **Variables:**
  - `NODE_ENV=production`
  - `PORT=3000`

**Lien:** https://console.aws.amazon.com/ecs/v2/task-definitions

#### 4. ECS Service
- **Nom:** `arquantix-coming-soon`
- **Cluster:** `arquantix-cluster`
- **Desired count:** 1
- **Network:** VPC avec subnets publics + security group (port 3000 ouvert)

**Lien:** https://console.aws.amazon.com/ecs/v2/clusters/arquantix-cluster/services

#### 5. ALB (si nécessaire)
- **Target Group:** Port 3000
- **Health Check:** `/` (200 OK)
- **Listener:** Port 80/443

**Commandes de création (si service n'existe pas):**

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

# ⚠️ Remplacez subnet-xxx et sg-xxx par vos valeurs
```

---

## 🌐 Phase 4: CloudFront + TLS (HTTPS)

### 1. Certificat ACM (us-east-1) ⚠️ OBLIGATOIRE

**⚠️ IMPORTANT:** CloudFront nécessite un certificat dans `us-east-1` (N. Virginia)

**Actions:**

1. Aller sur: https://console.aws.amazon.com/acm/home?region=us-east-1#/certificates
2. "Request certificate" → Public certificate
3. Domaines: `arquantix.com`, `www.arquantix.com`
4. Validation: DNS
5. Créer les enregistrements CNAME dans Route53 (validation automatique)
6. Attendre validation (quelques minutes)

### 2. CloudFront Distribution

**Configuration:**

- **Origin:**
  - Si ALB: `alb-dns-name.elb.me-central-1.amazonaws.com`
  - Si service direct: IP publique ECS (non recommandé)
- **Origin Protocol:** HTTP
- **Viewer Protocol Policy:** Redirect HTTP to HTTPS
- **Compress:** Yes
- **Alternate Domain Names (CNAME):**
  - `arquantix.com`
  - `www.arquantix.com`
- **SSL Certificate:** Sélectionner le certificat ACM us-east-1

**Lien:** https://console.aws.amazon.com/cloudfront/v3/home

### 3. Route53 DNS

**Actions:**

1. Aller sur: https://console.aws.amazon.com/route53/v2/hostedzones
2. Sélectionner zone `arquantix.com`
3. Créer deux enregistrements Alias A:
   - **Nom:** `arquantix.com` (apex)
   - **Type:** A - IPv4
   - **Alias:** Oui
   - **Target:** CloudFront Distribution
   - **Nom:** `www.arquantix.com`
   - **Type:** A - IPv4
   - **Alias:** Oui
   - **Target:** CloudFront Distribution

### 4. Invalidation CloudFront

Après chaque déploiement:

```bash
aws cloudfront create-invalidation \
  --distribution-id <DISTRIBUTION-ID> \
  --paths "/*"
```

Ou depuis la console: CloudFront → Distribution → Invalidations → Create → `/*`

---

## ✅ Phase 5: Vérification finale

### Tests

```bash
# HTTPS
curl -I https://arquantix.com
curl -I https://www.arquantix.com

# Contenu
curl https://arquantix.com | grep -i "coming soon"
```

### Checklist

- [ ] https://arquantix.com → 200 OK
- [ ] https://www.arquantix.com → 200 OK
- [ ] Navbar visible (logo + Coming soon)
- [ ] Hero carousel fonctionne (2 images)
- [ ] Footer visible (logo + copyright)
- [ ] Images se chargent correctement

---

## 📋 Résumé Actions Manuelles

### ✅ Automatique (fait par workflow)

- [x] Build Docker image
- [x] Push vers ECR (si workflow déclenché)

### ⚠️ Manuel (à faire dans AWS Console)

1. **Git:**
   - [ ] Ajouter fichiers Arquantix au commit (voir Phase 1)
   - [ ] Créer PR vers main

2. **GitHub Actions:**
   - [ ] Vérifier secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
   - [ ] Déclencher workflow ou merger main

3. **ECS:**
   - [ ] Vérifier/créer cluster `arquantix-cluster`
   - [ ] Créer Task Definition `arquantix-coming-soon`
   - [ ] Créer Service ECS `arquantix-coming-soon`
   - [ ] Configurer ALB (si nécessaire)

4. **CloudFront + TLS:**
   - [ ] Créer certificat ACM us-east-1 (`arquantix.com`, `www.arquantix.com`)
   - [ ] Créer distribution CloudFront
   - [ ] Configurer Route53 (alias A records)
   - [ ] Invalidation CloudFront après déploiement

---

## 🔗 Liens Utiles

- **GitHub Actions:** https://github.com/geniusga-vancelian/vancelian-app/actions
- **ECR:** https://console.aws.amazon.com/ecr/repositories/private/411714852748/arquantix-coming-soon
- **ECS:** https://console.aws.amazon.com/ecs/v2/clusters
- **CloudFront:** https://console.aws.amazon.com/cloudfront/v3/home
- **Route53:** https://console.aws.amazon.com/route53/v2/hostedzones
- **ACM (us-east-1):** https://console.aws.amazon.com/acm/home?region=us-east-1#/certificates

---

**Status:** Phase 1 terminée. Phases 2-5 nécessitent actions manuelles dans AWS Console.

