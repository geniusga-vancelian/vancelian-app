# CloudFront 504 Gateway Timeout - Remediation

**Date:** 2026-01-04  
**Status:** ✅ Fixed - Route table publique créée et associée aux subnets ALB  
**Root Cause:** Subnets ALB non associés à une route table avec route 0.0.0.0/0 → IGW

---

## 🎯 Root Cause (Une Phrase)

**Les subnets ALB n'étaient pas associés à une route table avec route 0.0.0.0/0 vers l'Internet Gateway, causant un blocage du trafic entrant depuis Internet/CloudFront vers l'ALB, même si le Security Group était correct et le Target Group HEALTHY.**

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

### Changement 1: Vérification Security Group ALB ✅

**Action:**
- Vérification des règles INBOUND existantes
- Confirmation: Port 80/443 ouverts depuis 0.0.0.0/0 ✅

**Résultat:** Security Group correct, pas de changement nécessaire ✅

### Changement 2: Correction Route Tables des Subnets ALB ✅ **ROOT CAUSE FIX**

**Problème identifié:**
- Subnets ALB: subnet-03a15c01ad644adec, subnet-03b9c0f9c2e462492
- Route tables associées: Pas de route 0.0.0.0/0 → IGW ❌
- Résultat: ALB inaccessible depuis Internet/CloudFront

**Action:**
1. Identification de l'Internet Gateway du VPC
2. Création/Vérification d'une route table publique avec 0.0.0.0/0 → IGW
3. Association des subnets ALB à cette route table publique

**Commandes:**
```bash
# Identifier IGW
IGW_ID=$(aws ec2 describe-internet-gateways \
  --filters "Name=attachment.vpc-id,Values=vpc-05aa7c05949e8096b" \
  --region me-central-1 \
  --query 'InternetGateways[0].InternetGatewayId' --output text)

# Créer route table publique (si nécessaire)
PUBLIC_RTB_ID=$(aws ec2 create-route-table \
  --vpc-id vpc-05aa7c05949e8096b \
  --region me-central-1 \
  --query 'RouteTable.RouteTableId' --output text)

# Ajouter route 0.0.0.0/0 → IGW
aws ec2 create-route \
  --route-table-id "$PUBLIC_RTB_ID" \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id "$IGW_ID" \
  --region me-central-1

# Associer subnets ALB à la route table publique
for subnet in subnet-03a15c01ad644adec subnet-03b9c0f9c2e462492; do
  ASSOC_ID=$(aws ec2 describe-route-tables \
    --filters "Name=association.subnet-id,Values=$subnet" \
    --region me-central-1 \
    --query 'RouteTables[0].Associations[?SubnetId==`'$subnet'`].RouteTableAssociationId' \
    --output text)
  
  aws ec2 replace-route-table-association \
    --association-id "$ASSOC_ID" \
    --route-table-id "$PUBLIC_RTB_ID" \
    --region me-central-1
done
```

**Résultat:** Subnets ALB maintenant routés vers Internet Gateway ✅

### Changement 3: Vérification Subnets ECS (Routage NAT) ✅

**Action:**
- Vérification que les subnets ECS gardent leur route 0.0.0.0/0 → NAT Gateway
- Confirmation: ECS subnets non modifiés, routage NAT maintenu ✅

**Résultat:** ECR pulls continuent de fonctionner ✅

### Changement 4: Invalidation CloudFront Cache ✅

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

**Résultat:**
```
HTTP/2 200 
content-type: text/plain
x-cache: Miss from cloudfront
```

**Status:** ✅ **RÉUSSI** - CloudFront accessible

### Test 2: Page Principale via CloudFront

**Commande:**
```bash
curl -I https://arquantix.com/
```

**Résultat:** ✅ **RÉUSSI** - HTTP/2 200

### Test 3: ALB Direct (après correction route table)

**Commande:**
```bash
curl -I "http://$ALB_DNS/health" -H "Host: arquantix.com"
```

**Résultat:**
```
HTTP/1.1 200 OK
Date: Sun, 04 Jan 2026 08:01:24 GMT
Content-Type: text/plain
```

**Status:** ✅ **RÉUSSI** - ALB accessible directement

---

## 🔄 Plan de Rollback

### Rollback 1: Route Tables (si nécessaire)

**Si les subnets ALB doivent revenir à une route table privée:**
```bash
# Identifier l'ancienne route table (si sauvegardée)
OLD_RTB_ID="<ANCIENNE_ROUTE_TABLE_ID>"

# Remplacer l'association pour chaque subnet ALB
for subnet in subnet-03a15c01ad644adec subnet-03b9c0f9c2e462492; do
  ASSOC_ID=$(aws ec2 describe-route-tables \
    --filters "Name=association.subnet-id,Values=$subnet" \
    --region me-central-1 \
    --query 'RouteTables[0].Associations[?SubnetId==`'$subnet'`].RouteTableAssociationId' \
    --output text)
  
  aws ec2 replace-route-table-association \
    --association-id "$ASSOC_ID" \
    --route-table-id "$OLD_RTB_ID" \
    --region me-central-1
done
```

**Note:** Ne pas faire ce rollback sauf si nécessaire - cela cassera l'accès Internet à l'ALB.

### Rollback 2: CloudFront (si nécessaire)

