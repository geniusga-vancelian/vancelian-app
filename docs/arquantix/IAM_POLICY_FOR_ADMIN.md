# Politique IAM à Attacher - ACM + ALB HTTPS

**Destinataire:** Admin AWS  
**Date:** 2026-01-03  
**Objectif:** Permissions minimales pour créer un certificat ACM, le valider via Route53, et l'attacher à un listener HTTPS sur l'ALB.

---

## Politique IAM JSON

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

## Instructions pour l'Admin AWS

### Option 1: Politique Inline (Recommandé pour test)

1. **IAM Console** → **Users** → Sélectionner `cursor-admin` (ou l'utilisateur concerné)
2. **Onglet "Permissions"**
3. **Cliquer sur "Add permissions"** → **"Create inline policy"**
4. **Onglet "JSON"**
5. **Coller la politique JSON ci-dessus**
6. **Cliquer sur "Review policy"**
7. **Nom:** `ACM-ALB-HTTPS-Policy`
8. **Cliquer sur "Create policy"**

### Option 2: Politique Gérée (Recommandé pour production)

1. **IAM Console** → **Policies** → **"Create policy"**
2. **Onglet "JSON"**
3. **Coller la politique JSON ci-dessus**
4. **Cliquer sur "Next"**
5. **Nom:** `ACM-ALB-HTTPS-Policy`
6. **Description:** "Minimal permissions for ACM certificate creation (me-central-1) and ALB HTTPS listener (arquantix-prod-alb)"
7. **Cliquer sur "Create policy"**
8. **Attacher à l'utilisateur:**
   - **IAM** → **Users** → `cursor-admin`
   - **Add permissions** → **Attach policies directly**
   - Rechercher `ACM-ALB-HTTPS-Policy`
   - Cocher et **Add permissions**

---

## Détails des Permissions

### ACM (Certificate Manager)
- **Région:** `me-central-1` uniquement (condition)
- **Actions:** Créer, lister, décrire, tagger, supprimer des certificats
- **Ressources:** Tous les certificats (restriction par région)

### Route53
- **Zone:** `arquantix.com` (Z08819812KDG05NSYVRFJ)
- **Actions:** Créer/modifier des records DNS (pour validation ACM)
- **Ressources:** Zone hosted spécifique uniquement

### Elastic Load Balancing (ALB)
- **ALB:** `arquantix-prod-alb` uniquement
- **Target Group:** `arquantix-prod-tg` uniquement
- **Actions:** Créer/modifier des listeners, décrire les ressources
- **Ressources:** ARNs spécifiques (pas d'accès à d'autres ALBs)

---

## Vérification Post-Attachement

```bash
# Tester les permissions ACM
aws acm list-certificates --region me-central-1

# Tester les permissions Route53
aws route53 list-hosted-zones

# Tester les permissions ALB
aws elbv2 describe-load-balancers --region me-central-1 \
  --query 'LoadBalancers[?contains(LoadBalancerName, `arquantix`)]'
```

---

## Contact

En cas de question ou problème, contacter l'équipe DevOps.

---

**Note:** Cette politique suit le principe du "least privilege" - permissions minimales nécessaires pour la tâche spécifique.

