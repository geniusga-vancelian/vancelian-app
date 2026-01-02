# Action Requise - Mise à jour CloudFront Origin

**Date:** 2026-01-03  
**Status:** Invalidation CloudFront créée, origine à mettre à jour manuellement

---

## ✅ Ce qui a été fait

1. **Invalidation CloudFront créée**
   - ID: `I4TII1BSFQMXH0EOSNGR15T3T5`
   - Status: `InProgress`
   - Paths: `/*`

2. **Infrastructure ECS**
   - Cluster: `arquantix-cluster` (existe)
   - Task Definition: `arquantix-coming-soon` (créée/vérifiée)
   - Image ECR: `arquantix-coming-soon:latest` (179 MB, 2026-01-03)

---

## ⚠️ Action Manuelle Requise

### Étape 1: Vérifier/Créer Service ECS

**Console:** https://console.aws.amazon.com/ecs/v2/clusters/arquantix-cluster/services

1. Aller sur la console ECS
2. Sélectionner le cluster `arquantix-cluster`
3. Vérifier si le service `arquantix-coming-soon` existe

**Si le service n'existe pas:**

1. Cliquer sur **Create Service**
2. **Task Definition:** `arquantix-coming-soon`
3. **Service name:** `arquantix-coming-soon`
4. **Desired tasks:** `1`
5. **Launch type:** `Fargate`
6. **VPC:** Sélectionner le VPC par défaut
7. **Subnets:** Sélectionner 2 subnets publics
8. **Security groups:** Sélectionner le security group par défaut
9. **Auto-assign public IP:** `ENABLED`
10. **Load balancer:** Optionnel (peut être ajouté plus tard)
11. **Create service**

**Si le service existe:**

- Vérifier qu'il est `RUNNING` avec `1/1` tasks
- Attendre 2-3 minutes si la task démarre

### Étape 2: Obtenir l'Endpoint ECS

**Option A: Si ALB configuré**

1. Aller sur: https://console.aws.amazon.com/ec2/v2/home#LoadBalancers:
2. Trouver l'ALB associé au service ECS
3. Copier le **DNS name** (ex: `arquantix-alb-1234567890.me-central-1.elb.amazonaws.com`)

**Option B: Si pas d'ALB (IP publique)**

1. Dans ECS → Service → Tasks
2. Cliquer sur la task running
3. Dans **Network**, noter l'**Public IP**
4. Endpoint sera: `http://<PUBLIC_IP>:3000`

### Étape 3: Mettre à jour CloudFront Origin

**Console:** https://console.aws.amazon.com/cloudfront/v3/home#/distributions/EPJ3WQCO04UWW/edit/origins

1. Aller sur la distribution CloudFront `EPJ3WQCO04UWW`
2. Cliquer sur **Edit**
3. Onglet **Origins**
4. Sélectionner l'origine `S3-arquantix-coming-soon-dev`
5. Cliquer sur **Edit**

**Modifications:**

- **Origin domain:** 
  - Si ALB: `arquantix-alb-1234567890.me-central-1.elb.amazonaws.com`
  - Si IP: `x.x.x.x` (mais préférer ALB)
- **Origin protocol:** 
  - Si ALB: `HTTPS` (ou `HTTP` si pas de certificat)
  - Si IP: `HTTP`
- **Origin path:** `/` (vide)
- **HTTP port:** `80` (si HTTP) ou `443` (si HTTPS)
- **HTTPS port:** `443` (si HTTPS)

6. **Save changes**
7. Attendre 5-15 minutes pour le déploiement

### Étape 4: Vérification

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

- **ECS Service:** https://console.aws.amazon.com/ecs/v2/clusters/arquantix-cluster/services
- **CloudFront Edit Origins:** https://console.aws.amazon.com/cloudfront/v3/home#/distributions/EPJ3WQCO04UWW/edit/origins
- **Invalidation Status:** https://console.aws.amazon.com/cloudfront/v3/home#/distributions/EPJ3WQCO04UWW/invalidations

---

## 📋 Checklist

- [ ] Vérifier/créer service ECS `arquantix-coming-soon`
- [ ] Service running avec 1/1 tasks
- [ ] Obtenir endpoint ECS (ALB DNS ou IP publique)
- [ ] Mettre à jour CloudFront origin
- [ ] Attendre déploiement CloudFront (5-15 min)
- [ ] Tester https://arquantix.com
- [ ] Tester https://www.arquantix.com
- [ ] Vérifier contenu (nouvelle page Next.js)

---

**Note:** L'invalidation CloudFront a déjà été créée. Une fois l'origine mise à jour, le cache sera automatiquement invalidé.

