# Configuration Certificat SSL pour www.arquantix.com

**Date:** 2026-01-01  
**Domaine:** www.arquantix.com  
**Région ACM:** us-east-1 (exigence CloudFront)

---

## ✅ Actions Effectuées

### 1. Certificat ACM Créé

- **Domaine principal:** `www.arquantix.com`
- **Domaine alternatif:** `arquantix.com`
- **Méthode de validation:** DNS
- **Région:** `us-east-1` (exigence CloudFront)

### 2. Enregistrements DNS de Validation

Les enregistrements CNAME de validation ont été ajoutés dans Route53 (zone `arquantix.com`).

**Format des enregistrements:**
- **Name:** `_xxxxx.www.arquantix.com` (fourni par ACM)
- **Type:** CNAME
- **Value:** `_xxxxx.acm-validations.aws.` (fourni par ACM)

### 3. CloudFront Mis à Jour

- **Alias ajouté:** `www.arquantix.com`
- **Certificat SSL:** Certificat ACM (une fois validé)

---

## ⏳ En Attente

### Validation du Certificat

Le certificat est en cours de validation. Cela prend généralement **quelques minutes** après l'ajout des enregistrements DNS.

**Vérifier le statut:**
```bash
# Remplacer CERT_ARN par l'ARN réel du certificat
aws acm describe-certificate \
  --certificate-arn CERT_ARN \
  --region us-east-1 \
  --query 'Certificate.{Status:Status,ValidationStatus:DomainValidationOptions[0].ValidationStatus}' \
  --output json
```

**Statuts possibles:**
- `PENDING_VALIDATION`: En attente de validation
- `ISSUED`: ✅ Certificat validé et émis
- `VALIDATION_TIMED_OUT`: Échec de validation (vérifier les enregistrements DNS)

### Déploiement CloudFront

Après la validation du certificat, CloudFront doit être mis à jour. Cela prend **5-10 minutes**.

**Vérifier le statut:**
```bash
aws cloudfront get-distribution --id EPJ3WQCO04UWW \
  --query 'Distribution.{Status:Status,Aliases:Aliases.Items}' \
  --output json
```

**Statut attendu:** `Deployed` (pas `InProgress`)

---

## 🔍 Vérification

### Vérifier les Enregistrements DNS de Validation

```bash
aws route53 list-resource-record-sets \
  --hosted-zone-id Z08819812KDG05NSYVRFJ \
  --query "ResourceRecordSets[?contains(Name, 'acm-validations')].{Name:Name,Type:Type,Value:ResourceRecords[0].Value}" \
  --output table
```

### Vérifier le Statut du Certificat

```bash
# Lister les certificats
aws acm list-certificates --region us-east-1 \
  --query "CertificateSummaryList[?contains(DomainName, 'arquantix')].{DomainName:DomainName,Status:Status,Arn:CertificateArn}" \
  --output table

# Détails d'un certificat spécifique
aws acm describe-certificate \
  --certificate-arn CERT_ARN \
  --region us-east-1 \
  --query 'Certificate.{DomainName:DomainName,Status:Status,ValidationStatus:DomainValidationOptions[*].{Domain:DomainName,Status:ValidationStatus}}' \
  --output json
```

### Vérifier CloudFront

```bash
aws cloudfront get-distribution --id EPJ3WQCO04UWW \
  --query 'Distribution.{Id:Id,Status:Status,Aliases:Aliases.Items,Certificate:DistributionConfig.ViewerCertificate.ACMCertificateArn}' \
  --output json
```

### Tester le Site

```bash
# Tester avec curl
curl -I https://www.arquantix.com

# Vérifier le certificat SSL
openssl s_client -connect www.arquantix.com:443 -servername www.arquantix.com < /dev/null 2>/dev/null | openssl x509 -noout -dates
```

---

## 🆘 Dépannage

### Le Certificat Ne Se Valide Pas

1. **Vérifier les enregistrements DNS:**
   - Les enregistrements CNAME doivent être présents dans Route53
   - Les valeurs doivent correspondre exactement à celles fournies par ACM

2. **Vérifier la propagation DNS:**
   ```bash
   dig _xxxxx.www.arquantix.com CNAME
   ```
   Doit résoudre vers la valeur fournie par ACM

3. **Réessayer la validation:**
   - Parfois, il faut attendre quelques minutes supplémentaires
   - AWS vérifie périodiquement les enregistrements DNS

### CloudFront Ne Peut Pas Utiliser le Certificat

1. **Vérifier que le certificat est validé:**
   - Le statut doit être `ISSUED`

2. **Vérifier que le certificat est dans us-east-1:**
   - CloudFront exige us-east-1

3. **Vérifier que le domaine correspond:**
   - Le certificat doit couvrir `www.arquantix.com` (ou wildcard `*.arquantix.com`)

---

## 📋 Checklist

- [x] Certificat ACM créé dans us-east-1
- [x] Enregistrements DNS de validation ajoutés dans Route53
- [x] CloudFront mis à jour avec alias et certificat
- [ ] Certificat validé (statut: ISSUED)
- [ ] CloudFront déployé (statut: Deployed)
- [ ] Site accessible via https://www.arquantix.com
- [ ] Certificat SSL valide (pas d'erreur de certificat)

---

## 🌐 URLs

### Après Validation Complète

```
https://www.arquantix.com
```

**Status:** En attente de validation du certificat et déploiement CloudFront

### CloudFront Direct (toujours disponible)

```
https://d2gtzmv0zk47i6.cloudfront.net
```

---

**Dernière mise à jour:** 2026-01-01  
**Status:** ⏳ En attente de validation du certificat


