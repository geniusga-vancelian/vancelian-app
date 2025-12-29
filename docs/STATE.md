# State - Vancelian App

## TL;DR

État actuel du déploiement avec tableau "Current Deployment" à remplir après chaque déploiement. Format: placeholders à remplir avec les valeurs réelles.

---

## Ce qui est vrai aujourd'hui

### Current Deployment

| Champ | Valeur | Notes |
|-------|--------|-------|
| **Date** | `YYYY-MM-DD` | Date du dernier déploiement |
| **Env** | `dev` \| `staging` \| `prod` | Environnement |
| **Domain** | `api.maisonganopa.com` | Domain name public |
| **ALB Name** | `[ALB_NAME]` | Nom de l'ALB dans AWS Console |
| **ALB ARN** | `arn:aws:elasticloadbalancing:me-central-1:411714852748:loadbalancer/app/[ALB_NAME]/[ID]` | ARN complet de l'ALB |
| **Listener 443** | `[LISTENER_ARN]` | ARN du listener HTTPS |
| **ALB Rules** | `Path is /telegram/webhook → [TG_ARN]` | Règles de routing |
| **Target Group Name** | `ganopa-dev-bot-tg` (ou similaire) | Nom du Target Group |
| **Target Group ARN** | `arn:aws:elasticloadbalancing:me-central-1:411714852748:targetgroup/[TG_NAME]/[ID]` | ARN du Target Group |
| **Target Group Type** | `IP` | Type (IP ou Instance) |
| **Target Group Port** | `8000` | Port des targets |
| **Target Group Health Check** | `Path: /health, Port: 8000, Protocol: HTTP` | Configuration health check |
| **ECS Cluster** | `vancelian-dev-api-cluster` | Nom du cluster ECS |
| **ECS Service** | `ganopa-dev-bot-svc` | Nom du service ECS |
| **Task Definition Family** | `ganopa-bot` | Family name |
| **Task Definition Revision** | `[REVISION]` | Dernière revision (ex: 23) |
| **Task Definition ARN** | `arn:aws:ecs:me-central-1:411714852748:task-definition/ganopa-bot:[REVISION]` | ARN complet |
| **Docker Image** | `411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot:[GITHUB_SHA]` | Image ECR avec tag |
| **Docker Image Tag** | `[GITHUB_SHA]` | Commit hash (ex: a35db8b) |
| **Container Name** | `ganopa-bot` | Nom du container dans Task Definition |
| **Container Port** | `8000` | Port exposé |
| **Healthcheck Path** | `/health` | Path pour health check |
| **Healthcheck Port** | `8000` | Port pour health check |
| **Desired Count** | `1` | Nombre de tasks désirées |
| **Running Count** | `1` | Nombre de tasks en cours d'exécution |
| **Service Status** | `ACTIVE` | Statut du service (ACTIVE/INACTIVE) |
| **Env Vars Required** | `TELEGRAM_BOT_TOKEN` (required)<br>`OPENAI_API_KEY` (required)<br>`WEBHOOK_SECRET` (optional)<br>`OPENAI_MODEL` (optional, default: "gpt-4o-mini")<br>`BUILD_ID` (optional, default: "dev")<br>`PORT` (optional, default: "8000") | Variables d'environnement |
| **Last Known Good Version** | `ganopa-bot-[HASH]` | Version retournée par `/_meta` |
| **Last Known Good Build ID** | `[BUILD_ID]` | Build ID retourné par `/_meta` |
| **Last Verified** | `YYYY-MM-DD HH:MM` | Date/heure de dernière vérification |

---

## Commandes pour Remplir le Tableau

### ALB

```bash
# ALB Name et ARN
aws elbv2 describe-load-balancers --region me-central-1 \
  --query 'LoadBalancers[?contains(DNSName, `maisonganopa`)].{name:LoadBalancerName,arn:LoadBalancerArn}' \
  --output json | jq

# Listener 443 ARN
ALB_ARN="[ALB_ARN_FROM_ABOVE]"
aws elbv2 describe-listeners --region me-central-1 --load-balancer-arn "${ALB_ARN}" \
  --query 'Listeners[?Port==`443`].ListenerArn' --output text

# ALB Rules
LISTENER_ARN="[LISTENER_ARN_FROM_ABOVE]"
aws elbv2 describe-rules --region me-central-1 --listener-arn "${LISTENER_ARN}" \
  --query 'Rules[*].{priority:Priority,conditions:Conditions[*].Values,actions:Actions[*].TargetGroupArn}' \
  --output json | jq
```

### Target Group

```bash
# Target Group Name et ARN
aws elbv2 describe-target-groups --region me-central-1 \
  --query 'TargetGroups[?contains(TargetGroupName, `ganopa`)].{name:TargetGroupName,arn:TargetGroupArn,port:Port,type:TargetType}' \
  --output json | jq

# Health Check
TG_ARN="[TG_ARN_FROM_ABOVE]"
aws elbv2 describe-target-groups --region me-central-1 --target-group-arns "${TG_ARN}" \
  --query 'TargetGroups[0].HealthCheckPath' --output text
```

### ECS

```bash
# Service Info
aws ecs describe-services --region me-central-1 \
  --cluster vancelian-dev-api-cluster --services ganopa-dev-bot-svc \
  --query 'services[0].{status:status,desired:desiredCount,running:runningCount,taskDef:taskDefinition}' \
  --output json | jq

# Task Definition
TASKDEF_ARN="[TASKDEF_ARN_FROM_ABOVE]"
aws ecs describe-task-definition --region me-central-1 --task-definition "${TASKDEF_ARN}" \
  --query 'taskDefinition.{family:family,revision:revision,image:containerDefinitions[0].image}' \
  --output json | jq
```

### Version

```bash
# Version déployée
curl -s https://api.maisonganopa.com/_meta | jq '{version,build_id}'
```

---

## Historique des Déploiements

| Date | Env | Version | Build ID | Image Tag | Status | Notes |
|------|-----|---------|----------|-----------|--------|-------|
| `YYYY-MM-DD` | `dev` | `ganopa-bot-[HASH]` | `[BUILD_ID]` | `[GITHUB_SHA]` | ✅ OK | Initial deployment |
| `YYYY-MM-DD` | `dev` | `ganopa-bot-[HASH]` | `[BUILD_ID]` | `[GITHUB_SHA]` | ✅ OK | Added command system |

---

## À vérifier quand ça casse

### Le tableau n'est pas à jour

1. Exécuter les commandes ci-dessus pour récupérer les valeurs
2. Mettre à jour le tableau "Current Deployment"
3. Ajouter une entrée dans "Historique des Déploiements"

### Besoin de vérifier un déploiement précédent

1. Consulter "Historique des Déploiements"
2. Utiliser les valeurs pour vérifier l'état à cette date
3. Comparer avec l'état actuel

---

**Dernière mise à jour:** 2025-12-29

