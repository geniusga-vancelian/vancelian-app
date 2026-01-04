# 🔍 AUDIT COMPLET - DÉPLOIEMENT ECS ARQUANTIX

**Date :** 2026-01-04  
**Région AWS :** me-central-1  
**Service :** arquantix-coming-soon  
**Cluster :** arquantix-cluster

---

## 📋 RÉSUMÉ EXÉCUTIF

Le déploiement ECS est **bloqué en échec** depuis plusieurs heures. Le service tente de déployer une nouvelle task definition (revision 6) avec l'image tag `0337eafb300d26bc0aa60dd9de0286670d3d9f5e`, mais **toutes les nouvelles tasks échouent immédiatement** avec l'erreur `ResourceInitializationError: unable to pull secrets or registry auth`. La cause racine est un **problème de connectivité réseau** : les tasks Fargate sont dans des subnets privés (`assignPublicIp: DISABLED`) **sans VPC Endpoint pour ECR**, ce qui empêche l'authentification et le téléchargement des images depuis ECR. Le déploiement PRIMARY reste bloqué en `IN_PROGRESS` avec 8 tasks échouées, tandis que l'ancien déploiement ACTIVE (revision 3, image `latest`) continue de fonctionner normalement.

---

## 🔎 OBSERVATIONS CLÉS

### Phase A - Audit Repo / Workflow

#### 1. Workflow GitHub Actions
- **Fichier :** `.github/workflows/arquantix-coming-soon-deploy.yml`
- **Triggers :** 
  - Push sur branches `main` ou `arquantix-coming-soon`
  - Paths : `services/arquantix/web/**` ou le workflow lui-même
- **Image tag :** `${{ github.sha }}` (SHA du commit, pas `latest`)
- **Task definition :** Récupérée depuis le service existant, puis nettoyée (suppression de `taskRoleArn: null`)
- **wait-for-service-stability :** `true` ✅
- **container-name :** `arquantix-coming-soon` ✅

#### 2. Task Definition Template
- **Fichier :** `services/arquantix/.aws/task-definition.json`
- **Chemin utilisé par workflow :** ✅ Correct
- **Port :** 3000 ✅
- **CPU/Memory :** 256/512 ✅

#### 3. Dockerfile
- **Fichier :** `services/arquantix/web/Dockerfile`
- **Port exposé :** 3000 ✅
- **Commande start :** `node_modules/.bin/next start -H 0.0.0.0 -p 3000` ✅
- **Build arg NEXT_PUBLIC_GIT_SHA :** ✅ Présent

#### 4. Route /figma
- **Fichier :** `services/arquantix/web/src/app/figma/page.tsx`
- **Status :** ✅ Existe et affiche le build SHA

---

### Phase B - Audit GitHub Actions

#### Dernier Run
- **SHA :** `4f8b7b3244f025bbacf18d6a30ab3c19a4aacf04`
- **Status :** `completed`
- **Conclusion :** `failure`
- **URL :** https://github.com/geniusga-vancelian/vancelian-app/actions/runs/20692942547

**Note :** Le workflow échoue probablement à l'étape "Deploy to ECS" car le service ne peut pas stabiliser (tasks qui échouent continuellement).

---

### Phase C - Audit AWS

#### C1) ECR - Images disponibles

```json
[
  {
    "tags": null,
    "digest": "sha256:b28934f82e6cf7d1e1af520dbc1e002095fdab42b7f6fade0eea514b90dda6fc",
    "pushedAt": "2026-01-04T15:15:39.298000+04:00"
  },
  {
    "tags": ["latest"],
    "digest": "sha256:5cbd45360d1d8bcf1fa808c37241f5759cf4c75f70948af2b41bbf701a12de5b",
    "pushedAt": "2026-01-04T15:25:55.875000+04:00"
  },
  {
    "tags": ["8e184e5d5647f21e60ca28d23c3c9843bf18e3d2"],
    "digest": "sha256:b46a5f1a7e11fa9b495b5d71ad1e7d492cc5c42b25437f9b1fcec21498f46044",
    "pushedAt": "2026-01-04T15:36:27.026000+04:00"
  },
  {
    "tags": ["b1510bec39b4d2e0068414a2e18c3e2c08d505d9"],
    "digest": "sha256:03a02e3e705d6e085856bad8c3b25663c4a0d9401e719566d40b644c54b47eef",
    "pushedAt": "2026-01-04T15:42:23.386000+04:00"
  },
  {
    "tags": ["0337eafb300d26bc0aa60dd9de0286670d3d9f5e"],
    "digest": "sha256:816ff9a79461839f0ff8adfaa653c716e7ba62aef8c08643164f2ac7ad7fa3c3",
    "pushedAt": "2026-01-04T15:42:26.156000+04:00"
  }
]
```

