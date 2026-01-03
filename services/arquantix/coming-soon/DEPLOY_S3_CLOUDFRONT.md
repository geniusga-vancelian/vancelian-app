# Déploiement Arquantix - S3 + CloudFront

**Date:** 2026-01-01  
**Service:** Arquantix Coming Soon  
**Méthode:** S3 Static Website Hosting + CloudFront CDN

---

## Architecture

```
User → Route53 (arquantix.com) → CloudFront → S3 Bucket (arquantix-coming-soon)
```

---

## Étapes de Déploiement

### 1. Créer le Bucket S3

```bash
# Créer le bucket (nom doit être unique globalement)
aws s3 mb s3://arquantix-coming-soon --region me-central-1

# Ou avec nom plus spécifique
aws s3 mb s3://arquantix-coming-soon-dev --region me-central-1
```

**Configuration du bucket:**
- **Nom:** `arquantix-coming-soon` (ou `arquantix-coming-soon-dev`)
- **Région:** `me-central-1`
- **Block Public Access:** Désactiver (pour CloudFront)
- **Static Website Hosting:** Activé
- **Index document:** `index.html`
- **Error document:** `index.html` (ou `error.html`)

### 2. Configurer le Bucket pour Static Website Hosting

```bash
# Activer le static website hosting
aws s3 website s3://arquantix-coming-soon \
  --index-document index.html \
  --error-document index.html
```

**Bucket Policy (pour CloudFront):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontAccess",
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudfront.amazonaws.com"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::arquantix-coming-soon/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::411714852748:distribution/DISTRIBUTION_ID"
        }
      }
    }
  ]
}
```

### 3. Uploader les Fichiers

```bash
# Depuis le dossier du projet
cd services/arquantix/coming-soon

# Upload index.html
aws s3 cp index.html s3://arquantix-coming-soon/index.html \
  --content-type "text/html" \
  --cache-control "max-age=3600"

# Ou upload récursif si d'autres fichiers
aws s3 sync . s3://arquantix-coming-soon/ \
  --exclude "*.md" \
  --exclude ".gitignore" \
  --exclude "Dockerfile" \
  --exclude "README.md" \
  --exclude "AUDIT_AND_SETUP.md" \
  --exclude "DEPLOY_S3_CLOUDFRONT.md" \
  --content-type "text/html" \
  --cache-control "max-age=3600"
```

### 4. Créer la Distribution CloudFront

```bash
# Créer la distribution (nécessite un fichier de configuration)
# Voir section "CloudFront Configuration JSON" ci-dessous
```

**CloudFront Configuration:**
- **Origin Domain:** `arquantix-coming-soon.s3.me-central-1.amazonaws.com` (ou S3 website endpoint)
- **Origin Path:** (vide)
- **Viewer Protocol Policy:** Redirect HTTP to HTTPS
- **Allowed HTTP Methods:** GET, HEAD
- **Compress:** Yes
- **Default Root Object:** `index.html`
- **Error Pages:** 403 → 200 avec `/index.html`

### 5. Configurer Route53 (Domain)

```bash
# Créer un enregistrement A (Alias) pointant vers CloudFront
# Via AWS Console ou CLI
```

**Route53 Configuration:**
- **Record Type:** A (Alias)
- **Alias Target:** Distribution CloudFront
- **TTL:** (automatique pour Alias)

---

## Commandes Complètes

### Script de Déploiement Complet

```bash
#!/bin/bash
set -euo pipefail

BUCKET_NAME="arquantix-coming-soon"
REGION="me-central-1"
CLOUDFRONT_DISTRIBUTION_NAME="arquantix-coming-soon"

echo "=== 1. Créer le bucket S3 ==="
aws s3 mb s3://${BUCKET_NAME} --region ${REGION} || echo "Bucket existe déjà"

echo "=== 2. Configurer le static website hosting ==="
aws s3 website s3://${BUCKET_NAME} \
  --index-document index.html \
  --error-document index.html

echo "=== 3. Désactiver Block Public Access (pour CloudFront) ==="
aws s3api put-public-access-block \
  --bucket ${BUCKET_NAME} \
  --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

echo "=== 4. Uploader les fichiers ==="
cd services/arquantix/coming-soon
aws s3 cp index.html s3://${BUCKET_NAME}/index.html \
  --content-type "text/html" \
  --cache-control "max-age=3600"

echo "=== 5. Créer la distribution CloudFront ==="
# Note: CloudFront nécessite généralement la création via Console ou un fichier JSON
# Voir la section CloudFront Configuration JSON ci-dessous

