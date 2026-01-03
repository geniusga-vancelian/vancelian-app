# Diagnostic Erreurs 502/504 - Arquantix

**Date:** 2026-01-03  
**Problème:** Erreurs 502 Bad Gateway et 504 Gateway Timeout sur arquantix.com

---

## 🔍 Symptômes

- **Target Group:** UNHEALTHY (FailedHealthChecks)
- **ALB:** 502 Bad Gateway
- **Service ECS:** RUNNING mais ne répond pas
- **Ressources affectées:**
  - `/logo-arquantix.svg` → 502
  - `/hero.jpg` → 502
  - `/hero-2.jpg` → 502
  - CSS/JS assets → 502/504

---

## 🔎 Causes Identifiées

### 1. Health Check Échoue

Le target group health check échoue sur le path `/` :
- **Status:** UNHEALTHY
- **Reason:** Target.FailedHealthChecks
- **Path:** `/` (changé récemment de `/fr`)

### 2. Serveur Next.js Standalone

Le serveur démarre correctement (logs: "Ready in 310ms") mais :
- Le health check sur `/` échoue
- La redirection `/` → `/fr` pourrait ne pas fonctionner correctement en standalone
- Le timeout du health check pourrait être trop court

### 3. Anciens Chemins Utilisés

Le navigateur essaie toujours d'accéder aux anciens chemins :
- `/logo-arquantix.svg` (au lieu de `/media/logo/arquantix.svg`)
- `/hero.jpg` (au lieu de `/media/hero/slide-1.jpg`)
- `/hero-2.jpg` (au lieu de `/media/hero/slide-2.jpg`)

**Note:** Cela indique que le cache CloudFront ou le navigateur utilise encore l'ancienne version du HTML.

---

## ✅ Solutions Appliquées

### 1. Endpoint `/health` Dédié

Création d'un endpoint dédié pour les health checks :
```typescript
// src/app/health/route.ts
export async function GET() {
  return NextResponse.json(
    { status: 'ok', service: 'arquantix-coming-soon' },
    { status: 200 }
  )
}
```

### 2. Health Check Path Mis à Jour

Le target group health check a été mis à jour :
- **Ancien:** `/`
- **Nouveau:** `/health`

### 3. Invalidation CloudFront

Une invalidation CloudFront sera nécessaire après le déploiement pour :
- Vider le cache de l'ancien HTML
- Forcer le navigateur à charger la nouvelle version avec les bons chemins

---

## 📋 Actions Requises

### Immédiat

1. ✅ Endpoint `/health` créé
2. ✅ Health check path mis à jour
3. ⏳ Attendre le déploiement (5-10 min)

### Après Déploiement

1. **Vérifier le health check:**
   ```bash
   aws elbv2 describe-target-health \
     --target-group-arn arn:aws:elasticloadbalancing:me-central-1:411714852748:targetgroup/arquantix-prod-tg/89fe413e994d9f0f \
     --region me-central-1
   ```
   Doit montrer: `Health: healthy`

2. **Invalidation CloudFront:**
   ```bash
   aws cloudfront create-invalidation \
     --distribution-id EPJ3WQCO04UWW \
     --paths "/*"
   ```

3. **Tester les URLs:**
   - `https://arquantix.com/health` → doit retourner `{"status":"ok"}`
   - `https://arquantix.com/` → doit afficher la page
   - `https://arquantix.com/media/logo/arquantix.svg` → doit servir le logo

---

## 🔄 Prochain Déploiement

Le workflow GitHub Actions va :
1. Build l'image avec l'endpoint `/health`
2. Push vers ECR
3. Déployer sur ECS
4. Le health check devrait passer HEALTHY
5. Le site devrait être accessible

---

## 📊 Monitoring

### Vérifier les Logs

```bash
aws logs tail /ecs/arquantix-coming-soon \
  --region me-central-1 \
  --since 30m \
  --format short
```

### Vérifier le Service

```bash
aws ecs describe-services \
  --cluster arquantix-cluster \
  --services arquantix-coming-soon \
  --region me-central-1
```

---

## 🎯 Résultat Attendu

Après le déploiement :
- ✅ Target Group: HEALTHY
- ✅ ALB: 200 OK
- ✅ Site accessible sur `https://arquantix.com`
- ✅ Médias accessibles sur `/media/...`
- ✅ Health check fonctionne sur `/health`

---

**Status:** ✅ Corrections appliquées, en attente de déploiement

