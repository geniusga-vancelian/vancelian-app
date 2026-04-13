# Deployment - Arquantix Vitrine + CMS

**Date:** 2026-01-01  
**Status:** 🚧 En cours de développement

---

## TL;DR

Guide de déploiement pour Arquantix: Next.js sur AWS ECS/ALB, Strapi optionnel (dev local pour le moment).

---

## Ce qui est vrai aujourd'hui

### Stratégie de Déploiement Actuelle

- **Next.js Web:** Déploiement sur AWS ECS/ALB (prévu)
- **Strapi CMS:** Développement local uniquement (pas de déploiement prod pour le moment)

---

## Déploiement Next.js (Site Vitrine)

### Architecture Production

```
┌─────────────────┐
│   CloudFront    │  (CDN + HTTPS)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ALB (AWS)      │  (Load Balancer)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ECS Fargate    │
│  ┌───────────┐  │
│  │ Next.js   │  │  (Site Vitrine)
│  └───────────┘  │
└─────────────────┘
```

### Étapes de Déploiement

#### 1. Build de l'Image Docker

```bash
cd services/arquantix/web

# Build local (test)
docker build -t arquantix-web:latest .

# Ou via Docker Compose
docker compose -f docker-compose.arquantix.yml build arquantix-web
```

#### 2. Push vers ECR

```bash
# Variables d'environnement
export AWS_REGION=me-central-1
export ECR_REGISTRY=411714852748.dkr.ecr.me-central-1.amazonaws.com
export ECR_REPOSITORY=arquantix-web
export IMAGE_TAG=latest

# Login ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_REGISTRY

# Tag image
docker tag arquantix-web:latest $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG

# Push
docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
```

#### 3. Configuration ECS

**Task Definition:**
- Container: `arquantix-web`
- Image: `411714852748.dkr.ecr.me-central-1.amazonaws.com/arquantix-web:latest`
- Port: `3000`
- Variables d'environnement:
  - `NODE_ENV=production`
  - `NEXT_PUBLIC_STRAPI_URL` (si Strapi en prod, sinon optionnel)
  - `NEXT_PUBLIC_STRAPI_API_URL` (si Strapi en prod, sinon optionnel)

**Service ECS:**
- Cluster: (existant ou nouveau)
- Service: `arquantix-web`
- Task Definition: (révision)
- Desired Count: 1 (ou plus)
- Load Balancer: ALB existant (ou nouveau)

**Target Group:**
- Port: 3000
- Health Check Path: `/` (ou `/health` si configuré)
- Protocol: HTTP

**ALB Listener:**
- Port: 443 (HTTPS)
- Certificate: ACM (SSL)
- Rules: Route vers `arquantix-web` target group

#### 4. Variables d'Environnement Production

Créer ou mettre à jour la Task Definition avec:

```bash
NODE_ENV=production
NEXT_PUBLIC_STRAPI_URL=https://cms.arquantix.com  # Si Strapi en prod
NEXT_PUBLIC_STRAPI_API_URL=https://cms.arquantix.com/api  # Si Strapi en prod
```

#### 5. Workflow GitHub Actions

Le workflow GitHub Actions est configuré pour:
- Builder l'image Docker
- Pousser vers ECR
- (Optionnel) Déclencher un déploiement ECS

Voir `.github/workflows/arquantix-web-deploy.yml` (à créer).

---

## Déploiement Strapi (Optionnel)

### Option 1: Strapi sur ECS (Recommandé pour Production)

**Architecture:**
```
┌─────────────────┐
│  ECS Fargate    │
│  ┌───────────┐  │
│  │  Strapi   │  │
│  └───────────┘  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  RDS PostgreSQL │
└─────────────────┘
```

**Étapes:**

1. **Créer RDS PostgreSQL:**
   - Engine: PostgreSQL 15
   - Instance: (selon charge)
   - Database: `arquantix_cms`
   - User: `strapi`
   - Password: (secret)

2. **Build et Push Image Strapi:**
   ```bash
   cd services/arquantix/cms
   docker build -t arquantix-cms:latest .
   # Push vers ECR (similaire à Next.js)
   ```