**✅ Les images sont bien poussées dans ECR avec les tags SHA attendus.**

#### C2) ECS Service - État du déploiement

```json
{
  "status": "ACTIVE",
  "desiredCount": 1,
  "runningCount": 1,
  "pendingCount": 0,
  "taskDefinition": "arn:aws:ecs:me-central-1:411714852748:task-definition/arquantix-coming-soon:6",
  "deployments": [
    {
      "id": "ecs-svc/7131085801412074600",
      "status": "PRIMARY",
      "taskDefinition": "arn:aws:ecs:me-central-1:411714852748:task-definition/arquantix-coming-soon:6",
      "desiredCount": 1,
      "pendingCount": 0,
      "runningCount": 0,
      "failedTasks": 8,
      "rolloutState": "IN_PROGRESS",
      "rolloutStateReason": "ECS deployment ecs-svc/7131085801412074600 in progress."
    },
    {
      "id": "ecs-svc/2073405824300860302",
      "status": "ACTIVE",
      "taskDefinition": "arn:aws:ecs:me-central-1:411714852748:task-definition/arquantix-coming-soon:3",
      "desiredCount": 1,
      "runningCount": 1,
      "failedTasks": 0,
      "rolloutState": "COMPLETED"
    }
  ]
}
```

**❌ PROBLÈME :** Le déploiement PRIMARY (revision 6) est bloqué avec **8 tasks échouées** et **0 running**. L'ancien déploiement (revision 3) continue de tourner.

#### C3) Événements ECS - Erreur récurrente

**Erreur observée (répétée 50+ fois) :**

```
(service arquantix-coming-soon) was unable to place a task. 
Reason: ResourceInitializationError: unable to pull secrets or registry auth: 
The task cannot pull registry auth from Amazon ECR: There is a connection issue 
between the task and Amazon ECR. Check your task network configuration. 
operation error ECR: GetAuthorizationToken, exceeded maximum number of attempts, 3, 
https response error StatusCode: 0, RequestID: , request send failed, 
Post "https://api.ecr.me-central-1.amazonaws.com/": dial tcp 3.28.72.11:443: i/o timeout.
```

**🔴 ROOT CAUSE IDENTIFIÉ :** Les tasks ne peuvent pas accéder à ECR pour s'authentifier et télécharger l'image.

#### C4) Task Definition - Configuration réseau

```json
{
  "family": "arquantix-coming-soon",
  "revision": 6,
  "image": "411714852748.dkr.ecr.me-central-1.amazonaws.com/arquantix-coming-soon:0337eafb300d26bc0aa60dd9de0286670d3d9f5e",
  "networkMode": "awsvpc",
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": ["subnet-03b9c0f9c2e462492", "subnet-03a15c01ad644adec"],
      "securityGroups": ["sg-0205603e4e671f752"],
      "assignPublicIp": "DISABLED"  // ❌ PROBLÈME
    }
  }
}
```

**❌ PROBLÈME :** `assignPublicIp: DISABLED` dans un environnement **sans VPC Endpoint pour ECR**.

#### C5) Subnets - Configuration

```json
[
  {
    "subnetId": "subnet-03b9c0f9c2e462492",
    "availabilityZone": "me-central-1b",
    "mapPublicIpOnLaunch": true,
    "vpcId": "vpc-05aa7c05949e8096b"
  },
  {
    "subnetId": "subnet-03a15c01ad644adec",
    "availabilityZone": "me-central-1a",
    "mapPublicIpOnLaunch": true,
    "vpcId": "vpc-05aa7c05949e8096b"
  }
]
```

**Note :** Les subnets ont `mapPublicIpOnLaunch: true`, mais cela ne s'applique **pas** aux tasks Fargate. Les tasks Fargate nécessitent explicitement `assignPublicIp: ENABLED` ou un VPC Endpoint.

#### C6) VPC Endpoints - Absence critique

```json
[]
```

**❌ PROBLÈME CRITIQUE :** **AUCUN VPC Endpoint pour ECR** n'existe dans le VPC. Les tasks dans des subnets privés ne peuvent pas accéder à ECR.

#### C7) ALB / Target Group - Health checks

```json
{
  "port": 3000,
  "protocol": "HTTP",
  "healthCheckPath": "/health",
  "healthCheckIntervalSeconds": 30,
  "healthCheckTimeoutSeconds": 10,
  "healthyThresholdCount": 2,
  "unhealthyThresholdCount": 5,
  "matcher": {"HttpCode": "200-399"}
}
```

**Target Health :**
```json
{
  "TargetHealthDescriptions": [
    {
      "Target": {"Id": "172.31.33.175", "Port": 3000},
      "TargetHealth": {"State": "healthy"}
    }
  ]
}
```

**✅ L'ancien déploiement (revision 3) est healthy.** Le problème est uniquement sur le nouveau déploiement.