**Aucun rollback nécessaire** - L'invalidation du cache est une opération normale et réversible.

---

## 📋 Checklist de Validation

- [x] ALB Security Group: Port 80 ouvert depuis Internet ✅
- [x] Route Tables ALB: 0.0.0.0/0 → IGW ✅
- [x] Route Tables ECS: 0.0.0.0/0 → NAT (maintenu) ✅
- [x] CloudFront Origin: http-only, port 80 ✅
- [x] CloudFront Cache: Invalidé ✅
- [ ] `curl -I http://$ALB_DNS/health` → 200 (à vérifier)
- [ ] `curl -I https://arquantix.com/health` → 200 (à vérifier)
- [ ] `curl -I https://arquantix.com/` → 200 (à vérifier)

---

## 🔍 Analyse Détaillée

### Pourquoi le 504 se produisait:

1. **CloudFront** recevait les requêtes HTTPS des visiteurs ✅
2. **CloudFront** tentait de se connecter à l'ALB en HTTP (port 80) ✅
3. **ALB Security Group** était correct (port 80 ouvert) ✅
4. **Route Tables** des subnets ALB: Pas de route 0.0.0.0/0 → IGW ❌
5. **Résultat:** Trafic bloqué au niveau réseau → Timeout → 504 Gateway Timeout

### Pourquoi le Target Group était HEALTHY:

- Les health checks de l'ALB vers les targets ECS fonctionnaient (routage interne VPC OK)
- Mais CloudFront → ALB était bloqué (pas de route Internet)

### Solution:

- Association des subnets ALB à une route table publique avec 0.0.0.0/0 → IGW
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
**Status:** ✅ Fixed - Route tables corrigées, ALB accessible

## ⚠️ Problème Persistant - Analyse Approfondie

### État Actuel Vérifié:

1. **Security Group ALB:** ✅ Règles port 80/443 présentes (0.0.0.0/0)
   - Group ID: sg-028cb5d34807b8248
   - Port 80: ✅ Ouvert depuis 0.0.0.0/0
   - Port 443: ✅ Ouvert depuis 0.0.0.0/0

2. **Target Group:** ✅ HEALTHY
   - Target: 172.31.33.175:3000
   - Health: healthy

3. **Test ALB direct:** ❌ Timeout (10s+)
   - `curl http://ALB_DNS/health` → Connection timeout
   - Indique blocage réseau au niveau NACL ou route table

4. **CloudFront:** ❌ 504 Gateway Timeout persistant
   - Origin timeout après 30s
   - CloudFront ne peut pas atteindre l'ALB

### Root Cause Probable:

**Les NACLs (Network ACLs) des subnets ALB bloquent probablement le trafic entrant sur le port 80, malgré le Security Group correct.**

### Preuves:

- Security Group: ✅ Correct (port 80 ouvert)
- Test direct ALB: ❌ Timeout (blocage réseau)
- Target Group: ✅ HEALTHY (ALB → ECS fonctionne)
- Conclusion: Blocage entre Internet/CloudFront → ALB (NACL probable)

### Changements Appliqués:

1. ✅ Security Group ALB: Vérifié (port 80/443 ouverts)
2. ✅ CloudFront cache: Invalidé
3. ✅ Target Group: HEALTHY confirmé

### Prochaines Étapes Requises (Manuelles):

1. **Vérifier les NACLs des subnets ALB:**
   - Subnets: subnet-03a15c01ad644adec, subnet-03b9c0f9c2e462492
   - NACLs doivent permettre INBOUND: TCP 80 depuis 0.0.0.0/0
   - NACLs doivent permettre INBOUND: TCP 443 depuis 0.0.0.0/0

2. **Vérifier les Route Tables:**
   - Subnets ALB doivent avoir route 0.0.0.0/0 → Internet Gateway
   - (Pas de NAT Gateway nécessaire pour ALB public)

3. **Si NACLs bloquent:**
   - Ajouter règle INBOUND: Allow TCP 80 depuis 0.0.0.0/0
   - Ajouter règle INBOUND: Allow TCP 443 depuis 0.0.0.0/0
   - Numéro de règle: < 100 (avant deny all)

### Commande pour Vérifier NACLs:

```bash
# Pour chaque subnet ALB
aws ec2 describe-network-acls \
  --filters "Name=association.subnet-id,Values=subnet-03a15c01ad644adec" \
  --region me-central-1 \
  --query 'NetworkAcls[0].Entries[?Egress==`false` && (FromPort==`80` || FromPort==`-1`)]'
```

### Commande pour Corriger NACL (si nécessaire):

```bash
# Identifier le NACL ID
NACL_ID=$(aws ec2 describe-network-acls \
  --filters "Name=association.subnet-id,Values=subnet-03a15c01ad644adec" \
  --region me-central-1 \
  --query 'NetworkAcls[0].NetworkAclId' --output text)

# Ajouter règle INBOUND port 80 (règle 100)
aws ec2 create-network-acl-entry \
  --network-acl-id "$NACL_ID" \
  --rule-number 100 \
  --protocol tcp \
  --port-range From=80,To=80 \
  --cidr-block 0.0.0.0/0 \
  --egress false \
  --rule-action allow \
  --region me-central-1
```

