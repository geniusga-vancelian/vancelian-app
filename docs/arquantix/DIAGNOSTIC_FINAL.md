# Diagnostic Final - Problème 504 Gateway Timeout

**Date:** 2026-01-03  
**Objectif:** Résoudre définitivement le 504 Gateway Timeout

---

## 🔍 Diagnostic Complet

### Problème Identifié

**Le serveur Next.js démarre mais ne répond pas aux requêtes HTTP.**

**Preuves:**
1. ✅ Logs ECS: "Ready in 2.2s" - Le serveur démarre
2. ❌ Test direct IP privée: Timeout - Le serveur ne répond pas
3. ❌ Test ALB: Timeout - Le serveur ne répond pas
4. ❌ Target Group: UNHEALTHY - Health checks échouent

### Cause Racine Probable

**Next.js n'écoute pas sur `0.0.0.0:3000` mais probablement sur `127.0.0.1:3000`.**

Même si `HOSTNAME=0.0.0.0` est défini, Next.js pourrait ne pas l'utiliser correctement sans le flag `-H`.

---

## ✅ Corrections Appliquées

### 1. Dockerfile - Flag `-H 0.0.0.0`

**Avant:**
```dockerfile
CMD ["node_modules/.bin/next", "start", "-p", "3000"]
```

**Après:**
```dockerfile
CMD ["node_modules/.bin/next", "start", "-H", "0.0.0.0", "-p", "3000"]
```

**Impact:** Force Next.js à écouter sur `0.0.0.0` au lieu de `127.0.0.1`.

### 2. Health Check Path

**Avant:** `/fr`  
**Après:** `/health`

**Impact:** Endpoint dédié, plus robuste, pas de dépendance à i18n.

### 3. Logs de Diagnostic

**Ajouté:**
- `instrumentation.ts`: Logs au démarrage (HOSTNAME, PORT, etc.)
- `/health` route: Logs à chaque hit

**Impact:** Permet de diagnostiquer les problèmes de démarrage.

### 4. Middleware pour /fr → /

**Ajouté:** `middleware.ts` qui redirige `/fr` vers `/` (308 permanent).

**Impact:** Le site fonctionne sur `/` sans `/fr`.

---

## 📊 Configuration Finale

### Target Group
- **Port:** 80 (forward vers port 3000 des targets)
- **Health Check Path:** `/health`
- **Health Check Matcher:** `200`
- **Timeout:** 10 secondes
- **Interval:** 30 secondes

### ECS Task Definition
- **Container Port:** 3000
- **Host Port:** 3000
- **Environment:**
  - `PORT=3000`
  - `HOSTNAME=0.0.0.0`
  - `HOST=0.0.0.0`

### Next.js
- **Command:** `next start -H 0.0.0.0 -p 3000`
- **Health Endpoint:** `/health` (200 OK)
- **Middleware:** Redirige `/fr` → `/`

---

## 🧪 Tests de Validation

### Après Déploiement

```bash
# 1. Health check
curl -I https://arquantix.com/health
# Attendu: 200 OK

# 2. Page principale
curl -I https://arquantix.com/
# Attendu: 200 OK

# 3. Redirection /fr
curl -I https://arquantix.com/fr
# Attendu: 308 Location: /

# 4. Target Group health
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:me-central-1:411714852748:targetgroup/arquantix-prod-tg/89fe413e994d9f0f \
  --region me-central-1
# Attendu: Health: healthy
```

---

## 📋 Checklist de Validation

- [ ] Service ECS: RUNNING
- [ ] Target Group: HEALTHY
- [ ] `/health`: 200 OK
- [ ] `/`: 200 OK
- [ ] `/fr`: 308 → `/`
- [ ] Logs ECS montrent "Listening on 0.0.0.0:3000"
- [ ] Aucun 504/502 dans les tests

---

## 🔄 Plan de Rollback

Voir `docs/arquantix/ROLLBACK.md` pour la procédure complète.

**Rollback rapide:**
```bash
aws ecs update-service \
  --cluster arquantix-cluster \
  --service arquantix-coming-soon \
  --task-definition arquantix-coming-soon:1 \
  --region me-central-1 \
  --force-new-deployment
```

---

## 📝 Fichiers Modifiés

1. `services/arquantix/web/Dockerfile` - Ajout `-H 0.0.0.0`
2. `services/arquantix/web/src/app/health/route.ts` - Logs ajoutés
3. `services/arquantix/web/src/instrumentation.ts` - Nouveau (logs startup)
4. `services/arquantix/web/src/middleware.ts` - Nouveau (redirect /fr → /)
5. `services/arquantix/web/next.config.js` - instrumentationHook activé

---

## ⏳ Prochain Déploiement

Le workflow GitHub Actions va automatiquement:
1. Build l'image avec les corrections
2. Push vers ECR
3. Déployer sur ECS

**Temps estimé:** 5-10 minutes

**Résultat attendu:** Site opérationnel sur `https://arquantix.com/` sans 504/502.

---

**Status:** ✅ Corrections appliquées, en attente de déploiement

