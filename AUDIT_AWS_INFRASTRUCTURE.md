# Audit Infrastructure AWS - Vancelian App

**Date:** 2025-12-30  
**Région:** me-central-1  
**Account ID:** 411714852748

---

## Résumé Exécutif

### ✅ Ce qui fonctionne

1. **Maison Ganopa (Bot Telegram)**
   - Service ECS `ganopa-dev-bot-svc` déployé sur cluster `vancelian-dev-api-cluster`
   - Workflow GitHub Actions opérationnel (OIDC)
   - ECR repository `ganopa-bot` configuré
   - ALB routing configuré (`api.maisonganopa.com`)

2. **Arquantix (Coming Soon)**
   - Code source créé (`services/arquantix/coming-soon/`)
   - Workflow GitHub Actions créé (avec secrets)
   - ECR repository à créer : `arquantix-coming-soon`

### ⚠️ Ce qui doit être vérifié/mis à jour

1. **Arquantix**
   - ❌ ECR repository `arquantix-coming-soon` n'existe pas encore (workflow va échouer)
   - ❌ Pas de Task Definition ECS
   - ❌ Pas de Service ECS
   - ❌ Pas de Target Group ALB
   - ❌ Pas de routing ALB configuré

2. **Vancelian API (environnements dev/staging/prod)**
   - ⚠️ Workflows existent mais infrastructure non documentée
   - ⚠️ ECR repository `vancelian-api` utilisé mais non documenté
   - ⚠️ Services ECS : `vancelian-dev-api-svc`, `vancelian-staging-api-svc`, `vancelian-prod-api-svc`
   - ⚠️ Clusters : `vancelian-dev-api-cluster`, `vancelian-staging-api-cluster`, `vancelian-prod-api-cluster`

3. **Maison Ganopa (staging/prod)**
   - ⚠️ Workflow supporte staging/prod mais infrastructure non documentée
   - ⚠️ Services ECS : `ganopa-staging-bot-svc`, `ganopa-prod-bot-svc` (potentiellement non créés)
   - ⚠️ Clusters : `vancelian-staging-api-cluster`, `vancelian-prod-api-cluster` (potentiellement non créés)

---

## Détail par Service/Marque

### 1. Maison Ganopa (Bot Telegram)

#### Environnement: DEV ✅

| Composant | Nom/Configuration | Status | Notes |
|-----------|------------------|--------|-------|
| **ECR Repository** | `ganopa-bot` | ✅ Configuré | Tag: `{GITHUB_SHA}` |
| **ECS Cluster** | `vancelian-dev-api-cluster` | ✅ Documenté | Utilisé par workflow |
| **ECS Service** | `ganopa-dev-bot-svc` | ✅ Documenté | Desired: 1 (Fargate) |
| **Task Definition** | `ganopa-bot:XX` | ✅ Configuré | Container: `ganopa-bot`, Port: 8000 |
| **Container Image** | `411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:{SHA}` | ✅ Configuré | |
| **ALB Target Group** | `ganopa-dev-bot-tg` | ✅ Documenté | Type: IP, Port: 8000, Health: `/health` |
| **ALB Routing** | Path: `/telegram/webhook` | ✅ Configuré | Domain: `api.maisonganopa.com` |
| **GitHub Workflow** | `deploy-ganopa-bot.yml` | ✅ Opérationnel | OIDC: `GitHubDeployRole` |
| **Domain** | `api.maisonganopa.com` | ✅ Documenté | Route53 → ALB |

**Endpoints:**
- `https://api.maisonganopa.com/health` (GET)
- `https://api.maisonganopa.com/_meta` (GET)
- `https://api.maisonganopa.com/telegram/webhook` (GET/POST)

#### Environnement: STAGING ⚠️

| Composant | Nom/Configuration | Status | Notes |
|-----------|------------------|--------|-------|
| **ECS Cluster** | `vancelian-staging-api-cluster` | ⚠️ Non vérifié | Mentionné dans workflow |
| **ECS Service** | `ganopa-staging-bot-svc` | ⚠️ Non vérifié | Mentionné dans workflow |
| **ALB Target Group** | `ganopa-staging-bot-tg` (?) | ❌ Non documenté | À vérifier |
| **Domain** | Non documenté | ❌ Non documenté | À configurer |

