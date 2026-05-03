# GitHub Actions ↔ AWS — Setup OIDC

Guide opérationnel pour passer les workflows de déploiement (`arquantix-*-deploy.yml`,
`arquantix-push-to-ecr.yml`) au vert après la réactivation du compte AWS
`411714852748` (région `me-central-1`).

Cible : **OIDC** (federated identity GitHub → IAM role), pas d'access keys
statiques. Plus aucun secret long-vie à rotater.

---

## 0. Vue d'ensemble

```
┌────────────────────┐     ID token (JWT)      ┌──────────────────────────────┐
│ GitHub Actions run │ ───────────────────────▶│ token.actions.githubusercontent.com │
│  (workflow YAML)   │                         └──────────────────────────────┘
│                    │                                       │ trust
│                    │                                       ▼
│                    │                       ┌────────────────────────────────┐
│                    │ ◀──── credentials ─── │ AWS IAM Role:                  │
│                    │   STS AssumeRoleWith- │   arquantix-github-actions-    │
│                    │   WebIdentity (1h)    │   deployer                     │
└────────────────────┘                       └────────────────────────────────┘
                                                          │ inline policy
                                                          ▼
                                                  ECR push/pull + ECS deploy
                                                  (scoped to arquantix-*)
```

**Tu fais 4 étapes une fois :**

| Phase | Acteur | Effort |
|-------|--------|--------|
| A — récupérer un access key admin temporaire | toi (AWS Console) | 5 min |
| B — exécuter le script bootstrap OIDC + role | toi (terminal local) | 2 min |
| C — coller l'ARN dans un secret GitHub repo | toi (GitHub UI ou CLI) | 1 min |
| D — déclencher un workflow et valider | toi (GitHub UI) | 5 min |

Après ça, **tous tes pushs sur `main` qui touchent `services/arquantix/**` déclenchent
les deploys, qui passent au vert sans aucune intervention manuelle.**

---

## Phase A — Récupérer un accès AWS admin temporaire

Le compte est UP mais ton ancienne access key locale est invalide
(`InvalidClientTokenId`). Régénère-la :

1. Connecte-toi à la **AWS Console** : <https://console.aws.amazon.com>
   - Sign-in : compte `411714852748` (root user **OU** mieux : un user IAM admin si tu en as un).
