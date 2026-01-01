# Arquantix — Coming Soon

Page "Coming Soon" pour Arquantix, déployée via Docker sur AWS ECS.

**Last updated:** 2025-12-30

## Structure

```
services/arquantix/coming-soon/
├── index.html      # Page HTML statique
├── Dockerfile      # Image nginx:alpine
└── README.md       # Ce fichier
```

## Build & Run Local

### Build l'image Docker

```bash
cd services/arquantix/coming-soon
docker build -t arquantix-coming-soon:local .
```

### Run local

```bash
docker run -p 8080:80 arquantix-coming-soon:local
```

Puis ouvrir: http://localhost:8080

### Test rapide avec nginx local

```bash
# Si nginx est installé localement
cd services/arquantix/coming-soon
nginx -p . -c /dev/null -g "daemon off; pid /tmp/nginx.pid; error_log /dev/stderr; access_log /dev/stdout; events { worker_connections 1024; } http { server { listen 8080; root .; index index.html; } }"
```

## Prochaine Étape: Déploiement ECR/ECS

Le workflow GitHub Actions `.github/workflows/arquantix-push-to-ecr.yml` va:

1. Build l'image Docker
2. Push vers ECR: `411714852748.dkr.ecr.me-central-1.amazonaws.com/arquantix-coming-soon:latest`
3. (Optionnel) Update ECS service si configuré

## Configuration ECS (à faire)

1. Créer un ECR repository: `arquantix-coming-soon`
2. Créer une Task Definition ECS (Fargate)
3. Créer un Service ECS pointant vers cette Task Definition
4. Configurer ALB/Route53 si nécessaire

## Secrets GitHub Actions Requis

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION=me-central-1`
- `ECR_REGISTRY=411714852748.dkr.ecr.me-central-1.amazonaws.com`
- `ECR_REPOSITORY=arquantix-coming-soon`

