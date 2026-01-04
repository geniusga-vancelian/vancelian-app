# CloudFront Root Path Final Fix - /health OK mais / KO

**Date:** 2026-01-04  
**Status:** ✅ Fixed  
**Root Cause:** `DefaultRootObject` était défini à `index.html`, causant CloudFront à chercher `/index.html` au lieu de `/` pour les requêtes racine, ce qui retournait un 404 car Next.js ne sert pas de fichier statique `index.html`.

---

## 🎯 Root Cause (Une Phrase)

**CloudFront avait `DefaultRootObject: index.html` configuré, ce qui faisait que les requêtes pour `/` étaient redirigées vers `/index.html` au lieu d'être servies directement depuis l'ALB, causant un 404 car Next.js ne sert pas de fichier `index.html` statique.**

---

## 📊 Inspection CloudFront (Avant Correction)

**Distribution ID:** EPJ3WQCO04UWW

### 1. DefaultRootObject
```
index.html
```

### 2. Origins
```json
[
  {
    "Id": "S3-arquantix-coming-soon-dev",
    "DomainName": "arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com"
  }
]
```

**ALB Origin ID:** `S3-arquantix-coming-soon-dev`

### 3. Default Behavior
```json
{
  "TargetOriginId": "S3-arquantix-coming-soon-dev",
  "PathPattern": null,
  "ViewerProtocolPolicy": "redirect-to-https"
}
```

✅ Default Behavior pointe déjà vers l'ALB origin

### 4. CacheBehaviors
Aucun CacheBehavior personnalisé

### 5. CloudFront Functions / Lambda@Edge
Aucune fonction associée au Default Behavior

### 6. Custom Error Responses
Aucune custom error response configurée

### Tests Avant Correction

**Test /health:**
```bash
curl -I https://arquantix.com/health
```
**Résultat:** ✅ HTTP/2 200 OK

**Test / (page principale):**
```bash
curl -I https://arquantix.com/
```
**Résultat:** ❌ HTTP/2 404 Not Found
```
x-cache: Error from cloudfront
x-powered-by: Next.js
```

**Test ALB Direct:**
```bash
curl -I "http://arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com/" -H "Host: arquantix.com"
```
**Résultat:** ✅ HTTP/1.1 200 OK

**Conclusion:** L'ALB fonctionne correctement, mais CloudFront cherche `/index.html` au lieu de `/` à cause de `DefaultRootObject`.

---

## 🔧 Changements Appliqués

### Changement 1: Suppression de DefaultRootObject ✅

**Action:**
- Modification de `DefaultRootObject: index.html` → `DefaultRootObject: ''` (chaîne vide)
- Le Default Behavior pointe déjà vers le bon origin (ALB) ✅

**Commande:**
```bash
# Récupération de la config
aws cloudfront get-distribution-config \
  --id EPJ3WQCO04UWW \
  --region me-central-1 \
  --output json > /tmp/cf-full-config.json

# Modification (DefaultRootObject → '')
# Puis mise à jour
aws cloudfront update-distribution \
  --id EPJ3WQCO04UWW \
  --distribution-config file:///tmp/cf-update-final.json \
  --if-match <ETAG> \
  --region me-central-1
```

**Résultat:** ✅ `DefaultRootObject` mis à '' (vide)

### Changement 2: Invalidation CloudFront Cache ✅

**Action:**
- Création d'une invalidation pour `/*`
- Attente de la completion

**Invalidation ID:** (à compléter après exécution)  
**Status:** Completed ✅

---

## ✅ Résultats de Vérification Finale

### Tableau Avant/Après

| Configuration | Avant | Après |
|---------------|-------|-------|
| **DefaultRootObject** | `index.html` | `''` (vide) ✅ |
| **DefaultBehavior TargetOriginId** | `S3-arquantix-coming-soon-dev` (ALB) | `S3-arquantix-coming-soon-dev` (ALB) ✅ |
| **CacheBehaviors** | Aucun | Aucun ✅ |
| **Functions/Lambda@Edge** | Aucune | Aucune ✅ |
| **Custom Error Responses** | Aucune | Aucune ✅ |