**Action requise:** Vérifier l'existence des ressources staging dans AWS Console.

#### Environnement: PROD ⚠️

| Composant | Nom/Configuration | Status | Notes |
|-----------|------------------|--------|-------|
| **ECS Cluster** | `vancelian-prod-api-cluster` | ⚠️ Non vérifié | Mentionné dans workflow |
| **ECS Service** | `ganopa-prod-bot-svc` | ⚠️ Non vérifié | Mentionné dans workflow |
| **ALB Target Group** | `ganopa-prod-bot-tg` (?) | ❌ Non documenté | À vérifier |
| **Domain** | Non documenté | ❌ Non documenté | À configurer |

**Action requise:** Vérifier l'existence des ressources prod dans AWS Console.

---

### 2. Arquantix (Coming Soon)

#### Environnement: DEV (Coming Soon) ❌

| Composant | Nom/Configuration | Status | Notes |
|-----------|------------------|--------|-------|
| **ECR Repository** | `arquantix-coming-soon` | ❌ **À CRÉER** | Workflow échouera sinon |
| **ECS Cluster** | Non défini | ❌ Non défini | Quel cluster utiliser ? |
| **ECS Service** | Non défini | ❌ Non défini | Nom à définir |
| **Task Definition** | Non défini | ❌ Non défini | Family à définir |
| **Container Image** | `411714852748.dkr.ecr.me-central-1.amazonaws.com/arquantix-coming-soon:latest` | ⚠️ Partiel | Image pas encore pushée |
| **ALB Target Group** | Non défini | ❌ Non défini | À créer |
| **ALB Routing** | Non défini | ❌ Non défini | Path/Domain à définir |
| **GitHub Workflow** | `arquantix-push-to-ecr.yml` | ⚠️ Créé | Utilise secrets (non OIDC) |
| **Domain** | Non défini | ❌ Non défini | Ex: `arquantix.com` ou sous-domaine ? |

**Actions requises:**
1. ✅ Créer ECR repository `arquantix-coming-soon`
2. ✅ Définir stratégie de déploiement (ECS Fargate ou autre ?)
3. ✅ Créer Task Definition ECS
4. ✅ Créer Service ECS (si ECS choisi)
5. ✅ Créer Target Group ALB
6. ✅ Configurer routing ALB
7. ✅ Configurer Domain (Route53)

**GitHub Workflow:**
- ✅ Workflow créé et fonctionnel
- ⚠️ Utilise secrets (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) au lieu d'OIDC
- ⚠️ Ne fait que push vers ECR (pas de déploiement ECS)

---

### 3. Vancelian API (Services généraux)

#### Environnement: DEV ⚠️

| Composant | Nom/Configuration | Status | Notes |
|-----------|------------------|--------|-------|
| **ECR Repository** | `vancelian-api` | ⚠️ Non documenté | Mentionné dans workflow |
| **ECS Cluster** | `vancelian-dev-api-cluster` | ✅ Documenté | Partagé avec ganopa-bot |
| **ECS Service** | `vancelian-dev-api-svc` | ⚠️ Non documenté | Container: `api`, Port: ? |
| **GitHub Workflow** | `deploy-dev.yml` | ✅ Configuré | Paths: `app/**`, `agent_gateway/**`, etc. |
| **Domain** | Non documenté | ❌ Non documenté | À vérifier |

**Code source:** `app/`, `agent_gateway/`, `agent/` (racine du repo)

#### Environnement: STAGING ⚠️

| Composant | Nom/Configuration | Status | Notes |
|-----------|------------------|--------|-------|
| **ECS Cluster** | `vancelian-staging-api-cluster` | ⚠️ Non vérifié | Mentionné dans workflow |
| **ECS Service** | `vancelian-staging-api-svc` | ⚠️ Non vérifié | Mentionné dans workflow |
| **GitHub Workflow** | `deploy-staging.yml` | ✅ Configuré | Trigger: push sur `staging` |

#### Environnement: PROD ⚠️

| Composant | Nom/Configuration | Status | Notes |
|-----------|------------------|--------|-------|
| **ECS Cluster** | `vancelian-prod-api-cluster` | ⚠️ Non vérifié | Mentionné dans workflow |
| **ECS Service** | `vancelian-prod-api-svc` | ⚠️ Non vérifié | Mentionné dans workflow |
| **GitHub Workflow** | `deploy-prod.yml` | ✅ Configuré | Trigger: push sur `prod` |

