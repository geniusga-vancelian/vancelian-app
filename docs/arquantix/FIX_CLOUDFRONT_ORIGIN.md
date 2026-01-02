# Fix CloudFront Origin - Arquantix

**Date:** 2026-01-03  
**Problème:** CloudFront pointe vers S3 au lieu de ECS

---

## 🚨 Problème

Le site https://arquantix.com affiche l'ancienne version statique depuis S3 au lieu de la nouvelle application Next.js depuis ECS.

**CloudFront Origin actuel:** `arquantix-coming-soon-dev.s3.me-central-1.amazonaws.com`

---

## ✅ Solution

### Étape 1: Vérifier Service ECS

1. Aller sur: https://console.aws.amazon.com/ecs/v2/clusters
2. Sélectionner le cluster `arquantix-cluster`
3. Vérifier si le service `arquantix-coming-soon` existe et est running

**Si le service n'existe pas:**
- Voir `docs/arquantix/DEPLOYMENT_CHECKLIST.md` pour créer le service ECS

**Si le service existe:**
- Noter le DNS de l'ALB (si ALB configuré)
- Ou noter l'IP publique du service (si pas d'ALB)

### Étape 2: Obtenir Endpoint ECS

**Option A: Si ALB existe**

1. Aller sur: https://console.aws.amazon.com/ec2/v2/home#LoadBalancers:
2. Trouver l'ALB associé à `arquantix-coming-soon`
3. Copier le DNS name (ex: `arquantix-alb-1234567890.me-central-1.elb.amazonaws.com`)

**Option B: Si pas d'ALB (IP publique)**

1. Dans ECS → Service → Tasks
2. Cliquer sur une task running
3. Noter l'IP publique (Public IP)

### Étape 3: Mettre à jour CloudFront Origin

1. Aller sur: https://console.aws.amazon.com/cloudfront/v3/home#/distributions/EPJ3WQCO04UWW
2. Cliquer sur **Edit**
3. Aller dans l'onglet **Origins**
4. Sélectionner l'origine `S3-arquantix-coming-soon-dev`
5. Cliquer sur **Edit**
6. Modifier:
   - **Origin domain:** 
     - Si ALB: `arquantix-alb-1234567890.me-central-1.elb.amazonaws.com`
     - Si IP publique: `x.x.x.x` (mais préférer ALB)
   - **Origin protocol:** `HTTPS` (si ALB) ou `HTTP` (si IP)
   - **Origin path:** `/` (vide)
   - **HTTP port:** `80` (si HTTP) ou `443` (si HTTPS)
   - **HTTPS port:** `443` (si HTTPS)
7. **Save changes**

### Étape 4: Invalidation CloudFront

1. Dans la distribution CloudFront, aller dans l'onglet **Invalidations**
2. Cliquer sur **Create invalidation**
3. **Object paths:** `/*`
4. **Create invalidation**
5. Attendre 2-5 minutes pour la propagation

### Étape 5: Vérification

```bash
# Tester les URLs
curl -I https://arquantix.com
curl -I https://www.arquantix.com

# Vérifier le contenu
curl https://arquantix.com | grep -i "FRACTIONAL REAL ESTATE"
```

**Attendu:** Le site devrait afficher la nouvelle page Next.js avec:
- Navbar (logo + bouton Coming soon)
- Hero (carousel 2 images + titre centré)
- Footer (logo + copyright)

---

## 🔗 Liens Directs

- **CloudFront Distribution:** https://console.aws.amazon.com/cloudfront/v3/home#/distributions/EPJ3WQCO04UWW/edit/origins
- **ECS Clusters:** https://console.aws.amazon.com/ecs/v2/clusters
- **ECR Repository:** https://console.aws.amazon.com/ecr/repositories/private/411714852748/arquantix-coming-soon
- **ALB:** https://console.aws.amazon.com/ec2/v2/home#LoadBalancers:

---

## 📋 Checklist

- [ ] Vérifier service ECS existe et running
- [ ] Obtenir endpoint ECS (ALB DNS ou IP publique)
- [ ] Mettre à jour CloudFront origin
- [ ] Invalidation CloudFront (`/*`)
- [ ] Tester https://arquantix.com
- [ ] Tester https://www.arquantix.com
- [ ] Vérifier contenu (nouvelle page Next.js)

---

**Status:** En attente de mise à jour CloudFront origin.