3. **Configuration ECS:**
   - Container: `arquantix-cms`
   - Image: ECR
   - Port: 1338
   - Variables d'environnement:
     - `DATABASE_HOST` (RDS endpoint)
     - `DATABASE_NAME=arquantix_cms`
     - `DATABASE_USERNAME=strapi`
     - `DATABASE_PASSWORD` (secret)
     - `DATABASE_SSL=true`
     - Tous les secrets Strapi (APP_KEYS, etc.)

4. **ALB pour Strapi:**
   - Créer un ALB séparé (ou utiliser le même avec des règles)
   - Port: 443 (HTTPS)
   - Certificate: ACM
   - Domain: `cms.arquantix.com`

### Option 2: Strapi sur EC2 (Alternative)

Déployer Strapi sur une instance EC2 avec PostgreSQL:
- Installer Node.js, PM2
- Cloner le repo
- Configurer Nginx comme reverse proxy
- Configurer SSL (Let's Encrypt ou ACM)

### Option 3: Garder Strapi en Dev Local (MVP)

Pour le MVP, garder Strapi en développement local:
- Contenu généré au build (SSG)
- Ou contenu statique dans le code
- Pas de CMS en prod

---

## Workflow GitHub Actions

### Workflow Existant

Le workflow `arquantix-push-to-ecr.yml` existe pour `arquantix-coming-soon`.

### Workflow pour Next.js Web

Créer `.github/workflows/arquantix-web-deploy.yml`:

```yaml
name: Arquantix Web - Deploy to ECS

on:
  push:
    branches: [ "main" ]
    paths:
      - "services/arquantix/web/**"
      - ".github/workflows/arquantix-web-deploy.yml"
  workflow_dispatch:

env:
  AWS_REGION: me-central-1
  ECR_REGISTRY: 411714852748.dkr.ecr.me-central-1.amazonaws.com
  ECR_REPOSITORY: arquantix-web
  ECS_SERVICE: arquantix-web
  ECS_CLUSTER: arquantix-cluster
  ECS_TASK_DEFINITION: arquantix-web

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: Build Docker image
        run: |
          docker build \
            -t ${{ env.ECR_REGISTRY }}/${{ env.ECR_REPOSITORY }}:latest \
            -f services/arquantix/web/Dockerfile \
            services/arquantix/web
      
      - name: Push Docker image to ECR
        run: |
          docker push ${{ env.ECR_REGISTRY }}/${{ env.ECR_REPOSITORY }}:latest
      
      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster ${{ env.ECS_CLUSTER }} \
            --service ${{ env.ECS_SERVICE }} \
            --force-new-deployment \
            --region ${{ env.AWS_REGION }}
```

---

## Checklist de Déploiement

- [ ] ECR repository créé: `arquantix-web`
- [ ] ECS cluster créé (ou existant)
- [ ] ECS Task Definition créée
- [ ] ECS Service créé
- [ ] ALB configuré (ou existant)
- [ ] Target Group créé
- [ ] Certificate ACM créé (si HTTPS)
- [ ] Route53 configuré (si domaine personnalisé)
- [ ] Variables d'environnement configurées dans Task Definition
- [ ] Workflow GitHub Actions créé et configuré
- [ ] Secrets GitHub configurés (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
- [ ] Test de déploiement réussi
- [ ] Health checks fonctionnent
- [ ] Site accessible (production URL)

---

## À vérifier quand ça casse

### Build Docker échoue

1. Vérifier les erreurs de build dans les logs
2. Vérifier les dépendances (package.json)
3. Vérifier les Dockerfiles

### Push ECR échoue

1. Vérifier les permissions AWS (ECR:PushImage)
2. Vérifier que le repository ECR existe
3. Vérifier la région AWS

### Déploiement ECS échoue

1. Vérifier les logs ECS (CloudWatch)
2. Vérifier la Task Definition (variables d'environnement, image)
3. Vérifier les permissions ECS (ecs:UpdateService)
4. Vérifier que le service ECS existe

### Health Check échoue

1. Vérifier que le container écoute sur le bon port (3000)
2. Vérifier que le health check path existe (`/` ou `/health`)
3. Vérifier les security groups (port 3000 ouvert)

### Site inaccessible

1. Vérifier ALB (status, listeners)
2. Vérifier Target Group (targets registered, healthy)
3. Vérifier Route53 (record DNS correct)
4. Vérifier Certificate ACM (valid, attached)

---

**Dernière mise à jour:** 2026-01-01

