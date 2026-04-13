# Audit Workspace & Setup Arquantix

## 1. Audit du Workspace (Résumé)

### Ce que je vois

1. **Structure monorepo** avec séparation par services :
   - `services/ganopa-bot/` : Service MaisonGanopa (bot Telegram avec OpenAI)
   - `agent_gateway/` : Gateway pour orchestrer GitHub Actions
   - `agent/` : Agent IA
   - `docs/` : Documentation technique complète (ARCHITECTURE, DECISIONS, RUNBOOK, etc.)
   - `product/` : Brainstorms et plans produit

2. **Infrastructure existante** :
   - Dockerfiles : `services/ganopa-bot/Dockerfile`, `agent_gateway/Dockerfile`
   - GitHub Actions : `.github/workflows/deploy-ganopa-bot.yml` (déploie ganopa-bot sur ECS)
   - AWS ECS Fargate : Cluster `vancelian-dev-api-cluster`, Service `ganopa-dev-bot-svc`
   - ECR : `411714852748.dkr.ecr.me-central-1.amazonaws.com/ganopa-bot`
   - ALB : `api.maisonganopa.com`

3. **Pattern de déploiement** :
   - Chaque service dans `services/{service-name}/`
   - Workflow GitHub Actions par service avec `paths` filter
   - Build Docker → Push ECR → Update ECS

### Risques si on met Arquantix au mauvais endroit

- ❌ **Mélange de marques** : Arquantix et MaisonGanopa dans le même dossier
- ❌ **Workflow déclenché par erreur** : Modifications Arquantix déclenchent le déploiement ganopa-bot
- ❌ **Confusion dans la documentation** : Docs mélangées entre les deux marques
- ❌ **Dockerfile racine** : Un Dockerfile à la racine pourrait créer de la confusion

### Meilleure localisation pour Arquantix

✅ **`services/arquantix/coming-soon/`**

**Justification :**
- Cohérent avec le pattern existant (`services/ganopa-bot/`)
- Séparation claire des marques (Arquantix ≠ MaisonGanopa)
- Workflow GitHub Actions peut filtrer par `paths: services/arquantix/**`
- Prêt pour extension future (`services/arquantix/api/`, `services/arquantix/frontend/`, etc.)

---

## 2. Emplacement Final Choisi

**`services/arquantix/coming-soon/`**

**Structure créée :**
```
services/arquantix/coming-soon/
├── index.html          # Page "Coming Soon" (FR + EN)
├── Dockerfile          # nginx:alpine, port 80
├── README.md          # Documentation build/run
├── .gitignore         # Fichiers à ignorer
└── AUDIT_AND_SETUP.md # Ce fichier
```

---

## 3. Fichiers Créés

### Fichiers Arquantix

1. **`services/arquantix/coming-soon/index.html`**
   - Page HTML statique "Coming Soon"
   - Design sobre et premium
   - FR : "Bientôt disponible"
   - EN : "Coming soon"

2. **`services/arquantix/coming-soon/Dockerfile`**
   - Base : `nginx:alpine`
   - Port : 80
   - Copie `index.html` vers `/usr/share/nginx/html/`

3. **`services/arquantix/coming-soon/README.md`**
   - Instructions build/run local
   - Prochaines étapes ECR/ECS
   - Liste des secrets GitHub requis

4. **`services/arquantix/coming-soon/.gitignore`**
   - `.DS_Store`
   - `*.log`
   - `.dockerignore`

5. **`.github/workflows/arquantix-push-to-ecr.yml`**
   - Workflow GitHub Actions
   - Trigger : push sur `main` ou `arquantix/coming-soon` avec `paths: services/arquantix/**`
   - Build Docker depuis `services/arquantix/coming-soon/`
   - Push vers ECR : `411714852748.dkr.ecr.me-central-1.amazonaws.com/arquantix-coming-soon:latest`

---

## 4. Commandes Git

### État Actuel

✅ **Branche créée** : `arquantix/coming-soon`
✅ **Commit créé** : `fc67b3b` - "feat: add Arquantix coming-soon page and ECR deployment workflow"

### Commandes à Exécuter

```bash
# Vérifier l'état actuel
git status

# Voir les fichiers Arquantix ajoutés
git status --short | grep arquantix

# Push la branche vers GitHub
git push -u origin arquantix/coming-soon

# (Optionnel) Merge dans main si vous voulez
git checkout main
git merge arquantix/coming-soon
git push origin main
```

