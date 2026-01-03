# Statut du Déploiement Arquantix - S3 + CloudFront

**Date:** 2026-01-01  
**Service:** Arquantix Coming Soon

---

## ✅ État Actuel

### S3 Bucket

- ✅ **Bucket créé:** `arquantix-coming-soon-dev`
- ✅ **Région:** `me-central-1`
- ✅ **Static Website Hosting:** Configuré
  - Index document: `index.html`
  - Error document: `index.html`
- ✅ **Block Public Access:** Désactivé
- ✅ **Bucket Policy:** Configurée (public read)
- ✅ **Fichier uploadé:** `index.html`

**URL S3 Website:**
```
http://arquantix-coming-soon-dev.s3-website-me-central-1.amazonaws.com
```

### CloudFront Distribution

- ⚠️ **Status:** Non créé (permissions CloudFront manquantes)
- ⚠️ **Action requise:** Créer la distribution via AWS Console ou ajouter les permissions CloudFront

**Permissions nécessaires:**
- `cloudfront:CreateDistribution`
- `cloudfront:ListDistributions`
- `cloudfront:GetDistribution`
- `cloudfront:UpdateDistribution`

### Route53 (Domain)

- ⚠️ **Status:** Non configuré
- ⚠️ **Action requise:** Configurer après création CloudFront

---

## 📋 Prochaines Étapes

### 1. Créer la Distribution CloudFront

**Option A: Via AWS Console (Recommandé)**

1. Ouvrir: https://console.aws.amazon.com/cloudfront/v3/home?region=me-central-1
2. Cliquer sur "Create distribution"
3. **Origin settings:**
   - **Origin domain:** `arquantix-coming-soon-dev.s3-website-me-central-1.amazonaws.com`
   - **Name:** `S3-arquantix-coming-soon-dev`
   - **Origin path:** (vide)
   - **Origin access:** Origin access control settings (recommended)
     - Créer un nouveau control setting:
       - **Control setting name:** `arquantix-coming-soon-dev-oac`
       - **Origin type:** S3
       - **Signing behavior:** Sign requests (recommended)
       - **Signing protocol:** SigV4
4. **Default cache behavior:**
   - **Viewer protocol policy:** Redirect HTTP to HTTPS
   - **Allowed HTTP methods:** GET, HEAD
   - **Cache policy:** CachingOptimized
   - **Compress objects automatically:** Yes
5. **Settings:**
   - **Price class:** Use all edge locations (ou "Use only North America and Europe" pour réduire coûts)
   - **Default root object:** `index.html`
   - **Comment:** `Arquantix Coming Soon - S3 Static Website`
6. **Custom error responses:**
   - **Error code 403:**
     - Customize error response: Yes
     - Response page path: `/index.html`
     - HTTP response code: 200
   - **Error code 404:**
     - Customize error response: Yes
     - Response page path: `/index.html`
     - HTTP response code: 200
7. Cliquer sur "Create distribution"
8. **Attendre 15-20 minutes** pour le déploiement

**Option B: Ajouter les permissions CloudFront**

Demander à un administrateur AWS d'ajouter les permissions CloudFront à l'utilisateur `cursor-admin`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudfront:CreateDistribution",
        "cloudfront:GetDistribution",
        "cloudfront:ListDistributions",
        "cloudfront:UpdateDistribution",
        "cloudfront:CreateInvalidation"
      ],
      "Resource": "*"
    }
  ]
}
```

Puis utiliser le fichier `cloudfront-config.json` pour créer la distribution via CLI.

### 2. Mettre à jour Bucket Policy pour CloudFront

Une fois CloudFront créé, mettre à jour le Bucket Policy:

1. Aller dans S3 → `arquantix-coming-soon-dev` → Permissions → Bucket policy
2. CloudFront affichera une policy à copier dans la section "Origin access control"
3. Remplacer la policy actuelle par celle fournie par CloudFront

### 3. Configurer Route53

**Option A: Sous-domaine (ex: arquantix.maisonganopa.com)**

1. Route53 → Hosted zones → `maisonganopa.com`
2. Create record:
   - **Record name:** `arquantix`
   - **Record type:** A (Alias)
   - **Alias:** Yes
   - **Route traffic to:** Alias to CloudFront distribution
   - **Choose distribution:** Sélectionner la distribution CloudFront
   - Create records

**Option B: Domaine dédié (ex: arquantix.com)**

1. Créer une Hosted Zone pour `arquantix.com`
2. Mettre à jour les nameservers chez le registrar
3. Créer un record A (Alias) → CloudFront

### 4. Mettre à jour CloudFront avec Domain

1. CloudFront → Distribution → General → Edit
2. **Alternate domain names (CNAMEs):** Ajouter le domaine (ex: `arquantix.maisonganopa.com`)
3. **Custom SSL certificate:** Sélectionner un certificat ACM (créer si nécessaire)
4. Save changes

---

## 🔍 Vérification

### Test S3 Website (temporaire)

```bash
curl http://arquantix-coming-soon-dev.s3-website-me-central-1.amazonaws.com
```

**Attendu:** HTML de la page "Coming Soon"

### Test CloudFront (après création)

```bash
curl https://dXXXXXXX.cloudfront.net
```

(Remplacez `dXXXXXXX` par l'ID réel de la distribution)

### Test Domain (après Route53)

```bash
curl https://arquantix.maisonganopa.com
```

---

## 📊 Checklist

- [x] Créer le bucket S3
- [x] Configurer static website hosting
- [x] Désactiver Block Public Access
- [x] Ajouter Bucket Policy (public read)
- [x] Uploader `index.html`
- [ ] Créer la distribution CloudFront
- [ ] Mettre à jour Bucket Policy avec CloudFront OAC
- [ ] Configurer Route53 (domain)
- [ ] Mettre à jour CloudFront avec CNAME et certificat SSL
- [ ] Tester l'accès via CloudFront URL
- [ ] Tester l'accès via domain

---

## 🌐 URLs

### S3 Website Endpoint
```
http://arquantix-coming-soon-dev.s3-website-me-central-1.amazonaws.com
```

### CloudFront Distribution
```
https://dXXXXXXX.cloudfront.net
```
(À remplacer par l'ID réel après création)

### Domain Final
```
https://arquantix.maisonganopa.com
```
(À configurer après Route53)

---

**Dernière mise à jour:** 2026-01-01