echo "✅ Déploiement terminé"
```

---

## CloudFront Configuration JSON

Créez un fichier `cloudfront-config.json`:

```json
{
  "CallerReference": "arquantix-coming-soon-2026-01-01",
  "Comment": "Arquantix Coming Soon - S3 Static Website",
  "Enabled": true,
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "S3-arquantix-coming-soon",
        "DomainName": "arquantix-coming-soon.s3.me-central-1.amazonaws.com",
        "S3OriginConfig": {
          "OriginAccessIdentity": ""
        }
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "S3-arquantix-coming-soon",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"],
      "CachedMethods": {
        "Quantity": 2,
        "Items": ["GET", "HEAD"]
      }
    },
    "ForwardedValues": {
      "QueryString": false,
      "Cookies": {
        "Forward": "none"
      }
    },
    "MinTTL": 0,
    "DefaultTTL": 3600,
    "MaxTTL": 86400,
    "Compress": true
  },
  "DefaultRootObject": "index.html",
  "CustomErrorResponses": {
    "Quantity": 1,
    "Items": [
      {
        "ErrorCode": 403,
        "ResponsePagePath": "/index.html",
        "ResponseCode": "200",
        "ErrorCachingMinTTL": 300
      }
    ]
  },
  "PriceClass": "PriceClass_100"
}
```

Créer la distribution:
```bash
aws cloudfront create-distribution --distribution-config file://cloudfront-config.json
```

---

## Domain Configuration

### Option 1: Sous-domaine (ex: arquantix.maisonganopa.com)

Si vous utilisez le même domaine que Ganopa:
- Route53 Hosted Zone: `maisonganopa.com`
- Record: `arquantix` (A Alias → CloudFront)

### Option 2: Domaine dédié (ex: arquantix.com)

Si vous avez un domaine dédié:
1. Créer une Hosted Zone Route53 pour `arquantix.com`
2. Mettre à jour les nameservers chez le registrar
3. Créer un record A (Alias) → CloudFront

---

## Workflow GitHub Actions pour S3

Mettre à jour `.github/workflows/arquantix-push-to-ecr.yml` ou créer un nouveau workflow:

```yaml
name: Arquantix - Deploy to S3 + CloudFront

on:
  push:
    branches: [ "main", "arquantix/coming-soon" ]
    paths:
      - "services/arquantix/**"

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: me-central-1
      
      - name: Upload to S3
        run: |
          cd services/arquantix/coming-soon
          aws s3 sync . s3://arquantix-coming-soon/ \
            --exclude "*.md" \
            --exclude ".gitignore" \
            --exclude "Dockerfile" \
            --content-type "text/html" \
            --cache-control "max-age=3600"
      
      - name: Invalidate CloudFront
        run: |
          DISTRIBUTION_ID=$(aws cloudfront list-distributions \
            --query "DistributionList.Items[?Comment=='Arquantix Coming Soon'].Id" \
            --output text)
          aws cloudfront create-invalidation \
            --distribution-id ${DISTRIBUTION_ID} \
            --paths "/*"
```

---

## Avantages S3 + CloudFront vs ECS

✅ **Plus simple:** Pas de containers, pas de services ECS  
✅ **Moins cher:** S3 + CloudFront coûte moins qu'ECS Fargate  
✅ **Plus rapide:** CDN global avec cache  
✅ **Scalable:** CloudFront gère automatiquement la charge  
✅ **Maintenance:** Moins de ressources à gérer  

---

## URLs et Endpoints

### S3 Website Endpoint
- `http://arquantix-coming-soon.s3-website-me-central-1.amazonaws.com`
- (Temporaire, avant CloudFront)

### CloudFront Distribution
- `https://dXXXXXXX.cloudfront.net`
- (Après création de la distribution)

### Domain Final
- `https://arquantix.com` (ou sous-domaine choisi)
- (Après configuration Route53)

---

## Checklist de Déploiement

- [ ] Créer le bucket S3
- [ ] Configurer static website hosting
- [ ] Désactiver Block Public Access
- [ ] Uploader `index.html`
- [ ] Créer la distribution CloudFront
- [ ] Configurer Route53 (domain)
- [ ] Tester l'accès via CloudFront
- [ ] Tester l'accès via domain
- [ ] (Optionnel) Créer workflow GitHub Actions pour déploiement automatique

---

**Note:** Ce document décrit le processus manuel. Pour automatiser, créer un workflow GitHub Actions comme décrit ci-dessus.


