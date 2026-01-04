# IAM Policy - ACM Certificate + ALB HTTPS Listener

**Objectif:** Permissions minimales pour créer un certificat ACM, le valider via Route53 DNS, et l'attacher à un listener HTTPS sur l'ALB.

---

## 1. Politique IAM JSON (Least Privilege)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ACM Certificate Management",
      "Effect": "Allow",
      "Action": [
        "acm:RequestCertificate",
        "acm:DescribeCertificate",
        "acm:ListCertificates",
        "acm:AddTagsToCertificate",
        "acm:DeleteCertificate"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "me-central-1"
        }
      }
    },
    {
      "Sid": "Route53 DNS Validation",
      "Effect": "Allow",
      "Action": [
        "route53:ChangeResourceRecordSets",
        "route53:ListHostedZones",
        "route53:ListResourceRecordSets",
        "route53:GetChange"
      ],
      "Resource": [
        "arn:aws:route53:::hostedzone/*",
        "arn:aws:route53:::change/*"
      ]
    },
    {
      "Sid": "ALB Listener Management",
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:CreateListener",
        "elasticloadbalancing:ModifyListener",
        "elasticloadbalancing:DescribeListeners",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups"
      ],
      "Resource": [
        "arn:aws:elasticloadbalancing:me-central-1:*:loadbalancer/app/arquantix-prod-alb/*",
        "arn:aws:elasticloadbalancing:me-central-1:*:listener/app/arquantix-prod-alb/*/*",
        "arn:aws:elasticloadbalancing:me-central-1:*:targetgroup/arquantix-prod-tg/*"
      ]
    }
  ]
}
```

### Version Alternative (Plus Restrictive - Si vous connaissez les ARNs exacts)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ACM Certificate Management",
      "Effect": "Allow",
      "Action": [
        "acm:RequestCertificate",
        "acm:DescribeCertificate",
        "acm:ListCertificates",
        "acm:AddTagsToCertificate",
        "acm:DeleteCertificate"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "me-central-1"
        }
      }
    },
    {
      "Sid": "Route53 DNS Validation",
      "Effect": "Allow",
      "Action": [
        "route53:ChangeResourceRecordSets",
        "route53:ListHostedZones",
        "route53:ListResourceRecordSets",
        "route53:GetChange"
      ],
      "Resource": [
        "arn:aws:route53:::hostedzone/Z08819812KDG05NSYVRFJ",
        "arn:aws:route53:::change/*"
      ]
    },
    {
      "Sid": "ALB Listener Management",
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:CreateListener",
        "elasticloadbalancing:ModifyListener",
        "elasticloadbalancing:DescribeListeners",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups"
      ],
      "Resource": [
        "arn:aws:elasticloadbalancing:me-central-1:411714852748:loadbalancer/app/arquantix-prod-alb/*",
        "arn:aws:elasticloadbalancing:me-central-1:411714852748:listener/app/arquantix-prod-alb/*/*",
        "arn:aws:elasticloadbalancing:me-central-1:411714852748:targetgroup/arquantix-prod-tg/*"
      ]
    }
  ]
}
```

---

## 2. Guide Console AWS - Étape par Étape

### Étape 1: Créer le Certificat ACM

1. **Ouvrir AWS Console** → **Certificate Manager (ACM)**
2. **Sélectionner la région:** `me-central-1` (Dubai)
3. **Cliquer sur "Request a certificate"**
4. **Choisir "Request a public certificate"**
5. **Domain names:**
   - Domain name: `arquantix.com`
   - Additional names: `www.arquantix.com`
6. **Validation method:** Sélectionner **DNS validation**
7. **Tags (optionnel):** Ajouter des tags si nécessaire
8. **Cliquer sur "Request"**

### Étape 2: Valider le Certificat via Route53

1. **Dans ACM**, le certificat apparaît avec le statut **"Pending validation"**
2. **Cliquer sur le certificat** pour voir les détails
3. **Section "Domains"**, vous verrez les **CNAME records** à créer:
   - `_abc123.arquantix.com` → `_xyz789.acm-validations.aws.`
   - `_def456.www.arquantix.com` → `_uvw012.acm-validations.aws.`
