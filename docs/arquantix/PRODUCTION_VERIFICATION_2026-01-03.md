# Production Verification - Arquantix.com (Read-Only)

**Date:** 2026-01-03  
**Région ALB:** me-central-1  
**Mode:** Fact finding uniquement (pas de modifications)

---

## 1. DNS Routing (Route53)

### Commande utilisée:
```bash
aws route53 list-resource-record-sets \
  --hosted-zone-id Z08819812KDG05NSYVRFJ \
  --query "ResourceRecordSets[?Name=='arquantix.com.' || Name=='www.arquantix.com.']"
```

### Résultats:

#### arquantix.com
- **Record Type:** A (Alias)
- **Alias Target:**
  - **HostedZoneId:** Z2FDTNDATAQYW2 (CloudFront)
  - **DNSName:** d2gtzmv0zk47i6.cloudfront.net.
  - **EvaluateTargetHealth:** false
- **Point vers:** ✅ **CloudFront Distribution** (d2gtzmv0zk47i6.cloudfront.net)

#### www.arquantix.com
- **Record Type:** A (Alias)
- **Alias Target:**
  - **HostedZoneId:** Z2FDTNDATAQYW2 (CloudFront)
  - **DNSName:** d2gtzmv0zk47i6.cloudfront.net.
  - **EvaluateTargetHealth:** false
- **Point vers:** ✅ **CloudFront Distribution** (d2gtzmv0zk47i6.cloudfront.net)

**Preuve:**
- Zone ID: Z08819812KDG05NSYVRFJ
- Les deux domaines pointent vers la même distribution CloudFront

---

## 2. CloudFront Distribution

### Distribution ID: EPJ3WQCO04UWW

### Commande utilisée:
```bash
aws cloudfront get-distribution-config \
  --id EPJ3WQCO04UWW \
  --region me-central-1
```

### Résultats:

#### Status
- **Status:** Deployed ✅

#### Domain Name
- **DomainName:** d2gtzmv0zk47i6.cloudfront.net

#### Origin Configuration

**Origin Domain Name:**
```
arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com
```

**Origin Path:**
```
"" (vide/empty)
```

**Origin Protocol Policy:**
```
http-only
```

**TLS Versions (Origin SSL Protocols):**
```
["TLSv1.2"]
```

**HTTPS Port:**
```
443
```

**Preuve:**
- Origin Domain = ALB DNS (arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com)
- Origin Path = "" (vide)
- Protocol Policy = "http-only" ⚠️
- TLS 1.2 activé

---

## 3. Application Load Balancer (Référence)

### Commande utilisée:
```bash
aws elbv2 describe-load-balancers \
  --region me-central-1 \
  --query 'LoadBalancers[?contains(LoadBalancerName, `arquantix`)]'
```

### Résultats:

**ALB Name:** arquantix-prod-alb  
**ALB DNS:** arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com  
**Région:** me-central-1  
**Scheme:** internet-facing

**Vérification:**
- ✅ CloudFront Origin Domain = ALB DNS (match exact)

---

## 4. Preuve / Evidence

### Console AWS Paths:

#### Route53
1. **AWS Console** → **Route53** → **Hosted zones**
2. **arquantix.com** (Zone ID: Z08819812KDG05NSYVRFJ)
3. **Records** → Voir les records A pour `arquantix.com` et `www.arquantix.com`
4. **Type:** A (Alias) → **Alias target:** d2gtzmv0zk47i6.cloudfront.net

#### CloudFront
1. **AWS Console** → **CloudFront** → **Distributions**
2. **Distribution ID:** EPJ3WQCO04UWW
3. **Onglet "Origins"** → Cliquer sur l'origin
4. **Voir:**
   - **Origin domain:** arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com
   - **Origin path:** (vide)
   - **Origin protocol policy:** HTTP Only
   - **Origin SSL protocols:** TLSv1.2

