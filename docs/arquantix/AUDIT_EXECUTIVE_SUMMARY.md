# Audit Production - Résumé Exécutif

**Date:** 2026-01-03  
**Site:** https://arquantix.com/  
**Status:** ❌ Inaccessible (504 Gateway Timeout)

---

## 🎯 Root Cause (Une Phrase)

**CloudFront est configuré pour se connecter en HTTPS (port 443) à l'ALB, mais l'ALB n'a pas de listener HTTPS (443), seulement HTTP (80), causant des timeouts et rendant le site inaccessible.**

---

## 📊 Diagramme de l'État Actuel

```
Route53 (arquantix.com, www.arquantix.com)
    │
    ▼ A/AAAA
CloudFront (d2gtzmv0zk47i6.cloudfront.net)
    │ Origin: ALB DNS ✅
    │ Protocol: http-only ⚠️ (mais essaie HTTPS)
    │
    ▼ HTTPS (port 443) ❌ ÉCHEC
ALB (arquantix-prod-alb)
    │ Listener 80: HTTP ✅
    │ Listener 443: ❌ MANQUANT
    │
    ▼ Forward
Target Group (arquantix-prod-tg)
    │ Port: 80 (traffic-port → 3000)
    │ Targets: UNHEALTHY ❌
    │
    ▼
ECS Service (arquantix-coming-soon)
    │ Tasks: Running mais unhealthy
    │ Health Check Grace: 180s ✅
```

---

## 🚨 Problèmes Critiques

### 1. ALB: Listener HTTPS (443) Manquant ❌ **CRITIQUE**

**Impact:** CloudFront ne peut pas se connecter à l'ALB en HTTPS  
**Solution:** Créer listener 443 avec certificat ACM

### 2. CloudFront: Protocol Policy "http-only" ⚠️

**Impact:** Incohérence avec la tentative de connexion HTTPS  
**Solution:** Changer en "https-only" après création du listener 443

### 3. Target Group: Targets UNHEALTHY ❌

**Impact:** Pas de targets disponibles pour servir le trafic  
**Solution:** Résoudre après correction de l'ALB

### 4. ECS: Erreurs ECR Timeout ⚠️

**Impact:** Tasks ne peuvent pas démarrer (problème réseau)  
**Solution:** Vérifier NAT Gateway / VPC endpoints

---

## 🔧 Changements AWS Requis (Ordre d'Application)

### 1. Créer Certificat ACM (si absent) ⚠️
- Région: me-central-1
- Domaines: arquantix.com, www.arquantix.com
- Validation: DNS via Route53

### 2. Créer Listener HTTPS (443) sur ALB ❌ **CRITIQUE**
- Protocol: HTTPS
- Port: 443
- Certificate: ACM (me-central-1)
- Default Action: Forward to arquantix-prod-tg

### 3. Modifier Listener HTTP (80) pour Redirect
- Type: Redirect
- Protocol: HTTPS
- Port: 443
- Status Code: 301

### 4. Mettre à jour CloudFront Origin Protocol
- Protocol Policy: https-only (au lieu de http-only)

### 5. ✅ Health Check Grace Period (DÉJÀ APPLIQUÉ)
- 180 secondes

---

## 🧪 Tests de Preuve

### Test 1: Health Check
```bash
curl -I https://arquantix.com/health
# Attendu: HTTP/2 200
```

### Test 2: ALB Direct (HTTPS)
```bash
ALB_DNS="arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com"
curl -I -k -H "Host: arquantix.com" "https://$ALB_DNS/health"
# Attendu: HTTP/1.1 200 (après création listener 443)
```

### Test 3: Target Group Health
```bash
aws elbv2 describe-target-health \
  --target-group-arn <TG_ARN> \
  --region me-central-1
# Attendu: Au moins 1 target HEALTHY
```

---

## 🔄 Plan de Rollback

### Rollback Rapide
```bash
# Supprimer listener 443
aws elbv2 delete-listener --listener-arn <LISTENER_443_ARN> --region me-central-1

# Restaurer listener 80
aws elbv2 modify-listener \
  --listener-arn <LISTENER_80_ARN> \
  --default-actions Type=forward,TargetGroupArn=<TG_ARN> \
  --region me-central-1

# Restaurer CloudFront
aws cloudfront update-distribution \
  --id EPJ3WQCO04UWW \
  --if-match <ETAG> \
  --distribution-config file://<ORIGINAL_CONFIG> \
  --region me-central-1
```

---

## 📋 Checklist de Validation

- [ ] Certificat ACM créé et validé dans me-central-1
- [ ] Listener 443 créé sur ALB
- [ ] Listener 80 modifié pour redirect 443
- [ ] CloudFront protocol policy = https-only
- [ ] Target Group: Au moins 1 target HEALTHY
- [ ] `curl -I https://arquantix.com/health` → 200
- [ ] `curl -I https://arquantix.com/` → 200

---

**Dernière mise à jour:** 2026-01-03

