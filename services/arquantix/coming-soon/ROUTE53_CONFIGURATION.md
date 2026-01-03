# Configuration Route53 pour Arquantix

**Date:** 2026-01-01  
**CloudFront Distribution ID:** `EPJ3WQCO04UWW`  
**CloudFront Domain:** `d2gtzmv0zk47i6.cloudfront.net`

---

## ⚠️ Permissions Requises

Les permissions suivantes sont nécessaires pour Route53:
- `route53:ListHostedZones`
- `route53:GetHostedZone`
- `route53:ListResourceRecordSets`
- `route53:ChangeResourceRecordSets`

Si vous n'avez pas ces permissions avec l'utilisateur `cursor-admin`, utilisez:
- AWS Console avec un utilisateur ayant plus de permissions
- Ou demandez à un administrateur AWS d'ajouter ces permissions

---

## 📋 Étapes de Configuration

### Étape 0: Vérifier ce qui existe déjà

#### Via AWS Console

1. **Ouvrir Route53 Console:**
   https://console.aws.amazon.com/route53/v2/hostedzones

2. **Lister les Hosted Zones:**
   - Chercher une zone nommée `arquantix.com` ou `www.arquantix.com`
   - Chercher la zone `maisonganopa.com` (si vous voulez utiliser un sous-domaine)

3. **Vérifier les enregistrements existants:**
   - Si une zone `arquantix.com` existe, voir les enregistrements existants
   - Si la zone `maisonganopa.com` existe, vérifier s'il y a déjà un enregistrement `arquantix` ou `arquantix.maisonganopa.com`

#### Via AWS CLI (avec permissions)

```bash
# Lister toutes les hosted zones
aws route53 list-hosted-zones --query 'HostedZones[*].{Name:Name,Id:Id}' --output table

# Vérifier la zone maisonganopa.com (si elle existe)
MAISON_ZONE_ID=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='maisonganopa.com.'].Id" --output text | awk -F'/' '{print $NF}')
if [ -n "$MAISON_ZONE_ID" ]; then
  echo "Zone maisonganopa.com trouvée: $MAISON_ZONE_ID"
  aws route53 list-resource-record-sets --hosted-zone-id $MAISON_ZONE_ID --query "ResourceRecordSets[*].{Name:Name,Type:Type}" --output table
fi

# Vérifier si une zone arquantix.com existe
ARQUANTIX_ZONE_ID=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='arquantix.com.'].Id" --output text | awk -F'/' '{print $NF}')
if [ -n "$ARQUANTIX_ZONE_ID" ]; then
  echo "Zone arquantix.com trouvée: $ARQUANTIX_ZONE_ID"
  aws route53 list-resource-record-sets --hosted-zone-id $ARQUANTIX_ZONE_ID --output table
fi
```

---

## 🎯 Options de Configuration

### Option A: Sous-domaine sur maisonganopa.com (Recommandé si la zone existe)

**Domain:** `arquantix.maisonganopa.com`

#### Via AWS Console

1. **Ouvrir Route53 Console:**
   https://console.aws.amazon.com/route53/v2/hostedzones

2. **Trouver la zone `maisonganopa.com`:**
   - Cliquer sur la zone `maisonganopa.com`

3. **Vérifier si un enregistrement `arquantix` existe déjà:**
   - Chercher dans la liste des enregistrements
   - Si `arquantix.maisonganopa.com` existe déjà:
     - Vérifier son type (A, CNAME, etc.)
     - Décider si vous voulez le modifier ou en créer un nouveau

4. **Créer ou modifier l'enregistrement:**
   - **Si l'enregistrement n'existe pas:**
     - Cliquer sur "Create record"
     - **Record name:** `arquantix`
     - **Record type:** A
     - **Alias:** Yes
     - **Route traffic to:** Alias to CloudFront distribution
     - **Choose distribution:** Sélectionner `EPJ3WQCO04UWW` (ou chercher "Arquantix Coming Soon" dans la liste)
     - **Evaluate target health:** No
     - Cliquer sur "Create records"
   
   - **Si l'enregistrement existe déjà:**
     - Cliquer sur l'enregistrement
     - Cliquer sur "Edit"
     - Modifier pour pointer vers CloudFront (comme ci-dessus)
     - Sauvegarder

#### Via AWS CLI (avec permissions)

```bash
# Obtenir l'ID de la zone maisonganopa.com
MAISON_ZONE_ID=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='maisonganopa.com.'].Id" --output text | awk -F'/' '{print $NF}')

# Créer un fichier JSON pour l'enregistrement
cat > /tmp/arquantix-record.json <<EOF
{
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "arquantix.maisonganopa.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z2FDTNDATAQYW2",
          "DNSName": "d2gtzmv0zk47i6.cloudfront.net",
          "EvaluateTargetHealth": false
        }
      }
    }
  ]
}
EOF

# Créer l'enregistrement
aws route53 change-resource-record-sets \
  --hosted-zone-id $MAISON_ZONE_ID \
  --change-batch file:///tmp/arquantix-record.json
```

---

### Option B: Domaine dédié arquantix.com

**Domain:** `arquantix.com`

#### Étape 1: Créer ou utiliser une Hosted Zone

**Si la zone n'existe pas:**

1. **Ouvrir Route53 Console:**
   https://console.aws.amazon.com/route53/v2/hostedzones

2. **Créer une hosted zone:**
   - Cliquer sur "Create hosted zone"
   - **Domain name:** `arquantix.com`
   - **Type:** Public hosted zone
   - Cliquer sur "Create hosted zone"

3. **Noter les nameservers:**
   - Route53 fournira 4 nameservers (ex: `ns-123.awsdns-12.com`)
   - **Important:** Vous devrez mettre à jour ces nameservers chez votre registrar de domaine