#### ALB
1. **AWS Console** → **EC2** → **Load Balancers**
2. **arquantix-prod-alb**
3. **DNS name:** arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com

### CLI Commands (Exact):

```bash
# Route53
aws route53 list-resource-record-sets \
  --hosted-zone-id Z08819812KDG05NSYVRFJ \
  --query "ResourceRecordSets[?Name=='arquantix.com.' || Name=='www.arquantix.com.']"

# CloudFront
aws cloudfront get-distribution-config \
  --id EPJ3WQCO04UWW \
  --region me-central-1 \
  --query 'DistributionConfig.Origins.Items[0]'

# ALB
aws elbv2 describe-load-balancers \
  --region me-central-1 \
  --query 'LoadBalancers[?contains(LoadBalancerName, `arquantix`)]'
```

---

## 5. Résumé Final (Réponses Directes)

### Question 1: CloudFront → ALB protocol is currently:
**Réponse:** `http-only`

**Détails:**
- CloudFront est configuré avec `OriginProtocolPolicy: http-only`
- Mais CloudFront essaie de se connecter en HTTPS (port 443) à l'ALB
- L'ALB n'a pas de listener HTTPS (443), seulement HTTP (80)
- **Incohérence détectée:** Protocol policy = "http-only" mais HTTPS port = 443

### Question 2: arquantix.com currently points to:
**Réponse:** `CloudFront Distribution (d2gtzmv0zk47i6.cloudfront.net)`

**Détails:**
- Record Type: A (Alias)
- Alias Target: d2gtzmv0zk47i6.cloudfront.net
- HostedZoneId: Z2FDTNDATAQYW2 (CloudFront)

### Question 3: www.arquantix.com currently points to:
**Réponse:** `CloudFront Distribution (d2gtzmv0zk47i6.cloudfront.net)`

**Détails:**
- Record Type: A (Alias)
- Alias Target: d2gtzmv0zk47i6.cloudfront.net
- HostedZoneId: Z2FDTNDATAQYW2 (CloudFront)
- Même distribution que arquantix.com

---

## 6. Observations Importantes

### ✅ Points Corrects:
1. Route53 pointe vers CloudFront (correct)
2. CloudFront origin = ALB DNS (correct)
3. Origin path = "" (vide, correct)
4. TLS 1.2 activé (correct)

### ⚠️ Points d'Attention:
1. **Protocol Policy = "http-only"** mais CloudFront utilise le port 443 (HTTPS)
2. **ALB n'a pas de listener 443** (seulement listener 80)
3. **Incohérence:** CloudFront configuré en "http-only" mais essaie HTTPS vers un port 443 inexistant

### 🔍 Analyse:
- Le problème principal est que CloudFront est configuré pour se connecter en HTTPS (port 443) à l'ALB, mais:
  - L'ALB n'a pas de listener HTTPS (443)
  - Le protocol policy est "http-only" (incohérent avec le port 443)
- Cela cause des timeouts/erreurs 502/504 car CloudFront ne peut pas établir la connexion HTTPS

---

## 7. État Actuel (Schéma)

```
Route53 (arquantix.com, www.arquantix.com)
    │
    ▼ A (Alias)
CloudFront (d2gtzmv0zk47i6.cloudfront.net)
    │ Distribution ID: EPJ3WQCO04UWW
    │ Status: Deployed
    │ Origin: arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com
    │ Origin Path: "" (vide)
    │ Protocol Policy: http-only ⚠️
    │ HTTPS Port: 443
    │
    ▼ HTTPS (port 443) → ❌ ÉCHEC
ALB (arquantix-prod-alb)
    │ DNS: arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com
    │ Listener 80: HTTP ✅
    │ Listener 443: ❌ MANQUANT
    │
    ▼ Forward
Target Group (arquantix-prod-tg)
```

---

**Dernière mise à jour:** 2026-01-03  
**Mode:** Read-only verification (aucune modification appliquée)