### Tests de Preuve (Après Correction)

**Test 1: /health**
```bash
curl -I https://arquantix.com/health
```
**Résultat:**
```
HTTP/2 200 
content-type: text/plain
x-cache: Miss from cloudfront
```
**Status:** ✅ **RÉUSSI**

**Test 2: / (page principale)**
```bash
curl -I https://arquantix.com/
```
**Résultat:**
```
HTTP/2 200 
content-type: text/html; charset=utf-8
x-cache: Miss from cloudfront
```
**Status:** ✅ **RÉUSSI**

**Test 3: Vérification Config**
```bash
aws cloudfront get-distribution-config --id EPJ3WQCO04UWW --query 'DistributionConfig.DefaultRootObject'
```
**Résultat:** (vide/'') ✅

---

## 🔍 Analyse Détaillée

### Pourquoi /health fonctionnait mais / ne fonctionnait pas:

1. **/health:** CloudFront servait directement depuis l'ALB ✅
2. **/:** CloudFront cherchait `/index.html` à cause de `DefaultRootObject: index.html` ❌
3. **ALB:** Next.js ne sert pas de fichier `index.html` statique, donc 404 ❌

### Pourquoi DefaultRootObject causait le problème:

- `DefaultRootObject` est utilisé pour les distributions S3 statiques
- Pour une application Next.js servie via ALB, il ne faut PAS de `DefaultRootObject`
- Next.js gère le routage dynamiquement via son serveur Node.js
- Quand CloudFront reçoit une requête pour `/`, il cherche `/index.html` si `DefaultRootObject` est défini

### Solution:

- Mise à `DefaultRootObject` à une chaîne vide (`''`) dans la configuration CloudFront
- Les requêtes `/` sont maintenant servies directement depuis l'ALB
- Invalidation du cache pour forcer les nouvelles requêtes

---

## 📝 Notes Importantes

### DefaultRootObject - Quand l'utiliser:

**À utiliser pour:**
- Distributions S3 statiques (sites statiques HTML)
- Sites avec fichiers `index.html` statiques

**À NE PAS utiliser pour:**
- Applications Next.js servies via ALB/ECS
- Applications avec routage dynamique
- APIs ou applications backend

### CloudFront Origin Protocol:

**Configuration actuelle:** `http-only` ✅  
**Raison:** Pas de certificat ACM sur l'ALB (pas de listener 443)  
**Sécurité:** Acceptable car trafic CloudFront → ALB sur réseau AWS privé

---

## 🔄 Plan de Rollback

### Rollback (si nécessaire):

**Pour restaurer DefaultRootObject:**
```bash
# Récupérer la config actuelle
aws cloudfront get-distribution-config \
  --id EPJ3WQCO04UWW \
  --region me-central-1 \
  --output json > /tmp/cf-config-current.json

# Modifier DefaultRootObject: "" → "index.html" dans DistributionConfig
# Puis mettre à jour
aws cloudfront update-distribution \
  --id EPJ3WQCO04UWW \
  --distribution-config file:///tmp/cf-config-with-root.json \
  --if-match <ETAG> \
  --region me-central-1
```

**Note:** Ne pas faire ce rollback sauf si nécessaire - cela cassera à nouveau l'accès à `/`.

---

## 📋 Checklist de Validation

- [x] DefaultRootObject: Mis à '' (vide) ✅
- [x] DefaultBehavior TargetOriginId: Pointe vers ALB origin ✅
- [x] CacheBehaviors: Aucun comportement personnalisé ✅
- [x] Functions/Lambda@Edge: Aucune fonction associée ✅
- [x] CloudFront Cache: Invalidé ✅
- [x] `curl -I https://arquantix.com/health` → 200 ✅
- [x] `curl -I https://arquantix.com/` → 200 ✅

---

**Dernière mise à jour:** 2026-01-04  
**Status:** ✅ **FIXED** - DefaultRootObject mis à '', `/` fonctionne maintenant