---

## 5. GitHub Remote

**Remote existant :**
```
origin	https://github.com/geniusga-vancelian/vancelian-app.git
```

**Pas besoin de créer un nouveau repo** - Arquantix est dans le même monorepo que MaisonGanopa, ce qui est cohérent avec la structure existante.

**Si vous voulez un repo séparé (non recommandé pour un monorepo) :**
```bash
# Créer un nouveau repo GitHub
gh repo create arquantix-coming-soon --public --source=. --remote=arquantix

# Ou manuellement via l'UI GitHub
# https://github.com/new
# Nom: arquantix-coming-soon
# Puis: git remote add arquantix https://github.com/geniusga-vancelian/arquantix-coming-soon.git
```

---

## 6. Secrets GitHub Actions Requis

Dans GitHub → Settings → Secrets and variables → Actions, créer :

1. **`AWS_ACCESS_KEY_ID`**
   - Description : AWS Access Key ID pour ECR push
   - Valeur : (votre AWS Access Key ID)

2. **`AWS_SECRET_ACCESS_KEY`**
   - Description : AWS Secret Access Key pour ECR push
   - Valeur : (votre AWS Secret Access Key)

3. **`AWS_REGION`** (optionnel, déjà dans le workflow)
   - Valeur : `me-central-1`

4. **`ECR_REGISTRY`** (optionnel, déjà dans le workflow)
   - Valeur : `411714852748.dkr.ecr.me-central-1.amazonaws.com`

5. **`ECR_REPOSITORY`** (optionnel, déjà dans le workflow)
   - Valeur : `arquantix-coming-soon`

**Note :** Le workflow utilise déjà `AWS_REGION`, `ECR_REGISTRY`, et `ECR_REPOSITORY` comme variables d'environnement. Seuls `AWS_ACCESS_KEY_ID` et `AWS_SECRET_ACCESS_KEY` sont vraiment requis comme secrets.

---

## 7. Prochaines Étapes

### A. Créer le Repository ECR

```bash
aws ecr create-repository \
  --region me-central-1 \
  --repository-name arquantix-coming-soon \
  --image-scanning-configuration scanOnPush=true
```

### B. Déclencher le Workflow GitHub Actions

1. Push la branche : `git push -u origin arquantix/coming-soon`
2. Ou merge dans `main` : le workflow se déclenchera automatiquement
3. Vérifier : https://github.com/geniusga-vancelian/vancelian-app/actions

### C. Créer la Task Definition ECS (optionnel pour l'instant)

```bash
# Template de Task Definition (à adapter)
aws ecs register-task-definition \
  --region me-central-1 \
  --family arquantix-coming-soon \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu 256 \
  --memory 512 \
  --container-definitions '[
    {
      "name": "arquantix-coming-soon",
      "image": "411714852748.dkr.ecr.me-central-1.amazonaws.com/arquantix-coming-soon:latest",
      "portMappings": [{"containerPort": 80, "protocol": "tcp"}],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/arquantix-coming-soon",
          "awslogs-region": "me-central-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]'
```

### D. Créer le Service ECS (optionnel pour l'instant)

```bash
aws ecs create-service \
  --region me-central-1 \
  --cluster vancelian-dev-api-cluster \
  --service-name arquantix-coming-soon-svc \
  --task-definition arquantix-coming-soon \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

---

## 8. Validation

### Test Local

```bash
cd services/arquantix/coming-soon
docker build -t arquantix-coming-soon:local .
docker run -p 8080:80 arquantix-coming-soon:local
# Ouvrir http://localhost:8080
```

### Vérifier le Workflow

1. Push la branche ou merge dans `main`
2. Aller sur : https://github.com/geniusga-vancelian/vancelian-app/actions
3. Vérifier que le workflow "Arquantix - Push to ECR" s'exécute
4. Vérifier que l'image est poussée vers ECR

### Vérifier l'Image ECR

```bash
aws ecr describe-images \
  --region me-central-1 \
  --repository-name arquantix-coming-soon \
  --query 'imageDetails[0].{digest:imageDigest,pushedAt:imagePushedAt,tags:imageTags}' \
  --output json
```

---

**Dernière mise à jour :** 2025-12-30