**Si la zone existe déjà:**
- Utiliser la zone existante
- Vérifier les enregistrements existants

#### Étape 2: Mettre à jour les Nameservers (si nouvelle zone)

1. **Aller chez votre registrar de domaine** (ex: GoDaddy, Namecheap, etc.)
2. **Trouver la section DNS / Nameservers**
3. **Remplacer les nameservers** par ceux fournis par Route53
4. **Attendre la propagation** (peut prendre jusqu'à 48h, généralement moins)

#### Étape 3: Créer l'enregistrement A (Alias)

1. **Dans Route53, ouvrir la zone `arquantix.com`**

2. **Créer un enregistrement:**
   - Cliquer sur "Create record"
   - **Record name:** (laisser vide pour la racine, ou `www` pour www.arquantix.com)
   - **Record type:** A
   - **Alias:** Yes
   - **Route traffic to:** Alias to CloudFront distribution
   - **Choose distribution:** Sélectionner `EPJ3WQCO04UWW` (ou chercher "Arquantix Coming Soon")
   - **Evaluate target health:** No
   - Cliquer sur "Create records"

3. **Si vous voulez aussi www.arquantix.com:**
   - Créer un autre enregistrement avec **Record name:** `www`
   - Pointer vers la même distribution CloudFront

#### Via AWS CLI (avec permissions)

```bash
# Si la zone n'existe pas, créer la hosted zone
aws route53 create-hosted-zone \
  --name arquantix.com \
  --caller-reference arquantix-$(date +%s)

# Obtenir l'ID de la zone
ARQUANTIX_ZONE_ID=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='arquantix.com.'].Id" --output text | awk -F'/' '{print $NF}')

# Obtenir les nameservers
aws route53 get-hosted-zone --id $ARQUANTIX_ZONE_ID --query 'DelegationSet.NameServers' --output text

# Créer l'enregistrement A (racine)
cat > /tmp/arquantix-root-record.json <<EOF
{
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "arquantix.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z2FDTNDATAQYW2",
          "DNSName": "d2gtzmv0zk47i6.cloudfront.net",
          "EvaluateTargetHealth": false
        }
      }
    }
  ]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id $ARQUANTIX_ZONE_ID \
  --change-batch file:///tmp/arquantix-root-record.json
```

---

## 🔐 Mettre à jour CloudFront avec le Domain

Une fois Route53 configuré, mettre à jour CloudFront:

### Via AWS Console

1. **Ouvrir CloudFront Console:**
   https://console.aws.amazon.com/cloudfront/v3/home#/distributions/EPJ3WQCO04UWW

2. **Onglet "General"** → **"Edit"**

3. **Alternate domain names (CNAMEs):**
   - Ajouter: `arquantix.maisonganopa.com` (Option A)
   - Ou: `arquantix.com` et `www.arquantix.com` (Option B)

4. **Custom SSL certificate:**
   - Sélectionner un certificat ACM (créer si nécessaire)
   - Pour `arquantix.maisonganopa.com`: Utiliser un certificat wildcard `*.maisonganopa.com` si disponible
   - Pour `arquantix.com`: Utiliser un certificat pour `arquantix.com` ou wildcard `*.arquantix.com`
   - **Note:** Le certificat doit être dans la région `us-east-1` pour CloudFront

5. **Cliquer sur "Save changes"**

6. **Attendre la mise à jour** (5-10 minutes)

### Créer un certificat ACM (si nécessaire)

1. **Ouvrir ACM Console:**
   https://console.aws.amazon.com/acm/home?region=us-east-1

2. **Request a certificate:**
   - **Domain names:**
     - Pour Option A: `arquantix.maisonganopa.com`
     - Pour Option B: `arquantix.com` et `www.arquantix.com`
   - **Validation method:** DNS validation (recommandé)
   - Cliquer sur "Request"

3. **Valider le certificat:**
   - ACM fournira des enregistrements CNAME à ajouter dans Route53
   - Ajouter ces enregistrements dans la hosted zone appropriée
   - Attendre la validation (généralement quelques minutes)

---

## ✅ Checklist de Configuration

- [ ] Vérifier les hosted zones existantes (arquantix.com, maisonganopa.com)
- [ ] Vérifier les enregistrements existants pour "arquantix"
- [ ] Décider: Option A (sous-domaine) ou Option B (domaine dédié)
- [ ] Créer/modifier l'enregistrement Route53
- [ ] (Option B uniquement) Mettre à jour les nameservers chez le registrar
- [ ] Créer/modifier le certificat ACM si nécessaire
- [ ] Mettre à jour CloudFront avec CNAME et certificat SSL
- [ ] Tester l'accès via le domaine
- [ ] Vérifier le statut CloudFront (doit être "Deployed")

---

## 🔍 Vérification

### Tester le domaine (après configuration)

```bash
# Tester avec curl
curl -I https://arquantix.maisonganopa.com
# ou
curl -I https://arquantix.com

# Vérifier la résolution DNS
dig arquantix.maisonganopa.com
# ou
dig arquantix.com
```

### Vérifier le statut CloudFront

```bash
aws cloudfront get-distribution --id EPJ3WQCO04UWW --query 'Distribution.Status' --output text
```

Doit être `Deployed` (pas `InProgress`)

---

## 📝 Informations CloudFront pour Route53

**Distribution ID:** `EPJ3WQCO04UWW`  
**CloudFront Domain:** `d2gtzmv0zk47i6.cloudfront.net`  
**CloudFront Hosted Zone ID:** `Z2FDTNDATAQYW2` (constante pour toutes les distributions CloudFront)

**Statut actuel:** `InProgress` (déploiement en cours, ~15-20 minutes)

---

**Dernière mise à jour:** 2026-01-01


