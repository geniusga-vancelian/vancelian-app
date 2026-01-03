# Guide de Configuration S3 + CloudFront pour Arquantix

**Date:** 2026-01-01  
**Service:** Arquantix Coming Soon  
**Méthode:** S3 Static Website Hosting + CloudFront CDN

---

## ⚠️ Permissions Requises

Les permissions suivantes sont nécessaires:
- `s3:CreateBucket`
- `s3:PutBucketWebsite`
- `s3:PutBucketPolicy`
- `s3:PutObject`
- `cloudfront:CreateDistribution`
- `cloudfront:GetDistribution`
- `cloudfront:UpdateDistribution`

Si vous n'avez pas ces permissions avec l'utilisateur `cursor-admin`, utilisez:
- AWS Console avec un utilisateur ayant plus de permissions
- Ou demandez à un administrateur AWS d'ajouter ces permissions

---

## 📋 Étapes de Configuration

### Étape 1: Créer le Bucket S3

#### Via AWS Console (Recommandé)

1. **Ouvrir S3 Console:**
   https://console.aws.amazon.com/s3/buckets?region=me-central-1

2. **Créer un bucket:**
   - Cliquer sur "Create bucket"
   - **Bucket name:** `arquantix-coming-soon-dev` (doit être unique globalement)
   - **AWS Region:** `Middle East (UAE) - me-central-1`
   - **Object Ownership:** ACLs disabled (Bucket owner enforced)
   - **Block Public Access settings:** 
     - ✅ Décocher "Block all public access" (nécessaire pour CloudFront)
     - Cocher "I acknowledge that the current settings might result in this bucket and the objects within becoming public"
   - **Bucket Versioning:** Disable
   - **Default encryption:** Enable (SSE-S3)
   - Cliquer sur "Create bucket"

#### Via AWS CLI (avec permissions)

```bash
# Créer le bucket
aws s3 mb s3://arquantix-coming-soon-dev --region me-central-1

# Configurer le static website hosting
aws s3 website s3://arquantix-coming-soon-dev \
  --index-document index.html \
  --error-document index.html

# Désactiver Block Public Access
aws s3api put-public-access-block \
  --bucket arquantix-coming-soon-dev \
  --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"
```

---

### Étape 2: Configurer le Bucket Policy

#### Via AWS Console