---

## 🎯 ROOT CAUSE PROBABLE

### Cause #1 : Absence de connectivité réseau vers ECR (CRITIQUE)

**Preuve :**
- Tasks dans subnets privés (`assignPublicIp: DISABLED`)
- Aucun VPC Endpoint pour ECR
- Erreur : `dial tcp 3.28.72.11:443: i/o timeout` (timeout sur ECR API)
- 8 tasks échouées avec `ResourceInitializationError`

**Impact :** Les tasks ne peuvent pas s'authentifier auprès d'ECR ni télécharger l'image, donc elles échouent immédiatement.

### Cause #2 : Déploiement bloqué en IN_PROGRESS

**Preuve :**
- `rolloutState: "IN_PROGRESS"` depuis 15:42:36 (plus d'1h)
- `failedTasks: 8`, `runningCount: 0`
- `wait-for-service-stability: true` dans le workflow → timeout/blocage

**Impact :** Le workflow GitHub Actions reste bloqué en attente de stabilité qui n'arrivera jamais.

---

## 🔧 CORRECTIFS RECOMMANDÉS

### Fix 1 : Solution immédiate - Activer Public IP (RAPIDE)

**Objectif :** Permettre aux tasks d'accéder à ECR via Internet public.

**Commande :**

```bash
# Modifier la task definition pour activer assignPublicIp
aws ecs update-service \
  --region me-central-1 \
  --cluster arquantix-cluster \
  --service arquantix-coming-soon \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-03b9c0f9c2e462492,subnet-03a15c01ad644adec],securityGroups=[sg-0205603e4e671f752],assignPublicIp=ENABLED}" \
  --force-new-deployment
```

**OU** modifier le workflow pour inclure `assignPublicIp: ENABLED` dans la task definition avant le render.

**Fichier à modifier :** `.github/workflows/arquantix-coming-soon-deploy.yml`

Ajouter après la ligne 117 (après avoir écrit `taskdef.json`) :

```yaml
# Ensure assignPublicIp is ENABLED for ECR access
python3 << 'PYEOF'
import json
with open('taskdef.json', 'r') as f:
    td = json.load(f)
if 'networkConfiguration' not in td:
    td['networkConfiguration'] = {}
if 'awsvpcConfiguration' not in td['networkConfiguration']:
    td['networkConfiguration']['awsvpcConfiguration'] = {}
td['networkConfiguration']['awsvpcConfiguration']['assignPublicIp'] = 'ENABLED'
with open('taskdef.json', 'w') as f:
    json.dump(td, f, indent=2, sort_keys=True)
print("✅ Set assignPublicIp=ENABLED for ECR access")
PYEOF
```

**Avantages :**
- ✅ Solution immédiate (5 minutes)
- ✅ Pas de coût supplémentaire
- ✅ Fonctionne immédiatement

**Inconvénients :**
- ⚠️ Moins sécurisé (tasks exposées sur Internet)
- ⚠️ Nécessite des security groups restrictifs

---

### Fix 2 : Solution recommandée - Créer VPC Endpoints pour ECR (SÉCURISÉ)

**Objectif :** Permettre l'accès privé à ECR sans exposer les tasks sur Internet.

**Commandes :**

```bash
# 1. Créer VPC Endpoint pour ECR API (com.amazonaws.me-central-1.ecr.api)
aws ec2 create-vpc-endpoint \
  --region me-central-1 \
  --vpc-id vpc-05aa7c05949e8096b \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.me-central-1.ecr.api \
  --subnet-ids subnet-03b9c0f9c2e462492 subnet-03a15c01ad644adec \
  --security-group-ids sg-0205603e4e671f752 \
  --private-dns-enabled

# 2. Créer VPC Endpoint pour ECR Docker (com.amazonaws.me-central-1.ecr.dkr)
aws ec2 create-vpc-endpoint \
  --region me-central-1 \
  --vpc-id vpc-05aa7c05949e8096b \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.me-central-1.ecr.dkr \
  --subnet-ids subnet-03b9c0f9c2e462492 subnet-03a15c01ad644adec \
  --security-group-ids sg-0205603e4e671f752 \
  --private-dns-enabled

# 3. Créer VPC Endpoint pour S3 (pour les layers Docker, Gateway type = gratuit)
aws ec2 create-vpc-endpoint \
  --region me-central-1 \
  --vpc-id vpc-05aa7c05949e8096b \
  --vpc-endpoint-type Gateway \
  --service-name com.amazonaws.me-central-1.s3 \
  --route-table-ids $(aws ec2 describe-route-tables --region me-central-1 --filters "Name=vpc-id,Values=vpc-05aa7c05949e8096b" --query 'RouteTables[0].RouteTableId' --output text)
```

**Coût estimé :** ~$7-10/mois pour les 2 Interface endpoints (ECR API + DKR). S3 Gateway = gratuit.

**Avantages :**
- ✅ Sécurisé (trafic privé uniquement)
- ✅ Pas d'exposition Internet
- ✅ Meilleure pratique AWS

**Inconvénients :**
- ⚠️ Coût mensuel (~$7-10)
- ⚠️ Nécessite quelques minutes pour créer

**Note :** Après création des endpoints, le déploiement devrait fonctionner automatiquement avec `assignPublicIp: DISABLED`.

---

### Fix 3 : Annuler le déploiement bloqué (IMMÉDIAT)

**Objectif :** Libérer le service du déploiement PRIMARY bloqué.

**Commande :**

```bash
# Option A : Forcer le rollback vers l'ancien déploiement
aws ecs update-service \
  --region me-central-1 \
  --cluster arquantix-cluster \
  --service arquantix-coming-soon \
  --task-definition arquantix-coming-soon:3 \
  --force-new-deployment

# Option B : Attendre que le déploiement PRIMARY échoue complètement (timeout)
# ECS annulera automatiquement après un certain nombre d'échecs
```

**Recommandation :** Exécuter Fix 1 ou Fix 2 d'abord, puis le déploiement se stabilisera automatiquement.

---

### Fix 4 : Améliorer le workflow pour éviter les blocages futurs

**Fichier :** `.github/workflows/arquantix-coming-soon-deploy.yml`

**Modification :** Ajouter un timeout et une meilleure gestion d'erreur :

```yaml
- name: Deploy to ECS
  uses: aws-actions/amazon-ecs-deploy-task-definition@v2
  with:
    task-definition: ${{ steps.render-taskdef.outputs.task-definition }}
    service: ${{ env.ECS_SERVICE }}
    cluster: ${{ env.ECS_CLUSTER }}
    wait-for-service-stability: true
  timeout-minutes: 15  # Ajouter un timeout
  continue-on-error: false
```

**OU** désactiver temporairement `wait-for-service-stability` pour éviter les blocages :

```yaml
wait-for-service-stability: false  # Temporaire, jusqu'à ce que le problème réseau soit résolu
```

---

## ✅ NEXT CHECKS - Validation après correctif

### 1. Vérifier que les tasks démarrent

```bash
aws ecs describe-services \
  --region me-central-1 \
  --cluster arquantix-cluster \
  --services arquantix-coming-soon \
  --query 'services[0].deployments[?status==`PRIMARY`].{runningCount:runningCount,failedTasks:failedTasks,rolloutState:rolloutState}' \
  --output json
```

**Attendu :** `runningCount: 1`, `failedTasks: 0`, `rolloutState: "COMPLETED"`

### 2. Vérifier l'image déployée

```bash
aws ecs describe-task-definition \
  --region me-central-1 \
  --task-definition arquantix-coming-soon \
  --query 'taskDefinition.containerDefinitions[0].image' \
  --output text
```

**Attendu :** Image avec tag SHA (ex: `...:4f8b7b3...`)

### 3. Vérifier le badge build SHA sur /figma

Visiter `https://<votre-domaine>/figma` et vérifier que le badge en bas à droite affiche le SHA attendu.

### 4. Vérifier les logs CloudWatch

```bash
aws logs tail /ecs/arquantix-coming-soon --region me-central-1 --follow
```

**Attendu :** Pas d'erreurs de connexion ECR, application Next.js démarrée.

---

## 📊 RÉSUMÉ DES ACTIONS PRIORITAIRES

1. **IMMÉDIAT (5 min) :** Exécuter Fix 1 (activer `assignPublicIp: ENABLED`) OU Fix 3 (rollback)
2. **COURT TERME (30 min) :** Exécuter Fix 2 (créer VPC Endpoints) pour une solution sécurisée
3. **MÉDIUM TERME :** Appliquer Fix 4 (améliorer le workflow) pour éviter les blocages futurs
4. **VALIDATION :** Exécuter les "Next checks" pour confirmer que tout fonctionne

---

## 📝 NOTES ADDITIONNELLES

- Le dernier SHA commité est `4f8b7b3`, mais l'image déployée dans la task definition est `0337eafb` (plus ancien). Cela suggère que le workflow a réussi à pousser l'image mais a échoué au déploiement.
- L'ancien déploiement (revision 3, image `latest`) fonctionne car il a probablement été déployé avant que `assignPublicIp` soit désactivé, ou via une autre méthode.
- Les subnets sont configurés avec `mapPublicIpOnLaunch: true`, mais cela ne s'applique pas aux tasks Fargate qui nécessitent explicitement `assignPublicIp: ENABLED` dans la configuration réseau du service.

---

**Rapport généré le :** 2026-01-04  
**Auditeur :** DevOps Audit System

