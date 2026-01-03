# Audit AWS - Résultats & Permissions Requises

**Date:** 2026-01-01  
**Utilisateur AWS:** `cursor-admin`  
**Région:** me-central-1  
**Account ID:** 411714852748

---

## ⚠️ Résultat de l'Audit

### Problème de Permissions

Toutes les commandes d'audit ont échoué avec des erreurs `AccessDeniedException`. L'utilisateur `cursor-admin` n'a **pas les permissions nécessaires** pour :

- ❌ `ecr:DescribeRepositories`
- ❌ `ecr:CreateRepository`
- ❌ `ecs:ListClusters`
- ❌ `ecs:ListServices`
- ❌ `ecs:DescribeServices`
- ❌ `ecs:ListTaskDefinitions`
- ❌ `elasticloadbalancing:DescribeLoadBalancers`
- ❌ `elasticloadbalancing:DescribeTargetGroups`

---

## 🔧 Solutions

### Option 1: Utiliser un Utilisateur avec Plus de Permissions

Si vous avez un autre utilisateur AWS ou un rôle avec plus de permissions, configurez-le :

```bash
# Configurer un profil AWS avec plus de permissions
aws configure --profile admin
# Entrer les credentials d'un utilisateur avec permissions admin

# Utiliser ce profil pour les commandes
export AWS_PROFILE=admin
```

### Option 2: Demander des Permissions Supplémentaires

Demander à un administrateur AWS d'ajouter les permissions suivantes à l'utilisateur `cursor-admin` :

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:*",
        "ecs:Describe*",
        "ecs:List*",
        "elasticloadbalancing:Describe*"
      ],
      "Resource": "*"
    }
  ]
}
```

### Option 3: Utiliser AWS Console

Exécuter l'audit via l'interface AWS Console :

1. **ECR:** https://console.aws.amazon.com/ecr/repositories?region=me-central-1
2. **ECS:** https://console.aws.amazon.com/ecs/v2/clusters?region=me-central-1
3. **ALB:** https://console.aws.amazon.com/ec2/v2/home?region=me-central-1#LoadBalancers:

---

## 📋 Commandes d'Audit à Exécuter (Avec Permissions)

### 1. ECR Repositories

```bash
aws ecr describe-repositories \
  --region me-central-1 \
  --query 'repositories[*].{name:repositoryName,uri:repositoryUri,created:createdAt}' \
  --output table
```

**Repositories attendus:**
- ✅ `ganopa-bot`
- ⚠️ `vancelian-api`
- ❌ `arquantix-coming-soon` (à créer)

### 2. ECS Clusters

```bash
aws ecs list-clusters \
  --region me-central-1 \
  --output json | jq -r '.clusterArns[]' | xargs -I {} aws ecs describe-clusters \
  --region me-central-1 \
  --clusters {} \
  --query 'clusters[0].{name:clusterName,status:status,registeredTasks:registeredContainerInstancesCount}' \
  --output table
```

**Clusters attendus:**
- ✅ `vancelian-dev-api-cluster`
- ⚠️ `vancelian-staging-api-cluster` (à vérifier)
- ⚠️ `vancelian-prod-api-cluster` (à vérifier)

### 3. ECS Services (DEV)

```bash
aws ecs list-services \
  --region me-central-1 \
  --cluster vancelian-dev-api-cluster \
  --output json | jq -r '.serviceArns[]' | xargs -I {} aws ecs describe-services \
  --region me-central-1 \
  --cluster vancelian-dev-api-cluster \
  --services {} \
  --query 'services[0].{name:serviceName,status:status,desired:desiredCount,running:runningCount,taskDef:taskDefinition}' \
  --output table
```

**Services attendus:**
- ✅ `ganopa-dev-bot-svc`
- ⚠️ `vancelian-dev-api-svc`

### 4. ECS Services (STAGING)

```bash
aws ecs list-services \
  --region me-central-1 \
  --cluster vancelian-staging-api-cluster \
  --output json | jq -r '.serviceArns[]' | xargs -I {} aws ecs describe-services \
  --region me-central-1 \
  --cluster vancelian-staging-api-cluster \
  --services {} \
  --query 'services[0].{name:serviceName,status:status,desired:desiredCount,running:runningCount,taskDef:taskDefinition}' \
  --output table
```

**Services attendus:**
- ⚠️ `ganopa-staging-bot-svc`
- ⚠️ `vancelian-staging-api-svc`

### 5. ECS Services (PROD)

```bash
aws ecs list-services \
  --region me-central-1 \
  --cluster vancelian-prod-api-cluster \
  --output json | jq -r '.serviceArns[]' | xargs -I {} aws ecs describe-services \
  --region me-central-1 \
  --cluster vancelian-prod-api-cluster \
  --services {} \
  --query 'services[0].{name:serviceName,status:status,desired:desiredCount,running:runningCount,taskDef:taskDefinition}' \
  --output table
```

**Services attendus:**
- ⚠️ `ganopa-prod-bot-svc`
- ⚠️ `vancelian-prod-api-svc`

### 6. ALB Load Balancers

```bash
aws elbv2 describe-load-balancers \
  --region me-central-1 \
  --query 'LoadBalancers[*].{name:LoadBalancerName,dns:DNSName,arn:LoadBalancerArn}' \
  --output table
```

### 7. Target Groups

```bash
aws elbv2 describe-target-groups \
  --region me-central-1 \
  --query 'TargetGroups[*].{name:TargetGroupName,port:Port,type:TargetType,protocol:Protocol,health:HealthCheckPath}' \
  --output table