2. Va dans **IAM** → **Users** → ton user (ou crée-en un avec policy `AdministratorAccess` si nécessaire).
3. Onglet **Security credentials** → **Create access key**
   - Use case : *Command Line Interface (CLI)*
   - Tag : `bootstrap-arquantix-oidc-2026-05` (pour s'en souvenir et la révoquer ensuite).
4. Note l'access key ID + secret access key (NE LES PARTAGE PAS).
5. Configure-les en local :

   ```bash
   aws configure
   # AWS Access Key ID    : <colle ici>
   # AWS Secret Access Key: <colle ici>
   # Default region name  : me-central-1
   # Default output format: json
   ```

6. Vérifie :

   ```bash
   aws sts get-caller-identity
   ```

   Attendu :

   ```json
   {
     "UserId":  "...",
     "Account": "411714852748",
     "Arn":     "arn:aws:iam::411714852748:user/<ton-user>"
   }
   ```

> Cette access key admin n'est utilisée que pour la Phase B. **Tu la révoqueras à la fin** (Phase E).

---

## Phase B — Bootstrap OIDC provider + IAM role

Tout est packagé dans un script idempotent. Tu peux le relancer 100 fois sans casser.

```bash
cd /Users/gael/dev/vancelian-app
./scripts/aws/github-oidc/setup.sh
```

Variables d'environnement reconnues (toutes ont des défauts adaptés à ce repo) :

| Var | Défaut | Description |
|-----|--------|-------------|
| `AWS_ACCOUNT_ID` | `411714852748` | Compte cible |
| `AWS_REGION` | `me-central-1` | Région des ressources ECR/ECS |
| `GITHUB_OWNER` | `geniusga-vancelian` | Owner du repo |
| `GITHUB_REPO` | `vancelian-app` | Nom du repo |
| `ROLE_NAME` | `arquantix-github-actions-deployer` | Nom du role IAM créé |

Le script :

1. Crée (ou détecte) le **OIDC provider** AWS pour `token.actions.githubusercontent.com`.
2. Crée (ou met à jour) un **IAM Role** `arquantix-github-actions-deployer` avec :
   - **Trust policy** : `sts:AssumeRoleWithWebIdentity` autorisé uniquement pour
     les workflows du repo `geniusga-vancelian/vancelian-app` (toutes branches).
   - **Inline policy** scopée :
     - `ecr:*` (limité aux repos `arn:aws:ecr:me-central-1:411714852748:repository/arquantix-*`)
     - `ecs:Describe*` / `Register*` / `Update*` (cluster + services + task defs)
     - `iam:PassRole` (uniquement vers `ecsTaskExecutionRole` et `arquantix-*-task-role`)
     - `logs:Describe*` (log groups `/ecs/arquantix-*`)

À la fin il imprime l'ARN du role à coller dans GitHub :

```
Role ARN: arn:aws:iam::411714852748:role/arquantix-github-actions-deployer
```

---

## Phase C — Ajouter le secret `AWS_ROLE_ARN` sur le repo

**Une seule valeur** à configurer (vs deux secrets dans l'ancien modèle). Deux options.

### C.1 — Via GitHub Web UI (le plus simple)

1. Va sur <https://github.com/geniusga-vancelian/vancelian-app/settings/secrets/actions/new>
2. Champs :
   - **Name** : `AWS_ROLE_ARN`
   - **Secret** : `arn:aws:iam::411714852748:role/arquantix-github-actions-deployer`
3. **Add secret**
4. (optionnel) Supprime les anciens secrets `AWS_ACCESS_KEY_ID` et `AWS_SECRET_ACCESS_KEY`
   s'ils existent encore — ils ne sont plus utilisés et ils sont une surface d'attaque inutile.

### C.2 — Via gh CLI (si tu préfères le terminal)

```bash
brew install gh        # déjà fait dans cet env si tu suis depuis le début
gh auth login          # flow interactif browser
gh secret set AWS_ROLE_ARN \
  --repo geniusga-vancelian/vancelian-app \
  --body "arn:aws:iam::411714852748:role/arquantix-github-actions-deployer"

gh secret list --repo geniusga-vancelian/vancelian-app | grep AWS_ROLE_ARN
```

---

## Phase D — Vérifier l'infra AWS et déclencher un test

### D.1 — Inventaire (read-only, pas de mutation)

```bash
./scripts/aws/github-oidc/inventory.sh
```

Sortie attendue (exemple) :

```
ECR repositories (region me-central-1):
  [OK]   arquantix-web   (411714852748.dkr.ecr.me-central-1.amazonaws.com/arquantix-web)
  [OK]   arquantix-api   (...)
  [OK]   arquantix-coming-soon (...)

ECS cluster:
  [OK]   arquantix-cluster (status=ACTIVE)

ECS services in arquantix-cluster:
  [OK]   arquantix-coming-soon (taskDef=arquantix-coming-soon:42)
  ...

GitHub Actions OIDC integration:
  [OK]   OIDC provider arn:aws:iam::411714852748:oidc-provider/...
  [OK]   Deployer role arquantix-github-actions-deployer
         ARN: arn:aws:iam::411714852748:role/arquantix-github-actions-deployer
```

Si tu vois `[MISS] arquantix-web (run: aws ecr create-repository ...)`, c'est que ECR
a été purgé pendant la suspension du compte. Recrée juste les repos manquants
avec la commande affichée — c'est gratuit, pas de mutation destructive.

### D.2 — Test du workflow le plus simple

Le bon premier test, c'est `arquantix-api-deploy.yml` (juste un push d'image,
pas de déploiement ECS). Lance-le manuellement :

1. <https://github.com/geniusga-vancelian/vancelian-app/actions/workflows/arquantix-api-deploy.yml>
2. Bouton **Run workflow** → branche `main` → **Run**.
3. Tu dois voir :
   - `Configure AWS credentials (OIDC)` ✓
   - `Login to Amazon ECR` ✓
   - `Build Docker image` ✓ (~1-2 min)
   - `Push Docker image to ECR` ✓
   - `Verify image in ECR` ✓

Si l'étape OIDC échoue avec `Could not assume role`, vérifie en CLI :

```bash
aws sts assume-role-with-web-identity \
  --role-arn arn:aws:iam::411714852748:role/arquantix-github-actions-deployer \
  --role-session-name local-dryrun \
  --web-identity-token "$(echo dummy)" 2>&1 | head -3
```

(Erreur `InvalidIdentityToken` est normal en local — ça prouve juste que le
role accepte la fédération. Le vrai test c'est dans GitHub Actions.)

### D.3 — Test du workflow ECS (`coming-soon-deploy`)

Plus exigeant car il déploie réellement sur ECS. Pré-requis :

- Le service ECS `arquantix-coming-soon` existe sur `arquantix-cluster` (vérifié par
  `inventory.sh`).
- Le service a un placeholder de task definition (le workflow récupère l'existante,
  remplace l'image, et redéploie).

Lance-le ensuite : <https://github.com/geniusga-vancelian/vancelian-app/actions/workflows/arquantix-coming-soon-deploy.yml>

---

## Phase E — Cleanup

Une fois tout au vert (Phase D OK), nettoie :

1. **Révoque l'access key admin temporaire** créée en Phase A.1 :
   - IAM → Users → ton user → Security credentials → l'access key tagguée
     `bootstrap-arquantix-oidc-2026-05` → **Make inactive** puis **Delete**.
2. **Supprime les anciens secrets** GitHub (s'ils existent encore) :
   ```bash
   gh secret delete AWS_ACCESS_KEY_ID    --repo geniusga-vancelian/vancelian-app
   gh secret delete AWS_SECRET_ACCESS_KEY --repo geniusga-vancelian/vancelian-app
   ```
3. **Vérifie** que `aws configure list` ne contient plus la access key admin
   (tu peux la garder en local si tu veux, mais c'est plus propre de tout passer
   en SSO ou de générer un user IAM moins privilégié pour ton dev courant).

---

## Annexes

### A.1 — Rotation des credentials

Avec OIDC il n'y a **plus rien à rotater**. Les credentials sont émis à la volée
par STS pour chaque run, durée maximale 1h, jamais stockés.

### A.2 — Ajouter un nouveau workflow déployant sur AWS

Copie le pattern OIDC d'un workflow existant :

```yaml
permissions:
  contents: read
  id-token: write   # OBLIGATOIRE pour OIDC

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          role-session-name: gha-<workflow-name>-${{ github.run_id }}
          aws-region: me-central-1
      # ... reste des steps
```

### A.3 — Restreindre la trust policy à `main` uniquement

Par défaut le script autorise toutes les branches du repo (`repo:owner/repo:*`).
Si tu veux restreindre à `main` :

```bash
# Édite scripts/aws/github-oidc/trust-policy.json.template :
# remplace
#   "repo:__GITHUB_OWNER__/__GITHUB_REPO__:*"
# par
#   "repo:__GITHUB_OWNER__/__GITHUB_REPO__:ref:refs/heads/main"
# Puis relance:
./scripts/aws/github-oidc/setup.sh   # met à jour la trust policy in-place
```

### A.4 — Élargir les permissions

Pour donner accès à un nouveau service AWS (ex. S3 d'assets, CloudFront invalidation,
RDS), édite `scripts/aws/github-oidc/permissions-policy.json.template` puis re-run
`setup.sh`. Le `aws iam put-role-policy` remplace la policy in-place.

---

## Annexe B — Known issue : `me-central-1` post-suspension (AWS support ticket)

**Symptôme** : tous les pushes ECR vers `me-central-1` échouent avec :

```
denied: The Amazon ECR action failed due to a KMS exception: AccessDenied
```

…même depuis un user IAM admin avec `AdministratorAccess`. L'erreur survient
au push docker, après que `aws ecr get-login-password` + `docker login` aient
réussi. Touche tous les repos ECR de la région (existants comme nouveaux),
indépendamment du tag mutability ou de l'encryption type (AES256 ou KMS).

**Cause confirmée par diagnostic** : l'infrastructure ECR de `me-central-1`
sur le compte `411714852748` est dans un état dégradé suite à la suspension
puis réactivation du compte (facture impayée puis payée). Les **AWS-owned
KMS keys** que ECR utilise pour AES256 ne sont pas correctement provisionnées
sur cette région.

**Validation** : un push test vers `us-east-1` (sur un repo de test)
fonctionne **sans aucun changement de policy**, prouvant que :

- la policy IAM du role est correcte ;
- l'OIDC GitHub ↔ AWS fonctionne ;
- le bug est strictement régional, lié à l'état du compte AWS.

### Comment ouvrir le ticket AWS Support

URL : <https://console.aws.amazon.com/support/home#/case/create>

- **Type** : *Technical*
- **Service** : *Elastic Container Registry (ECR)*
- **Category** : *Repository Issue*
- **Severity** : *General guidance* ou *System impaired* selon l'urgence

**Sujet suggéré** :

> ECR push fails with "KMS exception: AccessDenied" in me-central-1 after account reactivation

**Corps suggéré** (à coller / adapter) :

```
Hello AWS Support,

After my AWS account 411714852748 was suspended for unpaid invoice and then
reactivated (paid in full on 2026-05-XX), all ECR push operations in region
me-central-1 fail with the following error:

  denied: The Amazon ECR action failed due to a KMS exception: AccessDenied

This happens for both pre-existing repositories and brand new ones, with
encryption type AES256 (no customer KMS key involved). It also happens when
the caller is the root user or an IAM user with full AdministratorAccess —
so it cannot be a missing IAM permission on my side.

Verified facts:

- ECR Login (`aws ecr get-login-password` + `docker login`) succeeds.
- The same `docker push` command using the same image succeeds in us-east-1
  on a test repository created on the same account.
- The IAM role used in the original failure has full ECR + KMS permissions
  (verified via `aws iam simulate-principal-policy` — all actions return
  "allowed" against the target ECR resource ARN).
- ECR repos `arquantix-coming-soon`, `arquantix-web`, `arquantix-api` in
  me-central-1 all exhibit the bug.

Please verify the state of the AWS-owned KMS keys backing ECR default
AES256 encryption in me-central-1 for this account, and reset/refresh them
if needed. I suspect they were not correctly re-provisioned during account
reactivation.

Affected resources:
- Account ID:        411714852748
- Region:            me-central-1 (Bahrain)
- ECR repositories:  arquantix-coming-soon, arquantix-web, arquantix-api

Thanks!
```

### Que faire en attendant la résolution

- **Le code est sain** : la migration OIDC + le fix du YAML cassé ont été
  validés (toutes les étapes fonctionnent jusqu'au `Push Docker image to
  ECR`). Dès qu'AWS répare la région, **les workflows passeront au vert
  sans aucune intervention** — pas besoin de relancer un push.
- Si les fails rouges sur la page Actions te dérangent, tu peux désactiver
  temporairement les 4 workflows en ajoutant `if: false` au job, ou en
  commentant le bloc `on.push` (ne garder que `workflow_dispatch`).
- Tu peux re-trigger manuellement un workflow (`workflow_dispatch`) à tout
  moment pour vérifier si AWS a réparé : <https://github.com/geniusga-vancelian/vancelian-app/actions>

### Comment savoir si AWS a réparé

Test minimal local (depuis ta machine, avec le profil `arquantix-admin`) :

```bash
aws ecr get-login-password --region me-central-1 \
  | docker login --username AWS --password-stdin 411714852748.dkr.ecr.me-central-1.amazonaws.com
docker pull alpine:3.19
docker tag alpine:3.19 411714852748.dkr.ecr.me-central-1.amazonaws.com/arquantix-web:probe
docker push 411714852748.dkr.ecr.me-central-1.amazonaws.com/arquantix-web:probe
```

Si le `docker push` réussit → AWS a réparé, tu peux re-trigger les workflows
GitHub Actions et tout passera.