**Actions requises:** Documenter et vérifier l'infrastructure Vancelian API dans AWS Console.

---

## Comparaison des Configurations GitHub Actions

| Workflow | Authentication | ECR Repository | Déploiement ECS | Status |
|----------|---------------|----------------|-----------------|--------|
| `deploy-ganopa-bot.yml` | ✅ OIDC (`GitHubDeployRole`) | `ganopa-bot` | ✅ Oui | ✅ Opérationnel |
| `deploy-dev.yml` | ✅ OIDC (`GitHubDeployRole`) | `vancelian-api` | ✅ Oui | ✅ Configuré |
| `deploy-staging.yml` | ✅ OIDC (`GitHubDeployRole`) | `vancelian-api` | ✅ Oui | ✅ Configuré |
| `deploy-prod.yml` | ✅ OIDC (`GitHubDeployRole`) | `vancelian-api` | ✅ Oui | ✅ Configuré |
| `arquantix-push-to-ecr.yml` | ⚠️ Secrets (pas OIDC) | `arquantix-coming-soon` | ❌ Non | ⚠️ Partiel |

**Recommandation:** Migrer `arquantix-push-to-ecr.yml` vers OIDC pour cohérence et sécurité.

---

## Commandes AWS pour Audit Complet

### 1. Lister les ECR Repositories

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

### 2. Lister les ECS Clusters

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

### 3. Lister les Services ECS par Cluster

```bash
# DEV
aws ecs list-services \
  --region me-central-1 \
  --cluster vancelian-dev-api-cluster \
  --output json | jq -r '.serviceArns[]' | xargs -I {} aws ecs describe-services \
  --region me-central-1 \
  --cluster vancelian-dev-api-cluster \
  --services {} \
  --query 'services[0].{name:serviceName,status:status,desired:desiredCount,running:runningCount,taskDef:taskDefinition}' \
  --output table

# STAGING
aws ecs list-services \
  --region me-central-1 \
  --cluster vancelian-staging-api-cluster \
  --output json | jq -r '.serviceArns[]' | xargs -I {} aws ecs describe-services \
  --region me-central-1 \
  --cluster vancelian-staging-api-cluster \
  --services {} \
  --query 'services[0].{name:serviceName,status:status,desired:desiredCount,running:runningCount,taskDef:taskDefinition}' \
  --output table

# PROD
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

**Services attendus (DEV):**
- ✅ `ganopa-dev-bot-svc`
- ⚠️ `vancelian-dev-api-svc`

**Services attendus (STAGING):**
- ⚠️ `ganopa-staging-bot-svc`
- ⚠️ `vancelian-staging-api-svc`

**Services attendus (PROD):**
- ⚠️ `ganopa-prod-bot-svc`
- ⚠️ `vancelian-prod-api-svc`

### 4. Lister les ALB et Target Groups

```bash
# ALB
aws elbv2 describe-load-balancers \
  --region me-central-1 \
  --query 'LoadBalancers[*].{name:LoadBalancerName,dns:DNSName,arn:LoadBalancerArn}' \
  --output table

# Target Groups
aws elbv2 describe-target-groups \
  --region me-central-1 \
  --query 'TargetGroups[*].{name:TargetGroupName,port:Port,type:TargetType,protocol:Protocol,health:HealthCheckPath}' \
  --output table
```

**Target Groups attendus:**
- ✅ `ganopa-dev-bot-tg` (Port: 8000, Health: `/health`)
- ⚠️ `ganopa-staging-bot-tg` (à vérifier)
- ⚠️ `ganopa-prod-bot-tg` (à vérifier)
- ⚠️ Target groups pour `vancelian-api` (à vérifier)

### 5. Vérifier les Task Definitions

```bash
# Ganopa Bot
aws ecs list-task-definitions \
  --region me-central-1 \
  --family-prefix ganopa-bot \
  --query 'taskDefinitionArns[-1]' \
  --output text | xargs -I {} aws ecs describe-task-definition \
  --region me-central-1 \
  --task-definition {} \
  --query 'taskDefinition.{family:family,revision:revision,image:containerDefinitions[0].image,cpu:cpu,memory:memory}' \
  --output json | jq

