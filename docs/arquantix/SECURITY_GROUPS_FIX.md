# Fix Security Groups - ALB → ECS

**Date:** 2026-01-03  
**Problème:** Health check ALB échoue, site inaccessible (502/504)

---

## 🔍 Diagnostic

### Security Groups Identifiés

1. **ALB Security Group**
   - ID: À récupérer depuis l'ALB
   - Rôle: Autoriser le trafic entrant (HTTP/HTTPS depuis Internet)

2. **ECS Security Group**
   - ID: À récupérer depuis le service ECS
   - Rôle: Autoriser le trafic depuis l'ALB vers les containers ECS

### Problème Identifié

Le Security Group ECS doit autoriser le trafic **INBOUND** sur le port **3000** depuis le Security Group de l'ALB.

Si cette règle manque, le health check ALB échouera car le trafic sera bloqué.

---

## ✅ Solution

### Commande pour Ajouter la Règle

```bash
# Récupérer les Security Groups
ALB_SG=$(aws elbv2 describe-load-balancers \
  --region me-central-1 \
  --query 'LoadBalancers[?contains(LoadBalancerName, `arquantix`)].SecurityGroups[0]' \
  --output text)

ECS_SG=$(aws ecs describe-services \
  --cluster arquantix-cluster \
  --services arquantix-coming-soon \
  --region me-central-1 \
  --query 'services[0].networkConfiguration.awsvpcConfiguration.securityGroups[0]' \
  --output text)

# Ajouter la règle INBOUND
aws ec2 authorize-security-group-ingress \
  --group-id $ECS_SG \
  --protocol tcp \
  --port 3000 \
  --source-group $ALB_SG \
  --region me-central-1
```

### Vérification

```bash
# Vérifier que la règle existe
aws ec2 describe-security-groups \
  --group-ids $ECS_SG \
  --region me-central-1 \
  --query 'SecurityGroups[0].IpPermissions[?FromPort==`3000` && ToPort==`3000`]'
```

---

## 📋 Règles Requises

### Security Group ECS - INBOUND

| Type | Protocol | Port | Source | Description |
|------|----------|------|--------|-------------|
| Custom TCP | TCP | 3000 | ALB Security Group | Autoriser le trafic depuis l'ALB |

### Security Group ALB - INBOUND

| Type | Protocol | Port | Source | Description |
|------|----------|------|--------|-------------|
| HTTP | TCP | 80 | 0.0.0.0/0 | Trafic HTTP depuis Internet |
| HTTPS | TCP | 443 | 0.0.0.0/0 | Trafic HTTPS depuis Internet |

### Security Group ALB - OUTBOUND

| Type | Protocol | Port | Source | Description |
|------|----------|------|--------|-------------|
| All traffic | All | All | 0.0.0.0/0 | Autoriser tout le trafic sortant |

### Security Group ECS - OUTBOUND

| Type | Protocol | Port | Source | Description |
|------|----------|------|--------|-------------|
| All traffic | All | All | 0.0.0.0/0 | Autoriser tout le trafic sortant (pour logs, etc.) |

---

## 🔧 Après Correction

1. **Attendre 10-30 secondes** pour que la règle soit appliquée
2. **Vérifier la santé des targets ALB:**
   ```bash
   aws elbv2 describe-target-health \
     --target-group-arn <TARGET_GROUP_ARN> \
     --region me-central-1
   ```
3. **Tester le health check:**
   ```bash
   curl -I https://arquantix.com/health
   ```
4. **Tester le site:**
   ```bash
   curl -I https://arquantix.com/
   ```

---

## ⚠️ Notes Importantes

- La règle doit être ajoutée sur le **Security Group ECS**, pas sur l'ALB
- Le port doit correspondre au port du container (3000)
- La source doit être le **Security Group ID de l'ALB**, pas une IP
- Les changements de security groups sont appliqués immédiatement

---

**Dernière mise à jour:** 2026-01-03

