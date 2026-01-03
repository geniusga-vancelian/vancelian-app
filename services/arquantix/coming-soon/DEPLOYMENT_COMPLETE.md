# ✅ Déploiement Arquantix - S3 + CloudFront - COMPLET

**Date:** 2026-01-01  
**Service:** Arquantix Coming Soon  
**Status:** ✅ Infrastructure créée, en attente de déploiement CloudFront

---

## ✅ Infrastructure Créée

### S3 Bucket

- ✅ **Bucket:** `arquantix-coming-soon-dev`
- ✅ **Région:** `me-central-1`
- ✅ **Static Website Hosting:** Configuré
- ✅ **Bucket Policy:** Configurée pour CloudFront OAC
- ✅ **Fichier:** `index.html` uploadé (2.4 KB)

**URL S3 Website (temporaire):**
```
http://arquantix-coming-soon-dev.s3-website-me-central-1.amazonaws.com
```

### CloudFront Distribution

- ✅ **Distribution ID:** `EPJ3WQCO04UWW`
- ✅ **Domain Name:** `d2gtzmv0zk47i6.cloudfront.net`
- ✅ **Status:** `InProgress` (déploiement en cours, 15-20 minutes)
- ✅ **Origin Access Control (OAC):** `E2TW7B89RBY1WG`
- ✅ **Comment:** "Arquantix Coming Soon - S3 Static Website"

**URL CloudFront:**
```
https://d2gtzmv0zk47i6.cloudfront.net
```

**Console CloudFront:**
https://console.aws.amazon.com/cloudfront/v3/home#/distributions/EPJ3WQCO04UWW

---

## ⏳ En Attente

### CloudFront Déploiement

La distribution CloudFront est en cours de déploiement. Cela prend généralement **15-20 minutes**.

**Vérifier le statut:**
```bash
aws cloudfront get-distribution --id EPJ3WQCO04UWW --query 'Distribution.Status' --output text
```

**Quand le statut sera `Deployed`, la distribution sera accessible.**

### Route53 (Domain)

- ⚠️ **Status:** Non configuré
- ⚠️ **Action requise:** Configurer après déploiement CloudFront

**Options:**
1. **Sous-domaine:** `arquantix.maisonganopa.com`
2. **Domaine dédié:** `arquantix.com` (si vous avez le domaine)

---

## 🔍 Test de l'Infrastructure

### Test S3 Website (immédiat)

```bash
curl http://arquantix-coming-soon-dev.s3-website-me-central-1.amazonaws.com
```

**Attendu:** HTML de la page "Coming Soon"

### Test CloudFront (après déploiement, ~15-20 min)

```bash
curl https://d2gtzmv0zk47i6.cloudfront.net
```

**Attendu:** HTML de la page "Coming Soon" (via CDN)

### Test Domain (après Route53)

```bash
curl https://arquantix.maisonganopa.com
```

(ou votre domaine choisi)

---

## 📋 Configuration Route53

### Option A: Sous-domaine (arquantix.maisonganopa.com)

1. **Ouvrir Route53 Console:**
   https://console.aws.amazon.com/route53/v2/hostedzones

2. **Trouver la Hosted Zone:** `maisonganopa.com`

3. **Créer un enregistrement:**
   - Cliquer sur "Create record"
   - **Record name:** `arquantix`
   - **Record type:** A
   - **Alias:** Yes
   - **Route traffic to:** Alias to CloudFront distribution
   - **Choose distribution:** `EPJ3WQCO04UWW` (ou sélectionner dans la liste)
   - **Evaluate target health:** No
   - Cliquer sur "Create records"

**Résultat:** `arquantix.maisonganopa.com` → CloudFront → S3

### Option B: Domaine dédié (arquantix.com)

1. **Créer une Hosted Zone:**
   - Route53 → Hosted zones → Create hosted zone
   - **Domain name:** `arquantix.com`
   - **Type:** Public hosted zone
   - Cliquer sur "Create hosted zone"

2. **Mettre à jour les nameservers:**
   - Route53 fournira 4 nameservers
   - Aller chez votre registrar de domaine
   - Mettre à jour les nameservers

