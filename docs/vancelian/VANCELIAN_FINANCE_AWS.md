# vancelian.finance — infrastructure AWS

**Compte:** `411714852748` (utilisateur `cursor-admin`)  
**Région principale:** `us-east-1`  
**Date de mise en place:** 2026-05-20  
**Mise à jour staging privé:** 2026-05-21

## Domaine

| Élément | Valeur |
|--------|--------|
| Domaine | `vancelian.finance` |
| Enregistrement | Route53 Domains (~65 USD/an, auto-renew) |
| Zone Route53 | `Z091663116M960F99DPZB` |
| Expiration | 2027-05-20 |

## Surfaces (staging privé)

| Host | Service ECS | Target group | Visibilité |
|------|-------------|--------------|------------|
| `vancelian.finance`, `www` | `vancelian-web` (nginx coming-soon) | `vancelian-web-tg:80` | Public |
| `app.vancelian.finance` | `vancelian-next` (Next.js) | `vancelian-next-tg:3000` | WAF IP allowlist |
| `console.vancelian.finance` | `vancelian-next` (Next.js, `/admin/*`) | `vancelian-next-tg:3000` | WAF IP allowlist |

Script de déploiement : `./scripts/vancelian-finance-private-launch.sh`  
Workflow CI : `.github/workflows/vancelian-next-deploy.yml`

## Certificats ACM (us-east-1)

| Usage | ARN |
|-------|-----|
| CloudFront (`vancelian.finance`, `www`) | `arn:aws:acm:us-east-1:411714852748:certificate/46e5eb24-35ef-4a8e-a7fa-1f1c0a68ca66` |
| ALB (`*.vancelian.finance`) | `arn:aws:acm:us-east-1:411714852748:certificate/dd9243fd-5bfa-4c04-90da-219546f4c650` |

Validation DNS : enregistrements CNAME `_618148f90…` et `_f1a7e672…` dans la zone.

## Compute (miroir arquantix.com)

| Ressource | Détail |
|-----------|--------|
| ECS cluster | `arquantix-cluster` (partagé) |
| ECS service | `vancelian-web` |
| Task definition | `vancelian-web:1` (nginx coming-soon, port 80) |
| ECR | `411714852748.dkr.ecr.us-east-1.amazonaws.com/vancelian-web` |
| Image placeholder | `coming-soon` / `latest` |
| Logs | `/ecs/vancelian-web` |

## Load balancer

| Ressource | Détail |
|-----------|--------|
| ALB | `vancelian-alb` |
| DNS | `vancelian-alb-1936234667.us-east-1.elb.amazonaws.com` |
| Target group | `vancelian-web-tg` (HTTP:80, health `/`) |
| Listener | HTTP:80 → forward (HTTPS à ajouter via script finish) |

## DNS actuel (Route53)

- `vancelian.finance` → ALB (alias)
- `www.vancelian.finance` → ALB (alias)
- CNAME validation ACM

**Après certificats ISSUED :** exécuter `scripts/vancelian-finance-finish-ssl.sh` pour HTTPS ALB + CloudFront + bascule DNS vers CloudFront (comme `arquantix.com`).

## Prochaines étapes produit

1. Remplacer l’image `coming-soon` par une app Next.js vitrine (complexité comparable à `services/arquantix/web`).
2. Ajouter workflow GitHub `vancelian-web-deploy.yml` (ECR + ECS), calqué sur `.github/workflows/arquantix-web-deploy.yml`.
3. Sous-domaines futurs : `api.vancelian.finance` → règle ALB host (comme `api.arquantix.com`).

## Commandes utiles

```bash
# Déploiement / mise à jour infra + ECS
./scripts/vancelian-finance-private-launch.sh

# Ajouter une IP à la allowlist WAF (app + console) — fusionne sans écraser les IPs existantes
./scripts/vancelian-waf-add-ip.sh 176.204.158.33

# Alternative (remplace toute la liste — attention) :
# VANCELIAN_WAF_ALLOW_CIDRS="91.73.77.140/32,VOTRE_IP/32" ./scripts/vancelian-finance-private-launch.sh

# Secrets Privy API (ECS arquantix-api)
./scripts/arquantix-sync-privy-secrets.sh

# Statut certificats
aws acm describe-certificate --region us-east-1 \
  --certificate-arn arn:aws:acm:us-east-1:411714852748:certificate/46e5eb24-35ef-4a8e-a7fa-1f1c0a68ca66 \
  --query 'Certificate.Status'

# Finaliser HTTPS + CloudFront
./scripts/vancelian-finance-finish-ssl.sh

# Tester l’ALB (en attendant le DNS public)
curl -sI -H 'Host: vancelian.finance' http://vancelian-alb-1936234667.us-east-1.elb.amazonaws.com/
```
