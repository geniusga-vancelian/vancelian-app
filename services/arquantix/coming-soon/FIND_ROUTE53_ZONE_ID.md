# Trouver l'ID de la Zone Route53

**Objectif:** Trouver l'ID de la hosted zone pour affiner la policy Route53

---

## Méthode 1: Via AWS Console (Plus Simple)

1. **Ouvrir Route53 Console:**
   https://console.aws.amazon.com/route53/v2/hostedzones

2. **Trouver la zone:**
   - Si vous voulez utiliser `arquantix.maisonganopa.com`, chercher la zone `maisonganopa.com`
   - Si vous voulez utiliser `arquantix.com`, chercher la zone `arquantix.com`

3. **Cliquer sur la zone**

4. **L'ID de la zone est visible:**
   - Dans l'URL: `/hostedzone/Z123456789ABC`
   - Ou dans les détails de la zone
   - L'ID commence par `Z` suivi d'une série de caractères alphanumériques

**Exemple d'ID:** `Z1D633PJN98FT9`

---

## Méthode 2: Via AWS CLI (Après avoir ajouté les permissions read-only)

### Étape 1: Ajouter d'abord la policy avec Resource "*" (temporaire)

Ajoutez cette policy temporaire pour permettre de lister les zones:

**Fichier:** `route53-policy-step1.json` (déjà créé)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Route53ReadOnly",
      "Effect": "Allow",
      "Action": [
        "route53:ListHostedZones",
        "route53:ListHostedZonesByName",
        "route53:GetHostedZone",
        "route53:ListResourceRecordSets"
      ],
      "Resource": "*"
    },
    {
      "Sid": "Route53ChangeRecordsTemporary",
      "Effect": "Allow",
      "Action": [
        "route53:ChangeResourceRecordSets"
      ],
      "Resource": "*"
    }
  ]
}
```

**Note:** La partie `ChangeResourceRecordSets` avec `Resource: "*"` est temporaire, juste pour permettre de trouver l'ID. Une fois l'ID trouvé, on affinera la policy.

### Étape 2: Lister les zones pour trouver l'ID

Après avoir ajouté la policy ci-dessus, exécutez:

```bash
# Lister toutes les zones
aws route53 list-hosted-zones --query 'HostedZones[*].{Name:Name,Id:Id}' --output table

# Chercher spécifiquement maisonganopa.com
aws route53 list-hosted-zones --query "HostedZones[?Name=='maisonganopa.com.'].{Name:Name,Id:Id}" --output json

# Chercher spécifiquement arquantix.com
aws route53 list-hosted-zones --query "HostedZones[?Name=='arquantix.com.'].{Name:Name,Id:Id}" --output json
```

L'ID sera au format: `/hostedzone/Z123456789ABC`

**Important:** Utilisez seulement la partie après `/hostedzone/` (ex: `Z123456789ABC`)

### Étape 3: Créer la policy finale avec l'ID spécifique

Une fois l'ID trouvé, créez la policy finale:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Route53ReadOnly",
      "Effect": "Allow",
      "Action": [
        "route53:ListHostedZones",
        "route53:ListHostedZonesByName",
        "route53:GetHostedZone",
        "route53:ListResourceRecordSets"
      ],
      "Resource": "*"
    },
    {
      "Sid": "Route53ChangeRecords",
      "Effect": "Allow",
      "Action": [
        "route53:ChangeResourceRecordSets"
      ],
      "Resource": "arn:aws:route53:::hostedzone/Z123456789ABC"
    }
  ]
}
```

Remplacer `Z123456789ABC` par l'ID réel trouvé.

---

## Script Automatique

Une fois la policy temporaire ajoutée, vous pouvez exécuter:

```bash
# Chercher la zone maisonganopa.com
ZONE_ID=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='maisonganopa.com.'].Id" --output text | awk -F'/' '{print $NF}')

if [ -n "$ZONE_ID" ]; then
  echo "Zone maisonganopa.com trouvée:"
  echo "ID complet: /hostedzone/$ZONE_ID"
  echo "ID pour policy: $ZONE_ID"
  echo ""
  echo "ARN pour policy: arn:aws:route53:::hostedzone/$ZONE_ID"
else
  echo "Zone maisonganopa.com non trouvée"
fi

# Chercher la zone arquantix.com
ZONE_ID=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='arquantix.com.'].Id" --output text | awk -F'/' '{print $NF}')

if [ -n "$ZONE_ID" ]; then
  echo "Zone arquantix.com trouvée:"
  echo "ID complet: /hostedzone/$ZONE_ID"
  echo "ID pour policy: $ZONE_ID"
  echo ""
  echo "ARN pour policy: arn:aws:route53:::hostedzone/$ZONE_ID"
else
  echo "Zone arquantix.com non trouvée"
fi
```

---

## Résumé

1. **Ajouter d'abord la policy temporaire** (`route53-policy-step1.json`) avec `Resource: "*"` pour ChangeResourceRecordSets
2. **Lister les zones** pour trouver l'ID
3. **Créer la policy finale** avec l'ID spécifique trouvé
4. **Remplacer la policy temporaire** par la policy finale

---

**Note:** Si vous préférez, vous pouvez aussi utiliser la console AWS pour trouver l'ID directement, sans ajouter de policy temporaire.


