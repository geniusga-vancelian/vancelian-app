# AWS us-east-1 — Bootstrap Arquantix (web + API + DB)

> Date : mai 2026.
> Statut : **en ligne**.
> Région : **us-east-1** (migration depuis `me-central-1`, bug ECR/KMS).

## URLs en clair

| Cible | URL | Statut |
| --- | --- | --- |
| Site public | https://arquantix.com → `/fr` | HTTP 200 |
| API publique | https://api.arquantix.com | HTTP 200, `{"ok":true,"service":"arquantix-api","version":"2.0.0"}` |
| Admin Next.js | https://arquantix.com/admin | derrière login |
| ALB | `arquantix-alb-xxxxxxxxx.us-east-1.elb.amazonaws.com` | interne |

## Inventaire AWS

Compte : `411714852748` · Région : `us-east-1` · Profil CLI admin : `arquantix-admin`.

### Réseau & DNS

- VPC default us-east-1 (subnets publics tous AZ).
- ACM certificate `arquantix.com` + `*.arquantix.com` (DNS validation Route53).
- Route53 zone `arquantix.com` :
  - `A arquantix.com` → ALIAS ALB
  - `A api.arquantix.com` → ALIAS ALB
- ALB `arquantix-alb` (internet-facing).
  - Listener 80 → redirect 443.
  - Listener 443 (cert ACM) :
    - default forward → `arquantix-web-tg`.
    - Rule `Host = api.arquantix.com` → `arquantix-api-tg`.

### Compute

- ECS cluster `arquantix-cluster` (Fargate).
- Service `arquantix-web` :
  - Task def `arquantix-web:2` (image `arquantix-web:latest`).
  - Port container 3000.
  - Command override : `npx prisma db push --skip-generate --accept-data-loss && npm run start`.
- Service `arquantix-api` :
  - Task def `arquantix-api:5` (image `arquantix-api:latest`).
  - Port container 8000.
  - Env : `ENV=staging`, `APP_ENV=staging`, `AUTH_RL_BACKEND=auto`,
    `SKIP_TWO_FACTOR_CONFIG_GUARD=1`, `ARQUANTIX_ALLOW_UNAUTHENTICATED_APP_ROUTES=1`.

### Données

- RDS Postgres 16 `arquantix-db` (db.t4g.micro, 20 Go, encrypted, no public access, deletion-protected).
- ElastiCache Redis 7.1 `arquantix-redis` (cache.t4g.micro, single node).
- ECR : `arquantix-web`, `arquantix-api` (AES256 — pas KMS, contournement bug me-central-1).

### Secrets Manager (`arquantix/prod/*`)

| Nom | Usage |
| --- | --- |
| `database-url` | DSN Postgres (utilisé par API + Web) |
| `redis-url` | DSN Redis |
| `jwt-secret-key` | aliasé en `JWT_SECRET_KEY`, `AUTH_SECRET`, `TWO_FACTOR_TOTP_MASTER_KEY` |
| `admin-password`, `admin-seed-password` | bootstrap admin |
| `openai-api-key` | clé OpenAI (placeholder à remplacer) |
| `r2-endpoint`, `r2-access-key-id`, `r2-secret-access-key`, `r2-bucket-name` | Cloudflare R2 (placeholders) |
| `google-maps-api-key` | placeholder |
| `db-password` | mdp brut RDS (debug) |

### IAM

- `ecsTaskExecutionRole` : trust ECS + policies `AmazonECSTaskExecutionRolePolicy` + `SecretsManagerReadWrite`.
- `arquantix-github-actions-deployer` : OIDC GitHub `vancelian-com/arquantix`, policies ECR push + ECS update + KMS via ECR + CloudWatch logs (multi-régions wildcards).

## Workflows GitHub Actions

Branches déclenchantes : `main` push pour `arquantix-web-deploy.yml` et `arquantix-api-deploy.yml`.
`coming-soon` et `push-to-ecr` : `workflow_dispatch` uniquement.

Région : `us-east-1`. Registry : `411714852748.dkr.ecr.us-east-1.amazonaws.com`.

Étapes web :
1. Build image (avec `--build-arg NEXT_PUBLIC_API_URL=https://api.arquantix.com`, etc.).
2. Push ECR (`<sha>` + `latest`).
3. Render task def (download → patch image → register).
4. Deploy ECS (`amazon-ecs-deploy-task-definition`, wait stabilité).

Étapes API : identique mais sans build args et avec port 8000.

## Runbook ops courant

### Forcer un redeploy sans nouveau build

```bash
aws ecs update-service --region us-east-1 \
  --cluster arquantix-cluster \
  --service arquantix-api \
  --force-new-deployment
```

### Voir les logs récents

```bash
aws logs tail /ecs/arquantix-api --region us-east-1 --since 10m --follow
aws logs tail /ecs/arquantix-web --region us-east-1 --since 10m --follow
```

### Smoke

```bash
curl -sI https://arquantix.com/ | head -1
curl -s https://api.arquantix.com/
```

### État des tâches

```bash
aws ecs describe-services --region us-east-1 \
  --cluster arquantix-cluster \
  --services arquantix-api arquantix-web \
  --query 'services[].{Name:serviceName,Running:runningCount,Pending:pendingCount,Desired:desiredCount,TaskDef:taskDefinition}'
```

## Limites / dette connues

- **2FA prod désactivée** via `SKIP_TWO_FACTOR_CONFIG_GUARD=1` (env `staging`).
  → à activer quand `TWO_FACTOR_TOTP_MASTER_KEY` (32+ chars), `TWILIO_*`, `SES_FROM_EMAIL` seront provisionnés et basculer `ENV=production`.
- **OpenAI / Google Maps / R2** : secrets en placeholder. Recopier les valeurs réelles depuis `.env.arquantix` :

  ```bash
  aws secretsmanager update-secret --region us-east-1 \
    --secret-id arquantix/prod/openai-api-key \
    --secret-string "sk-..."
  ```

- **Pas d'auto-scaling** : 1 task par service. Suffisant pour le trafic actuel.
- **Pas de WAF** ni Shield Advanced.
- **DB et Redis sans réplica multi-AZ** (db.t4g.micro single-AZ).
- **Vancelian app** non encore branchée — voir `VANCELIAN_DEV_DISTRIBUTION.md` (à venir).

## Migration future Arquantix ↔ Vancelian

Un seul code, deux contextes. Aujourd'hui, l'API et la base servent les deux. Quand Vancelian
sortira en prod indépendante :

1. Cluster Fargate dédié `vancelian-cluster` (mêmes images).
2. RDS dédié `vancelian-db` + Redis dédié.
3. Domaines `vancelian.com` / `api.vancelian.com` + ACM + Route53 séparés.
4. Secrets Manager `vancelian/prod/*` (avec `ARQUANTIX_ENV=production` mais `BRAND=vancelian`).

L'isolation se fait par stack AWS, pas par modification du code applicatif.
