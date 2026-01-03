# Plan de Rollback - Arquantix

**Date:** 2026-01-03  
**Objectif:** Procédure de rollback en cas de problème après déploiement

---

## 🔄 Rollback ECS Task Definition

### Option 1: Rollback vers révision précédente

```bash
# 1. Lister les révisions disponibles
aws ecs list-task-definitions \
  --family-prefix arquantix-coming-soon \
  --region me-central-1 \
  --sort DESC \
  --max-items 10

# 2. Identifier la dernière révision stable (ex: revision 1)
LAST_STABLE_REVISION="1"

# 3. Mettre à jour le service avec l'ancienne révision
aws ecs update-service \
  --cluster arquantix-cluster \
  --service arquantix-coming-soon \
  --task-definition arquantix-coming-soon:$LAST_STABLE_REVISION \
  --region me-central-1 \
  --force-new-deployment

# 4. Vérifier le déploiement
aws ecs describe-services \
  --cluster arquantix-cluster \
  --services arquantix-coming-soon \
  --region me-central-1 \
  --query 'services[0].deployments'
```

### Option 2: Rollback via Git + Rebuild

```bash
# 1. Identifier le dernier commit stable
git log --oneline -10

# 2. Revert le commit problématique
git revert <commit-hash>

# 3. Push sur main (déclenchera automatiquement le rebuild)
git push origin main

# 4. Attendre le déploiement (5-10 min)
```

---

## 🔄 Rollback CloudFront

Si CloudFront cause des problèmes :

```bash
# 1. Vérifier la configuration actuelle
aws cloudfront get-distribution-config \
  --id EPJ3WQCO04UWW \
  --output json > current-config.json

# 2. Restaurer une configuration précédente si sauvegardée
# (Sinon, modifier manuellement dans la console AWS)

# 3. Invalider le cache
aws cloudfront create-invalidation \
  --distribution-id EPJ3WQCO04UWW \
  --paths "/*"
```

---

## 🔄 Rollback Target Group Health Check

Si le health check cause des problèmes :

```bash
# Remettre le health check sur /fr (qui fonctionnait avant)
TG_ARN="arn:aws:elasticloadbalancing:me-central-1:411714852748:targetgroup/arquantix-prod-tg/89fe413e994d9f0f"

aws elbv2 modify-target-group \
  --target-group-arn $TG_ARN \
  --health-check-path /fr \
  --region me-central-1
```

---

## 🔄 Rollback DNS (Route53)

Si DNS cause des problèmes :

```bash
# 1. Vérifier les records actuels
ZONE_ID="Z08819812KDG05NSYVRFJ"
aws route53 list-resource-record-sets \
  --hosted-zone-id $ZONE_ID \
  --query "ResourceRecordSets[?contains(Name, 'arquantix.com')]"

# 2. Modifier les records si nécessaire
# (Utiliser la console AWS ou aws route53 change-resource-record-sets)
```

---

## 📋 Checklist de Rollback

Avant de rollback :

- [ ] Identifier la cause du problème
- [ ] Vérifier les logs ECS
- [ ] Vérifier les logs CloudFront
- [ ] Vérifier le health check du Target Group
- [ ] Documenter ce qui a causé le problème

Pendant le rollback :

- [ ] Exécuter la commande de rollback
- [ ] Vérifier que le service se met à jour
- [ ] Attendre que le déploiement se termine
- [ ] Vérifier le health check

Après le rollback :

- [ ] Tester les endpoints critiques
- [ ] Vérifier que le site fonctionne
- [ ] Documenter le rollback
- [ ] Analyser la cause racine pour éviter la récurrence

---

## 🚨 Rollback d'Urgence

Si le site est complètement down :

1. **Rollback ECS immédiat:**
   ```bash
   aws ecs update-service \
     --cluster arquantix-cluster \
     --service arquantix-coming-soon \
     --task-definition arquantix-coming-soon:1 \
     --region me-central-1 \
     --force-new-deployment
   ```

2. **Vérifier le health check:**
   ```bash
   aws elbv2 describe-target-health \
     --target-group-arn arn:aws:elasticloadbalancing:me-central-1:411714852748:targetgroup/arquantix-prod-tg/89fe413e994d9f0f \
     --region me-central-1
   ```

3. **Si nécessaire, remettre health check sur /fr:**
   ```bash
   aws elbv2 modify-target-group \
     --target-group-arn arn:aws:elasticloadbalancing:me-central-1:411714852748:targetgroup/arquantix-prod-tg/89fe413e994d9f0f \
     --health-check-path /fr \
     --region me-central-1
   ```

---

## 📝 Historique des Rollbacks

| Date | Cause | Action | Résultat |
|------|-------|--------|----------|
| 2026-01-03 | Serveur ne répond pas (standalone) | Revert vers next start | En attente |

---

**Dernière mise à jour:** 2026-01-03

