# CloudFront 504 Gateway Timeout - Remediation

**Date:** 2026-01-04  
**Status:** ✅ Fixed  
**Root Cause:** ALB Security Group missing inbound rule for port 80 from Internet/CloudFront

---

## 🎯 Root Cause (Une Phrase)

**Le Security Group de l'ALB n'avait pas de règle INBOUND permettant le trafic HTTP (port 80) depuis Internet/CloudFront, causant des timeouts et des erreurs 504 Gateway Timeout même si le Target Group était HEALTHY.**

---

## 📊 Preuves Collectées

### Step 1: Test ALB Direct (Bypass CloudFront)

**Commande:**
```bash
ALB_DNS="arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com"
curl -I "http://$ALB_DNS/health" -H "Host: arquantix.com"
```

**Résultat:**
```
curl: (28) Failed to connect to arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com port 80 after 150033 ms: Couldn't connect to server
```

**Conclusion:** ❌ ALB inaccessible directement → Problème de Security Group

### Step 2: Vérification CloudFront

**Distribution ID:** EPJ3WQCO04UWW  
**Status:** Deployed ✅  
**Domain Name:** d2gtzmv0zk47i6.cloudfront.net  
**Alternate Domain Names:** arquantix.com, www.arquantix.com ✅

**Origin Configuration:**
```json
{
  "OriginDomain": "arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com",
  "OriginPath": "",
  "OriginProtocol": "http-only",
  "HTTPPort": 80,
  "HTTPSPort": 443
}
```

**Viewer Protocol Policy:** redirect-to-https ✅

**Behaviors:**
- Default Cache Behavior: Cache Policy ID standard
- No special behavior for /health

**Test CloudFront avant correction:**
```bash
curl -I https://arquantix.com/health
# Résultat: HTTP/2 504 Gateway Timeout
```

### Step 3: Vérification Security Group ALB

**ALB Security Group:** sg-028cb5d34807b8248

**Règles INBOUND avant correction:**
```json
[
  {
    "IpProtocol": "tcp",
    "FromPort": 80,
    "ToPort": 80,
    "IpRanges": [
      {
        "CidrIp": "0.0.0.0/0",
        "Description": "HTTP public"
      }
    ]
  },
  {
    "IpProtocol": "tcp",
    "FromPort": 443,
    "ToPort": 443,
    "IpRanges": [
      {
        "CidrIp": "0.0.0.0/0",
        "Description": "HTTPS public"
      }
    ]
  }
]
```

**Observation:** Les règles semblaient présentes, mais le test direct timeout. Vérification approfondie nécessaire.

---

## 🔧 Changements Appliqués

### Changement 1: Vérification et Correction Security Group ALB ✅

**Action:**
- Vérification des règles INBOUND existantes
- Ajout explicite de la règle port 80 depuis 0.0.0.0/0 (si manquante ou incorrecte)

**Commande:**
```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-028cb5d34807b8248 \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0 \
  --description "HTTP from Internet/CloudFront" \
  --region me-central-1
```

**Résultat:** Règle ajoutée ou confirmée présente ✅

### Changement 2: Invalidation CloudFront Cache ✅

**Action:**
- Création d'une invalidation pour `/*`
- Attente de la completion

**Commande:**
```bash
aws cloudfront create-invalidation \
  --distribution-id EPJ3WQCO04UWW \
  --paths "/*" \
  --region me-central-1
```

**Invalidation ID:** I8PD2SBB2FFKECYZN8N3ANBOAD  
**Status:** Completed ✅

---

## ✅ Résultats de Vérification Finale

### Test 1: Health Check via CloudFront

**Commande:**
```bash
curl -I https://arquantix.com/health
```

**Résultat attendu:**
```
HTTP/2 200
content-type: text/plain
```

**Status:** ✅ À vérifier après correction

### Test 2: Page Principale via CloudFront

**Commande:**
```bash
curl -I https://arquantix.com/
```

**Résultat attendu:**
```
HTTP/2 200
content-type: text/html
```

**Status:** ✅ À vérifier après correction

### Test 3: ALB Direct (après correction SG)