```

**Target Groups attendus:**
- ✅ `ganopa-dev-bot-tg` (Port: 8000, Health: `/health`)
- ⚠️ `ganopa-staging-bot-tg` (à vérifier)
- ⚠️ `ganopa-prod-bot-tg` (à vérifier)

### 8. Task Definitions - Ganopa Bot

```bash
aws ecs list-task-definitions \
  --region me-central-1 \
  --family-prefix ganopa-bot \
  --query 'taskDefinitionArns[-1]' \
  --output text | xargs -I {} aws ecs describe-task-definition \
  --region me-central-1 \
  --task-definition {} \
  --query 'taskDefinition.{family:family,revision:revision,image:containerDefinitions[0].image,cpu:cpu,memory:memory}' \
  --output json | jq
```

### 9. Task Definitions - Vancelian API

```bash
aws ecs list-task-definitions \
  --region me-central-1 \
  --family-prefix vancelian-api \
  --query 'taskDefinitionArns[-1]' \
  --output text | xargs -I {} aws ecs describe-task-definition \
  --region me-central-1 \
  --task-definition {} \
  --query 'taskDefinition.{family:family,revision:revision,image:containerDefinitions[0].image,cpu:cpu,memory:memory}' \
  --output json | jq
```

---

## 🔨 Création ECR Repository Arquantix (Avec Permissions)

### Commande

```bash
aws ecr create-repository \
  --region me-central-1 \
  --repository-name arquantix-coming-soon \
  --image-scanning-configuration scanOnPush=true \
  --output json
```

### Vérification

```bash
aws ecr describe-repositories \
  --region me-central-1 \
  --repository-names arquantix-coming-soon \
  --query 'repositories[0].{name:repositoryName,uri:repositoryUri,created:createdAt}' \
  --output json
```

### Alternative: Créer via AWS Console

1. Aller sur : https://console.aws.amazon.com/ecr/repositories?region=me-central-1
2. Cliquer sur "Create repository"
3. Configuration :
   - **Visibility settings:** Private
   - **Repository name:** `arquantix-coming-soon`
   - **Tag immutability:** Disabled (ou Enabled selon préférence)
   - **Scan on push:** ✅ Enabled
4. Cliquer sur "Create repository"

---

## 📝 Script Complet d'Audit

J'ai créé un script shell pour faciliter l'exécution de toutes les commandes :

```bash
#!/bin/bash
# audit-aws-infrastructure.sh

set -euo pipefail

REGION="me-central-1"

echo "=== AUDIT AWS INFRASTRUCTURE ==="
echo "Région: $REGION"
echo "Date: $(date)"
echo ""

echo "=== 1. ECR REPOSITORIES ==="
aws ecr describe-repositories \
  --region "$REGION" \
  --query 'repositories[*].{name:repositoryName,uri:repositoryUri,created:createdAt}' \
  --output table

echo ""
echo "=== 2. ECS CLUSTERS ==="
aws ecs list-clusters \
  --region "$REGION" \
  --output json | jq -r '.clusterArns[]' | xargs -I {} aws ecs describe-clusters \
  --region "$REGION" \
  --clusters {} \
  --query 'clusters[0].{name:clusterName,status:status}' \
  --output table

echo ""
echo "=== 3. ECS SERVICES - DEV ==="
aws ecs list-services \
  --region "$REGION" \
  --cluster vancelian-dev-api-cluster \
  --output json | jq -r '.serviceArns[]' | xargs -I {} aws ecs describe-services \
  --region "$REGION" \
  --cluster vancelian-dev-api-cluster \
  --services {} \
  --query 'services[0].{name:serviceName,status:status,desired:desiredCount,running:runningCount}' \
  --output table

echo ""
echo "=== 4. ALB LOAD BALANCERS ==="
aws elbv2 describe-load-balancers \
  --region "$REGION" \
  --query 'LoadBalancers[*].{name:LoadBalancerName,dns:DNSName}' \
  --output table

echo ""
echo "=== 5. TARGET GROUPS ==="
aws elbv2 describe-target-groups \
  --region "$REGION" \
  --query 'TargetGroups[*].{name:TargetGroupName,port:Port,type:TargetType,health:HealthCheckPath}' \
  --output table

echo ""
echo "=== AUDIT TERMINÉ ==="
```

---

## ✅ Actions Immédiates Requises

1. **Créer le repository ECR Arquantix** (via AWS Console ou CLI avec permissions)
   - Nom: `arquantix-coming-soon`
   - Scan on push: ✅ Enabled

2. **Exécuter l'audit** (avec un utilisateur ayant les permissions)
   - Utiliser le script ci-dessus ou les commandes individuelles
   - Documenter les résultats dans `AUDIT_AWS_INFRASTRUCTURE.md`

3. **Mettre à jour la documentation** après l'audit
   - `docs/STATE.md` avec les valeurs réelles
   - `docs/ARCHITECTURE.md` si nécessaire

---

## 🔐 Recommandations IAM

Pour permettre à `cursor-admin` d'effectuer ces audits, ajouter une policy :

**Policy Name:** `AWSInfrastructureReadOnly`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRReadOnly",
      "Effect": "Allow",
      "Action": [
        "ecr:DescribeRepositories",
        "ecr:DescribeImages",
        "ecr:GetRepositoryPolicy",
        "ecr:ListImages"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECSReadOnly",
      "Effect": "Allow",
      "Action": [
        "ecs:Describe*",
        "ecs:List*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ELBReadOnly",
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:Describe*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECRCreateRepository",
      "Effect": "Allow",
      "Action": [
        "ecr:CreateRepository"
      ],
      "Resource": "arn:aws:ecr:me-central-1:411714852748:repository/arquantix-coming-soon"
    }
  ]
}
```

---

**Note:** Ce document contient toutes les commandes nécessaires pour l'audit. Elles doivent être exécutées avec un utilisateur AWS ayant les permissions appropriées.