1. **Ouvrir le bucket:** `arquantix-coming-soon-dev`
2. **Onglet "Permissions"** → **"Bucket policy"**
3. **Ajouter cette policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::arquantix-coming-soon-dev/*"
    }
  ]
}
```

4. **Cliquer sur "Save changes"**

#### Via AWS CLI

```bash
aws s3api put-bucket-policy \
  --bucket arquantix-coming-soon-dev \
  --policy file://bucket-policy.json \
  --region me-central-1
```

---

### Étape 3: Uploader index.html

#### Via AWS Console

1. **Ouvrir le bucket:** `arquantix-coming-soon-dev`
2. **Onglet "Objects"** → **"Upload"**
3. **Ajouter des fichiers:**
   - Sélectionner `services/arquantix/coming-soon/index.html`
4. **Permissions:**
   - Décocher "Block all public access"
5. **Properties:**
   - **Content-Type:** `text/html`
   - **Cache-Control:** `max-age=3600`
6. **Cliquer sur "Upload"**

#### Via AWS CLI

```bash
cd services/arquantix/coming-soon

aws s3 cp index.html s3://arquantix-coming-soon-dev/index.html \
  --content-type "text/html" \
  --cache-control "max-age=3600" \
  --region me-central-1 \
  --acl public-read
```

**Vérification:**
```bash
aws s3 ls s3://arquantix-coming-soon-dev/ --region me-central-1
```

---

### Étape 4: Créer la Distribution CloudFront

#### Via AWS Console (Recommandé)

1. **Ouvrir CloudFront Console:**
   https://console.aws.amazon.com/cloudfront/v3/home?region=me-central-1

2. **Créer une distribution:**
   - Cliquer sur "Create distribution"

3. **Origin settings:**
   - **Origin domain:** Sélectionner `arquantix-coming-soon-dev.s3.me-central-1.amazonaws.com`
   - **Name:** `S3-arquantix-coming-soon-dev` (auto-généré)
   - **Origin path:** (laisser vide)
   - **Origin access:** Origin access control settings (recommended)
     - Cliquer sur "Create control setting"
       - **Control setting name:** `arquantix-coming-soon-dev-oac`
       - **Origin type:** S3
       - **Signing behavior:** Sign requests (recommended)
       - **Signing protocol:** SigV4
       - Cliquer sur "Create"
   - **Origin access control:** Sélectionner `arquantix-coming-soon-dev-oac` (créé ci-dessus)

4. **Default cache behavior:**
   - **Viewer protocol policy:** Redirect HTTP to HTTPS
   - **Allowed HTTP methods:** GET, HEAD
   - **Cache policy:** CachingOptimized (ou CachingDisabled pour dev)
   - **Origin request policy:** None (ou CORS-S3Origin si CORS nécessaire)
   - **Response headers policy:** None
   - **Compress objects automatically:** Yes

5. **Settings:**
   - **Price class:** Use all edge locations (best performance)
     - Ou "Use only North America and Europe" pour réduire les coûts
   - **Alternate domain names (CNAMEs):** (laisser vide pour l'instant, à configurer après Route53)
   - **Custom SSL certificate:** (optionnel, à configurer après Route53 si domaine personnalisé)
   - **Default root object:** `index.html`
   - **Comment:** `Arquantix Coming Soon - S3 Static Website`

6. **Custom error responses:**
   - **Error code:** 403
     - **Customize error response:** Yes
     - **Response page path:** `/index.html`
     - **HTTP response code:** 200
     - **Error caching minimum TTL:** 300
   - **Error code:** 404
     - **Customize error response:** Yes
     - **Response page path:** `/index.html`
     - **HTTP response code:** 200
     - **Error caching minimum TTL:** 300

7. **Cliquer sur "Create distribution"**

8. **Attendre que la distribution soit déployée** (peut prendre 15-20 minutes)

9. **Mettre à jour le Bucket Policy pour CloudFront:**
   - Une fois la distribution créée, CloudFront affichera une policy à copier
   - Aller dans S3 → Bucket → Permissions → Bucket policy
   - Remplacer la policy précédente par celle fournie par CloudFront

#### Via AWS CLI (avec permissions)

Le fichier `cloudfront-config.json` a été créé. Cependant, CloudFront nécessite généralement la création via Console car la configuration est complexe.

---

### Étape 5: Configurer Route53 (Domain)

#### Option A: Sous-domaine (ex: arquantix.maisonganopa.com)

1. **Ouvrir Route53 Console:**
   https://console.aws.amazon.com/route53/v2/hostedzones

2. **Trouver la Hosted Zone:** `maisonganopa.com`

3. **Créer un enregistrement:**
   - Cliquer sur "Create record"
   - **Record name:** `arquantix`
   - **Record type:** A
   - **Alias:** Yes
   - **Route traffic to:** Alias to CloudFront distribution
   - **Choose distribution:** Sélectionner la distribution CloudFront créée
   - **Evaluate target health:** No
   - Cliquer sur "Create records"

**Résultat:** `arquantix.maisonganopa.com` → CloudFront → S3

#### Option B: Domaine dédié (ex: arquantix.com)

1. **Créer une Hosted Zone:**
   - Route53 → Hosted zones → Create hosted zone
   - **Domain name:** `arquantix.com`
   - **Type:** Public hosted zone
   - Cliquer sur "Create hosted zone"

2. **Mettre à jour les nameservers:**
   - Route53 fournira 4 nameservers
   - Aller chez votre registrar de domaine
   - Mettre à jour les nameservers avec ceux fournis par Route53

3. **Créer un enregistrement A (Alias):**
   - Cliquer sur "Create record"
   - **Record name:** (laisser vide pour racine, ou `www` pour www.arquantix.com)
   - **Record type:** A
   - **Alias:** Yes
   - **Route traffic to:** Alias to CloudFront distribution
   - **Choose distribution:** Sélectionner la distribution CloudFront
   - Cliquer sur "Create records"

---

### Étape 6: Mettre à jour CloudFront avec le Domain

Une fois Route53 configuré:

1. **Ouvrir la distribution CloudFront**
2. **Onglet "General"** → **"Edit"**
3. **Alternate domain names (CNAMEs):**
   - Ajouter: `arquantix.maisonganopa.com` (ou `arquantix.com`)
4. **Custom SSL certificate:**
   - Sélectionner un certificat ACM (créer un certificat si nécessaire pour le domaine)
5. **Cliquer sur "Save changes"**
6. **Attendre la mise à jour** (5-10 minutes)

---

## 🚀 Déploiement Automatique via GitHub Actions

Créer un workflow `.github/workflows/arquantix-deploy-s3.yml`:

```yaml
name: Arquantix - Deploy to S3 + CloudFront

on:
  push:
    branches: [ "main", "arquantix/coming-soon" ]
    paths:
      - "services/arquantix/coming-soon/index.html"
      - ".github/workflows/arquantix-deploy-s3.yml"
  workflow_dispatch:

permissions:
  contents: read
  id-token: write

env:
  AWS_REGION: me-central-1
  S3_BUCKET: arquantix-coming-soon-dev
  CLOUDFRONT_DISTRIBUTION_ID: "EXXXXXXXXXXXXX" # À remplacer par l'ID réel

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::411714852748:role/GitHubDeployRole
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Upload to S3
        run: |
          cd services/arquantix/coming-soon
          aws s3 cp index.html s3://${{ env.S3_BUCKET }}/index.html \
            --content-type "text/html" \
            --cache-control "max-age=3600" \
            --region ${{ env.AWS_REGION }}
      
      - name: Invalidate CloudFront
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ env.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/*" \
            --region ${{ env.AWS_REGION }}
```

**Note:** Remplacer `CLOUDFRONT_DISTRIBUTION_ID` par l'ID réel de la distribution CloudFront.

---

## ✅ Checklist de Déploiement

- [ ] Créer le bucket S3 (`arquantix-coming-soon-dev`)
- [ ] Configurer static website hosting
- [ ] Désactiver Block Public Access
- [ ] Ajouter Bucket Policy (public read)
- [ ] Uploader `index.html`
- [ ] Créer la distribution CloudFront
- [ ] Mettre à jour Bucket Policy avec CloudFront OAC policy
- [ ] Configurer Route53 (domain)
- [ ] Mettre à jour CloudFront avec CNAME et certificat SSL
- [ ] Tester l'accès via CloudFront URL
- [ ] Tester l'accès via domain
- [ ] (Optionnel) Créer workflow GitHub Actions

---

## 🔍 Vérification

### Tester via S3 Website Endpoint (temporaire)

```
http://arquantix-coming-soon-dev.s3-website-me-central-1.amazonaws.com
```

### Tester via CloudFront Distribution

```
https://dXXXXXXX.cloudfront.net
```
(Remplacez `dXXXXXXX` par l'ID réel de votre distribution)

### Tester via Domain

```
https://arquantix.maisonganopa.com
```
(ou votre domaine choisi)

---

## 📊 Coûts Estimés (mensuel)

- **S3 Storage:** ~$0.023/GB/mois (négligeable pour une page HTML)
- **S3 Requests:** ~$0.005/1000 requests (GET)
- **CloudFront Data Transfer:** ~$0.085/GB (premiers 10 TB)
- **Route53:** ~$0.50/hosted zone/mois
- **Total estimé:** < $5/mois pour un trafic faible

---

## 🆘 Dépannage

### Le site ne s'affiche pas

1. **Vérifier le bucket policy:** Doit autoriser `s3:GetObject` pour `*` (ou CloudFront OAC)
2. **Vérifier CloudFront status:** Doit être "Deployed"
3. **Vérifier Route53:** L'enregistrement doit pointer vers CloudFront
4. **Vérifier le certificat SSL:** Doit être validé et associé à CloudFront

### Erreur 403 Forbidden

- Vérifier que le Bucket Policy autorise l'accès
- Vérifier que Block Public Access est désactivé
- Vérifier que CloudFront OAC est configuré correctement

### Erreur 404 Not Found

- Vérifier que `index.html` est uploadé dans le bucket
- Vérifier "Default root object" dans CloudFront (`index.html`)
- Vérifier Custom Error Responses (403/404 → 200 avec `/index.html`)

---

**Dernière mise à jour:** 2026-01-01


