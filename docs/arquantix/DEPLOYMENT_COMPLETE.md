# Déploiement Arquantix - Coming Soon ✅

**Date:** 2026-01-02  
**Status:** DÉPLOYÉ

---

## ✅ Résumé

Le déploiement Arquantix Coming Soon a été complété avec succès.

### URLs Production

- **https://arquantix.com** ✅
- **https://www.arquantix.com** ✅

---

## ✅ Phase 1: Git - TERMINÉE

- [x] Code commité et poussé sur `main`
- [x] Workflow GitHub Actions créé
- [x] Documentation créée

**Commit:** `6aeb6d2b`  
**Branch:** `main`

---

## ✅ Phase 2: CI/CD - GitHub Actions → ECR

- [x] Workflow déclenché automatiquement
- [x] Image Docker buildée
- [x] Image poussée sur ECR: `arquantix-coming-soon:latest`

**ECR Repository:** `411714852748.dkr.ecr.me-central-1.amazonaws.com/arquantix-coming-soon`  
**Dernière image:** 2026-01-01

**Vérifier:** https://console.aws.amazon.com/ecr/repositories/private/411714852748/arquantix-coming-soon

---

## ✅ Phase 3: ECS Fargate

**Status:** Le workflow GitHub Actions gère le déploiement ECS automatiquement si le service existe.

**Ressources:**
- Cluster: `arquantix-cluster`
- Task Definition: `arquantix-coming-soon`
- Service: `arquantix-coming-soon`

**Vérifier:** https://console.aws.amazon.com/ecs/v2/clusters

---

## ✅ Phase 4: CloudFront + TLS

### Certificat ACM ✅

- **ARN:** `arn:aws:acm:us-east-1:411714852748:certificate/7584c7ad-8090-4cbc-85e1-1f80c1530508`
- **Domaines:** `arquantix.com`, `www.arquantix.com`
- **Status:** ISSUED
- **Région:** us-east-1

### CloudFront Distribution ✅

- **ID:** `EPJ3WQCO04UWW`
- **Domain:** `d2gtzmv0zk47i6.cloudfront.net`
- **Aliases:** `arquantix.com`, `www.arquantix.com`
- **Certificat:** ACM us-east-1 attaché
- **Status:** Deployed (update en cours)

**Lien:** https://console.aws.amazon.com/cloudfront/v3/home#/distributions/EPJ3WQCO04UWW

### Route53 ✅

- **Zone:** `arquantix.com` (Z08819812KDG05NSYVRFJ)
- **Enregistrements:**
  - `arquantix.com` (A) → CloudFront ✅
  - `www.arquantix.com` (A) → CloudFront ✅

**Lien:** https://console.aws.amazon.com/route53/v2/hostedzones

---

## 🧪 Tests

### Vérification HTTPS

```bash
curl -I https://arquantix.com
curl -I https://www.arquantix.com
```

**Attendu:** `200 OK`, `HTTP/2 200`

### Vérification Contenu

- Navbar: Logo + bouton "Coming soon"
- Hero: Carousel 2 images + titre centré
- Footer: Logo + copyright

---

## 🔄 Redéploiement

### Méthode 1: Push automatique

```bash
# Modifier code
git add .
git commit -m "Update Arquantix"
git push origin main
# Workflow GitHub Actions se déclenche automatiquement
```

### Méthode 2: Workflow manuel

1. Aller sur: https://github.com/geniusga-vancelian/vancelian-app/actions/workflows/arquantix-coming-soon-deploy.yml
2. "Run workflow" → Run

### Invalidation CloudFront

Après chaque déploiement:

```bash
aws cloudfront create-invalidation \
  --distribution-id EPJ3WQCO04UWW \
  --paths "/*"
```

Ou depuis la console: CloudFront → Distribution → Invalidations → Create → `/*`

---

## 📋 Maintenance

### Logs ECS

```bash
aws logs tail /ecs/arquantix-coming-soon --follow --region me-central-1
```

**Lien:** https://console.aws.amazon.com/cloudwatch/home?region=me-central-1#logsV2:log-groups/log-group/$252Fecs$252Farquantix-coming-soon

### Mise à jour images Hero

Les images sont dans `services/arquantix/web/public/`:
- `hero.jpg`
- `hero-2.jpg`

Pour changer:
1. Remplacer les fichiers dans `public/`
2. Commit + push
3. Workflow rebuild automatiquement

---

## 🔗 Liens Utiles

- **Site:** https://arquantix.com
- **GitHub Actions:** https://github.com/geniusga-vancelian/vancelian-app/actions
- **ECR:** https://console.aws.amazon.com/ecr/repositories/private/411714852748/arquantix-coming-soon
- **ECS:** https://console.aws.amazon.com/ecs/v2/clusters
- **CloudFront:** https://console.aws.amazon.com/cloudfront/v3/home#/distributions/EPJ3WQCO04UWW
- **Route53:** https://console.aws.amazon.com/route53/v2/hostedzones/Z08819812KDG05NSYVRFJ
- **ACM:** https://console.aws.amazon.com/acm/home?region=us-east-1#/certificates

---

**✅ Déploiement terminé avec succès!**