3. **Créer un enregistrement A (Alias):**
   - Cliquer sur "Create record"
   - **Record name:** (vide pour racine, ou `www` pour www.arquantix.com)
   - **Record type:** A
   - **Alias:** Yes
   - **Route traffic to:** Alias to CloudFront distribution
   - **Choose distribution:** `EPJ3WQCO04UWW`
   - Cliquer sur "Create records"

---

## 🔐 Mettre à jour CloudFront avec Domain

Une fois Route53 configuré:

1. **Ouvrir la distribution CloudFront:**
   https://console.aws.amazon.com/cloudfront/v3/home#/distributions/EPJ3WQCO04UWW

2. **Onglet "General"** → **"Edit"**

3. **Alternate domain names (CNAMEs):**
   - Ajouter: `arquantix.maisonganopa.com` (ou `arquantix.com`)

4. **Custom SSL certificate:**
   - Sélectionner un certificat ACM (créer si nécessaire pour le domaine)
   - Si vous utilisez `arquantix.maisonganopa.com`, vous pouvez utiliser un certificat wildcard `*.maisonganopa.com` si disponible

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
  CLOUDFRONT_DISTRIBUTION_ID: "EPJ3WQCO04UWW"

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

**Note:** Remplacer `CLOUDFRONT_DISTRIBUTION_ID` par `EPJ3WQCO04UWW` (déjà fait ci-dessus).

---

## ✅ Checklist Finale

- [x] Créer le bucket S3
- [x] Configurer static website hosting
- [x] Désactiver Block Public Access
- [x] Ajouter Bucket Policy (CloudFront OAC)
- [x] Uploader `index.html`
- [x] Créer Origin Access Control (OAC)
- [x] Créer la distribution CloudFront
- [x] Mettre à jour Bucket Policy avec CloudFront
- [ ] Attendre le déploiement CloudFront (15-20 min)
- [ ] Tester l'accès via CloudFront URL
- [ ] Configurer Route53 (domain)
- [ ] Mettre à jour CloudFront avec CNAME et certificat SSL
- [ ] Tester l'accès via domain
- [ ] (Optionnel) Créer workflow GitHub Actions

---

## 🌐 URLs Finales

### S3 Website Endpoint (temporaire)
```
http://arquantix-coming-soon-dev.s3-website-me-central-1.amazonaws.com
```

### CloudFront Distribution
```
https://d2gtzmv0zk47i6.cloudfront.net
```
**Status:** En cours de déploiement (15-20 minutes)

### Domain Final (après Route53)
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

### Le site ne s'affiche pas via CloudFront

1. **Vérifier le statut CloudFront:**
   ```bash
   aws cloudfront get-distribution --id EPJ3WQCO04UWW --query 'Distribution.Status' --output text
   ```
   Doit être `Deployed` (pas `InProgress`)

2. **Vérifier le bucket policy:** Doit autoriser CloudFront OAC
3. **Vérifier que `index.html` est dans le bucket**

### Erreur 403 Forbidden

- Vérifier que le Bucket Policy autorise CloudFront
- Vérifier que l'OAC est correctement configuré dans CloudFront

### Erreur 404 Not Found

- Vérifier que `index.html` est uploadé dans le bucket
- Vérifier "Default root object" dans CloudFront (`index.html`)
- Vérifier Custom Error Responses (403/404 → 200 avec `/index.html`)

---

## 📝 Informations Techniques

### Origin Access Control (OAC)
- **ID:** `E2TW7B89RBY1WG`
- **Name:** `arquantix-coming-soon-dev-oac`
- **Type:** S3
- **Signing Protocol:** SigV4

### CloudFront Distribution
- **ID:** `EPJ3WQCO04UWW`
- **Domain:** `d2gtzmv0zk47i6.cloudfront.net`
- **Origin:** `arquantix-coming-soon-dev.s3.me-central-1.amazonaws.com`
- **Price Class:** PriceClass_100 (US, Canada, Europe)

---

**Dernière mise à jour:** 2026-01-01  
**Status:** ✅ Infrastructure créée, CloudFront en déploiement