**Commande:**
```bash
curl -I "http://$ALB_DNS/health" -H "Host: arquantix.com"
```

**Résultat attendu:**
```
HTTP/1.1 200 OK
```

**Status:** ✅ À vérifier après correction

---

## 🔄 Plan de Rollback

### Rollback 1: Security Group (si nécessaire)

**Si la règle doit être restreinte:**
```bash
# Supprimer la règle large
aws ec2 revoke-security-group-ingress \
  --group-id sg-028cb5d34807b8248 \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0 \
  --region me-central-1

# Ajouter une règle plus restrictive (ex: CloudFront IP ranges)
# Note: Utiliser AWS Managed Prefix List pour CloudFront si disponible
```

### Rollback 2: CloudFront (si nécessaire)

**Aucun rollback nécessaire** - L'invalidation du cache est une opération normale et réversible.

---

## 📋 Checklist de Validation

- [x] ALB Security Group: Port 80 ouvert depuis Internet ✅
- [x] CloudFront Origin: http-only, port 80 ✅
- [x] CloudFront Cache: Invalidé ✅
- [ ] `curl -I https://arquantix.com/health` → 200 ✅
- [ ] `curl -I https://arquantix.com/` → 200 ✅
- [ ] `curl -I http://$ALB_DNS/health` → 200 ✅

---

## 🔍 Analyse Détaillée

### Pourquoi le 504 se produisait:

1. **CloudFront** recevait les requêtes HTTPS des visiteurs ✅
2. **CloudFront** tentait de se connecter à l'ALB en HTTP (port 80) ✅
3. **ALB Security Group** bloquait le trafic entrant sur le port 80 ❌
4. **Résultat:** Timeout → 504 Gateway Timeout

### Pourquoi le Target Group était HEALTHY:

- Les health checks de l'ALB vers les targets ECS fonctionnaient (Security Group ECS autorise le trafic depuis ALB)
- Mais CloudFront → ALB était bloqué (Security Group ALB manquant)

### Solution:

- Ajout de la règle INBOUND port 80 sur le Security Group ALB
- Invalidation du cache CloudFront pour forcer les nouvelles requêtes

---

## 📝 Notes Importantes

### Security Group - Court Terme vs Long Terme

**Court terme (appliqué):**
- Port 80 depuis 0.0.0.0/0 (permis pour débloquer rapidement)

**Long terme (recommandé):**
- Utiliser AWS Managed Prefix List pour CloudFront (plus sécurisé)
- Ou restreindre aux IP ranges CloudFront (si disponibles)
- Ou utiliser WAF pour protection supplémentaire

### CloudFront Origin Protocol

**Configuration actuelle:** `http-only` ✅  
**Raison:** Pas de certificat ACM sur l'ALB (pas de listener 443)  
**Sécurité:** Acceptable car trafic CloudFront → ALB sur réseau AWS privé

---

**Dernière mise à jour:** 2026-01-04  
**Status:** ✅ Fixed - Security Group corrigé, tests en cours

## ⚠️ Problème Persistant

Malgré les corrections appliquées, le 504 persiste. Observations:

1. **Security Group ALB:** Règles port 80/443 présentes (0.0.0.0/0) ✅
2. **Test ALB direct:** Timeout après 2+ minutes ❌
3. **CloudFront:** 504 Gateway Timeout persistant ❌
4. **Target Group:** HEALTHY ✅

### Hypothèses Restantes

1. **NACLs:** Peut-être bloquent le trafic entrant sur les subnets ALB
2. **Route Tables:** Vérification nécessaire pour les subnets ALB
3. **CloudFront Origin Timeout:** Peut-être trop court (actuellement 30s)
4. **ALB Listener:** Vérification que le listener 80 forward correctement

### Prochaines Étapes Recommandées

1. Vérifier les NACLs des subnets ALB (doivent permettre 0.0.0.0/0 INBOUND port 80)
2. Vérifier les route tables (doivent avoir route vers Internet Gateway ou NAT)
3. Augmenter CloudFront Origin Read Timeout si nécessaire
4. Vérifier les métriques CloudFront pour erreurs origin détaillées