# Vancelian API
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

## Checklist des Actions Requises

### Arquantix (Priorité Haute)

- [ ] **Créer ECR repository `arquantix-coming-soon`**
  ```bash
  aws ecr create-repository \
    --region me-central-1 \
    --repository-name arquantix-coming-soon \
    --image-scanning-configuration scanOnPush=true
  ```

- [ ] **Définir stratégie de déploiement**
  - Option 1: ECS Fargate (comme ganopa-bot)
  - Option 2: S3 + CloudFront (statique)
  - Option 3: Autre (Lambda@Edge, etc.)

- [ ] **Si ECS choisi:**
  - [ ] Définir cluster ECS (utiliser `vancelian-dev-api-cluster` ou créer nouveau ?)
  - [ ] Créer Task Definition (`arquantix-coming-soon`)
  - [ ] Créer Service ECS (`arquantix-dev-coming-soon-svc`)
  - [ ] Créer Target Group ALB
  - [ ] Configurer routing ALB (path/domain)
  - [ ] Configurer Domain (Route53)

- [ ] **Migrer workflow vers OIDC** (optionnel mais recommandé)

### Maison Ganopa (Vérification)

- [ ] **Vérifier infrastructure STAGING**
  - [ ] Cluster `vancelian-staging-api-cluster` existe
  - [ ] Service `ganopa-staging-bot-svc` existe
  - [ ] Target Group existe et est configuré
  - [ ] Domain configuré (si nécessaire)

- [ ] **Vérifier infrastructure PROD**
  - [ ] Cluster `vancelian-prod-api-cluster` existe
  - [ ] Service `ganopa-prod-bot-svc` existe
  - [ ] Target Group existe et est configuré
  - [ ] Domain configuré (si nécessaire)

### Vancelian API (Documentation)

- [ ] **Documenter infrastructure DEV**
  - [ ] Service `vancelian-dev-api-svc` (status, endpoints, domain)
  - [ ] Task Definition details
  - [ ] ALB routing (si applicable)

- [ ] **Vérifier/Documenter infrastructure STAGING**
  - [ ] Cluster `vancelian-staging-api-cluster`
  - [ ] Service `vancelian-staging-api-svc`
  - [ ] Domain/endpoints

- [ ] **Vérifier/Documenter infrastructure PROD**
  - [ ] Cluster `vancelian-prod-api-cluster`
  - [ ] Service `vancelian-prod-api-svc`
  - [ ] Domain/endpoints

---

## Résumé des Problèmes Critiques

### 🔴 Critique (Blocant)

1. **Arquantix: ECR repository n'existe pas**
   - Le workflow GitHub Actions va échouer au push
   - **Fix:** Créer le repository ECR `arquantix-coming-soon`

### 🟡 Important (À vérifier)

2. **Arquantix: Pas de stratégie de déploiement définie**
   - Le workflow push vers ECR mais ne déploie pas
   - **Action:** Décider de la stratégie (ECS, S3+CloudFront, etc.)

3. **Maison Ganopa: Infrastructure staging/prod non documentée**
   - Workflows existent mais ressources AWS non vérifiées
   - **Action:** Vérifier l'existence des clusters/services dans AWS

4. **Vancelian API: Infrastructure non documentée**
   - Services utilisés mais non documentés dans `/docs`
   - **Action:** Documenter l'architecture complète

### 🟢 Mineur (Recommandations)

5. **Arquantix: Workflow utilise secrets au lieu d'OIDC**
   - Incohérent avec les autres workflows
   - **Recommandation:** Migrer vers OIDC pour sécurité et cohérence

---

## Prochaines Étapes Recommandées

1. **Immédiat:** Créer ECR repository `arquantix-coming-soon`
2. **Court terme:** Définir et implémenter stratégie de déploiement Arquantix
3. **Court terme:** Exécuter les commandes AWS d'audit et documenter les résultats
4. **Moyen terme:** Documenter complètement l'infrastructure Vancelian API
5. **Moyen terme:** Vérifier et documenter infrastructure staging/prod pour Ganopa

---

**Note:** Cet audit est basé sur l'analyse du code source et de la documentation. Les ressources AWS réelles doivent être vérifiées via AWS Console ou CLI avec les permissions appropriées.


