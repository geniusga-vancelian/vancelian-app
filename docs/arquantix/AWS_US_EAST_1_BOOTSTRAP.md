# AWS us-east-1 — Bootstrap Arquantix (web + API + DB)

> Date : mai 2026.
> Statut : **en ligne**.
> Région : **us-east-1** (migration depuis `me-central-1`, bug ECR/KMS).

## URLs en clair

| Cible | URL | Statut |
| --- | --- | --- |
| Site public | https://arquantix.com → `/fr` | HTTP 200 |
| API publique | https://api.arquantix.com | HTTP 200, `{"ok":true,"service":"arquantix-api","version":"2.0.0"}` |
| Admin Next.js | **https://console.arquantix.com/admin/login** (sous-domaine privé) | derrière login + 404 sur `arquantix.com/admin*` |
| ALB | `arquantix-alb-xxxxxxxxx.us-east-1.elb.amazonaws.com` | interne |

## Inventaire AWS

Compte : `411714852748` · Région : `us-east-1` · Profil CLI admin : `arquantix-admin`.

### Réseau & DNS

- VPC default us-east-1 (subnets publics tous AZ).
- ACM certificate `arquantix.com` + `*.arquantix.com` (DNS validation Route53).
- Route53 zone `arquantix.com` :
  - `A arquantix.com` → ALIAS ALB
  - `A api.arquantix.com` → ALIAS ALB
  - `A console.arquantix.com` → ALIAS ALB (sous-domaine privé admin/CMS, voir [SECURE_ADMIN_CONSOLE.md](SECURE_ADMIN_CONSOLE.md))
- ALB `arquantix-alb` (internet-facing).
  - Listener 80 → redirect 443.
  - Listener 443 (cert ACM) :
    - **default forward** → `arquantix-web-tg` (mode normal) ou `arquantix-maintenance-tg` (mode maintenance).
    - Rule prio 30 : `Host=arquantix.com` AND `Path=/admin, /admin/*, /api/admin/*` → **fixed-response 404** (admin fermé sur le domaine public).
    - Rule prio 40 : `Host=console.arquantix.com` → `arquantix-web-tg` (sous-domaine admin privé, toutes routes).
    - Rule prio 50 : `Host=arquantix.com` AND `Path=/api/site/media/*, /_next/*` → `arquantix-web-tg` (assets/média **toujours** servis, même en maintenance).
    - Rule prio 100 : `Host=api.arquantix.com` → `arquantix-api-tg`.
    - Rule prio 999 : (placeholder) host invalide → `arquantix-maintenance-tg` (binding ECS requis).

### Compute

- ECS cluster `arquantix-cluster` (Fargate).
- Service `arquantix-web` :
  - Task def `arquantix-web:3` (image `arquantix-web:latest`).
  - Port container 3000.
  - Command override : `prisma db push --accept-data-loss` puis `prisma db seed` (idempotent, upsert)
    puis `next start`. Le seed lit `ADMIN_SEED_EMAIL` (env) + `ADMIN_SEED_PASSWORD` (Secrets Manager).
  - Storage media injecté via secrets `STORAGE_*` (S3 bucket privé + presigned URLs).
- Service `arquantix-api` :
  - Task def `arquantix-api:5` (image `arquantix-api:latest`).
  - Port container 8000.
  - Env : `ENV=staging`, `APP_ENV=staging`, `AUTH_RL_BACKEND=auto`,
    `SKIP_TWO_FACTOR_CONFIG_GUARD=1`, `ARQUANTIX_ALLOW_UNAUTHENTICATED_APP_ROUTES=1`.
- Service `arquantix-maintenance` :
  - Task def `arquantix-maintenance:N` (image `arquantix-maintenance:latest` — nginx alpine + page 503).
  - Port container 8080.
  - Bascule manuelle via `scripts/aws/maintenance/{maintenance-on,off,status}.sh`.
  - Doc complète : [MAINTENANCE_MODE.md](MAINTENANCE_MODE.md).

### Données

- RDS Postgres 16 `arquantix-db` (db.t4g.micro, 20 Go, encrypted, no public access, deletion-protected).
- ElastiCache Redis 7.1 `arquantix-redis` (cache.t4g.micro, single node).
- ECR : `arquantix-web`, `arquantix-api`, `arquantix-maintenance` (AES256 — pas KMS, contournement bug me-central-1).
- S3 `arquantix-media-prod` (us-east-1, AES256, BlockPublicAccess ON, versioning enabled,
  lifecycle = abort multipart > 7 j). Sert le storage media (uploads admin, blog, projets, mobile DS).
  Accès via IAM user dédié `arquantix-media-uploader` (policy `arquantix-media-uploader-policy`).

### Secrets Manager (`arquantix/prod/*`)

| Nom | Usage |
| --- | --- |
| `database-url` | DSN Postgres (utilisé par API + Web) |
| `redis-url` | DSN Redis |
| `jwt-secret-key` | aliasé en `JWT_SECRET_KEY`, `AUTH_SECRET`, `TWO_FACTOR_TOTP_MASTER_KEY` |
| `admin-password`, `admin-seed-password` | bootstrap admin |
| `openai-api-key` | clé OpenAI (placeholder à remplacer) |
| `storage-bucket-name`, `storage-region`, `storage-endpoint`, `storage-public-url`, `storage-access-key-id`, `storage-secret-access-key` | S3 media (utilisé par Next.js web — `STORAGE_*`) |
| `r2-endpoint`, `r2-access-key-id`, `r2-secret-access-key`, `r2-bucket-name` | Legacy Cloudflare R2 (placeholders, conservés pour compat) |
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

## Storage media — S3 vs R2

Le code applicatif (`services/arquantix/web/src/lib/storage/*`) est désormais agnostique :

- `STORAGE_*` (priorité, prod AWS) : `STORAGE_ENDPOINT`, `STORAGE_ACCESS_KEY_ID`,
  `STORAGE_SECRET_ACCESS_KEY`, `STORAGE_REGION`, `STORAGE_BUCKET_NAME`, `STORAGE_PUBLIC_URL`.
- `R2_*` (fallback, dev local Cloudflare R2) — conservé pour compat.

Le `S3Client` détecte le backend (R2 si endpoint `*.r2.cloudflarestorage.com`, sinon S3) et adapte
`region` et `forcePathStyle` automatiquement. `getPublicUrl()` retourne :
1. `STORAGE_PUBLIC_URL` si défini, sinon
2. URL R2 (`pub-<account>.r2.dev/<key>`) si backend R2, sinon
3. URL S3 régionale (`<bucket>.s3.<region>.amazonaws.com/<key>`).

Le bucket prod est privé : ces URLs sont utilisées en input du presigning ou du proxy
`/api/site/media/[id]` ; un GET direct retourne 403 (attendu).

Tests e2e validés (mai 2026) : login admin → `POST /api/admin/media/upload` → row en DB
+ objet en S3 → `GET /api/site/media/[id]` (200) → `GET /api/admin/media/[id]/file` (200).

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