4. **Ouvrir un nouvel onglet** → **Route53**
5. **Hosted zones** → **arquantix.com**
6. **Cliquer sur "Create record"**
7. **Pour chaque CNAME:**
   - **Record name:** Copier depuis ACM (ex: `_abc123`)
   - **Record type:** `CNAME`
   - **Value:** Copier depuis ACM (ex: `_xyz789.acm-validations.aws.`)
   - **TTL:** `300` (ou laisser par défaut)
   - **Cliquer sur "Create records"**
8. **Répéter pour le deuxième CNAME** (www.arquantix.com)
9. **Retourner à ACM** → **Actualiser la page**
10. **Attendre 5-30 minutes** pour la validation automatique
11. **Le statut passe à "Issued"** une fois validé

### Étape 3: Créer le Listener HTTPS (443) sur l'ALB

1. **Ouvrir AWS Console** → **EC2** → **Load Balancers**
2. **Sélectionner:** `arquantix-prod-alb`
3. **Onglet "Listeners"**
4. **Cliquer sur "Add listener"**
5. **Configuration:**
   - **Protocol:** `HTTPS`
   - **Port:** `443`
   - **Default action:** `Forward to target group`
   - **Target group:** `arquantix-prod-tg`
6. **Default SSL certificate:**
   - **From ACM (recommended)**
   - **Certificate:** Sélectionner le certificat `arquantix.com` (celui créé à l'étape 1)
   - **Note:** Le certificat doit être dans la région `me-central-1`
7. **Cliquer sur "Add"**
8. **Attendre quelques secondes** → Le listener apparaît dans la liste

### Étape 4: Modifier le Listener HTTP (80) pour Redirect

1. **Dans la même page ALB** → **Onglet "Listeners"**
2. **Trouver le listener sur le port 80**
3. **Cliquer sur "Edit"** (icône crayon)
4. **Default action:** Changer de "Forward to" à **"Redirect to URL"**
5. **Redirect to:**
   - **Protocol:** `HTTPS`
   - **Port:** `443`
   - **Status code:** `301 - Permanently moved`
6. **Cliquer sur "Save changes"**

---

## 3. Étapes de Vérification

### Vérification 1: Certificat ACM Validé

```bash
# Via AWS CLI
aws acm list-certificates \
  --region me-central-1 \
  --query 'CertificateSummaryList[?contains(DomainName, `arquantix`)].{Domain:DomainName,Status:Status,Arn:CertificateArn}' \
  --output table

# Attendu:
# Domain: arquantix.com
# Status: ISSUED
```

**Via Console:**
1. **ACM** → **Certificates**
2. **Vérifier que le certificat `arquantix.com` a le statut "Issued"** (badge vert)

### Vérification 2: Listener 443 Créé

```bash
# Via AWS CLI
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --region me-central-1 \
  --query 'LoadBalancers[?contains(LoadBalancerName, `arquantix`)].LoadBalancerArn' \
  --output text)

aws elbv2 describe-listeners \
  --load-balancer-arn "$ALB_ARN" \
  --region me-central-1 \
  --query 'Listeners[*].{Port:Port,Protocol:Protocol,Certificate:Certificates[0].CertificateArn}' \
  --output table

# Attendu:
# Port: 443
# Protocol: HTTPS
# Certificate: arn:aws:acm:me-central-1:...:certificate/...
```

**Via Console:**
1. **EC2** → **Load Balancers** → **arquantix-prod-alb**
2. **Onglet "Listeners"**
3. **Vérifier qu'il y a un listener sur le port 443 avec protocol HTTPS**

### Vérification 3: Listener 80 Redirect

```bash
# Via AWS CLI
LISTENER_80=$(aws elbv2 describe-listeners \
  --load-balancer-arn "$ALB_ARN" \
  --region me-central-1 \
  --query 'Listeners[?Port==`80`].ListenerArn' \
  --output text)

aws elbv2 describe-listeners \
  --listener-arns "$LISTENER_80" \
  --region me-central-1 \
  --query 'Listeners[0].DefaultActions[0].{Type:Type,Protocol:RedirectConfig.Protocol,Port:RedirectConfig.Port,StatusCode:RedirectConfig.StatusCode}' \
  --output json

# Attendu:
# Type: redirect
# Protocol: HTTPS
# Port: 443
# StatusCode: HTTP_301
```

**Via Console:**
1. **EC2** → **Load Balancers** → **arquantix-prod-alb**
2. **Onglet "Listeners"**
3. **Listener port 80** → **Vérifier que l'action est "Redirect to URL"** (HTTPS, port 443, 301)

### Vérification 4: Test End-to-End

```bash
# Test via CloudFront
curl -I https://arquantix.com/health

# Attendu: HTTP/2 200 (ou 301 si redirect, puis 200)

# Test direct ALB (avec Host header)
ALB_DNS="arquantix-prod-alb-1651887598.me-central-1.elb.amazonaws.com"
curl -I -k -H "Host: arquantix.com" "https://$ALB_DNS/health"

# Attendu: HTTP/1.1 200
```

**Via Navigateur:**
1. **Ouvrir:** `https://arquantix.com/health`
2. **Vérifier:**
   - Pas d'erreur SSL
   - Statut 200 OK
   - Le certificat est valide (cadenas vert dans le navigateur)

### Vérification 5: CloudFront Origin Protocol

```bash
# Vérifier que CloudFront utilise HTTPS vers l'ALB
aws cloudfront get-distribution-config \
  --id EPJ3WQCO04UWW \
  --region me-central-1 \
  --query 'DistributionConfig.Origins.Items[0].CustomOriginConfig.OriginProtocolPolicy' \
  --output text

# Attendu: https-only
```

**Si ce n'est pas "https-only":**
1. **CloudFront** → **Distributions** → **EPJ3WQCO04UWW**
2. **Onglet "Origins"**
3. **Cliquer sur l'origin** → **Edit**
4. **Origin protocol policy:** Changer en **"HTTPS Only"**
5. **Save changes**

---

## 4. Application de la Politique IAM

### Option A: Attacher à un Utilisateur IAM

1. **IAM Console** → **Users** → Sélectionner l'utilisateur (ex: `cursor-admin`)
2. **Onglet "Permissions"**
3. **Cliquer sur "Add permissions"** → **"Create inline policy"**
4. **Onglet "JSON"**
5. **Coller la politique JSON** (section 1)
6. **Cliquer sur "Review policy"**
7. **Nom:** `ACM-ALB-HTTPS-Policy`
8. **Cliquer sur "Create policy"**

### Option B: Créer une Politique Gérée

1. **IAM Console** → **Policies** → **"Create policy"**
2. **Onglet "JSON"**
3. **Coller la politique JSON** (section 1)
4. **Cliquer sur "Next"**
5. **Nom:** `ACM-ALB-HTTPS-Policy`
6. **Description:** "Minimal permissions for ACM certificate creation and ALB HTTPS listener"
7. **Cliquer sur "Create policy"**
8. **Attacher à l'utilisateur/rôle:**
   - **IAM** → **Users** (ou **Roles**)
   - Sélectionner l'utilisateur/rôle
   - **Add permissions** → **Attach policies directly**
   - Rechercher `ACM-ALB-HTTPS-Policy`
   - Cocher et **Add permissions**

---

## 5. Dépannage

### Erreur: "Certificate not found in region me-central-1"
**Solution:** Vérifier que le certificat a été créé dans `me-central-1` (pas `us-east-1`)

### Erreur: "Certificate not issued"
**Solution:** Vérifier que les CNAME de validation sont créés dans Route53 et attendre 5-30 minutes

### Erreur: "AccessDenied" lors de la création du listener
**Solution:** Vérifier que la politique IAM inclut `elasticloadbalancing:CreateListener`

### Erreur: "Invalid certificate ARN"
**Solution:** Vérifier que le certificat est dans la même région que l'ALB (`me-central-1`)

---

**Dernière mise à jour:** 2026-01-03

