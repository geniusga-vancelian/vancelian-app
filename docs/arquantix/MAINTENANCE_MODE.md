# Mode maintenance Arquantix — runbook

> Bascule atomique du site `arquantix.com` vers une page d'attente
> sans toucher à l'admin, à l'API ou à la base. Conçu pour les phases
> de déploiement/refactor pendant lesquelles tu veux protéger les
> visiteurs sans casser la stack.

## Principe

```
                       ┌──────────────────────────────────────┐
   arquantix.com:443 → │          ALB arquantix-alb           │
                       └──────────────┬───────────────────────┘
                                      │
       ┌──── Rule prio 50 ────────────┤ Host=arquantix.com Path=/admin*, /api/admin/*,
       │                              │                         /api/site/media/*, /_next/*
       │                              │      → arquantix-web-tg (Next.js)
       │                              │
       │     Rule prio 100 ───────────┤ Host=api.arquantix.com
       │                              │      → arquantix-api-tg (FastAPI)
       │                              │
       │     default action ──────────┤ TOUT le reste
       │                                     │
       │                                     └─ MODE NORMAL  → arquantix-web-tg
       │                                        MODE MAINT.  → arquantix-maintenance-tg (nginx 503)
       │
       └─ La rule prio 50 garantit que /admin et l'API admin sont **toujours** servis
          par le vrai Next.js, même en maintenance. Idem pour les assets `/_next/*`
          afin que la console admin reste fonctionnelle.
```

La bascule atomique est un simple `aws elbv2 modify-listener` qui change la
default action du listener 443. Latence de propagation observée : **5 à 30 s**.

## Composants AWS dédiés

| Ressource | Identifiant | Rôle |
| --- | --- | --- |
| ECR repo | `arquantix-maintenance` | Image nginx alpine + page HTML statique |
| ECS task def | `arquantix-maintenance` | 256 CPU / 512 MB Fargate, port 8080, log group `/ecs/arquantix-maintenance` |
| ECS service | `arquantix-maintenance` | `desiredCount=1` (warm) → bascule instantanée |
| Target group | `arquantix-maintenance-tg` | port 8080 IP, health `/healthz` (200) |
| ALB rule prio 50 | (admin always-on) | Garantit `/admin` + `/api/admin/*` toujours servis |
| ALB rule prio 999 | (placeholder) | Binding TG ↔ ALB requis par ECS, host invalide |

Coût : **~7€/mois** Fargate (0.25 vCPU + 512 MB en permanence). Peut être réduit
en scalant le service à `desiredCount=0` quand pas en maintenance, au prix d'un
cold-start ~60s à la prochaine activation (`maintenance-off.sh --scale-down` puis
`maintenance-on.sh` redémarre automatiquement).

## Customisation du message

L'image nginx fait `envsubst` au démarrage à partir de :

| Variable | Défaut | Usage |
| --- | --- | --- |
| `MAINT_BRAND` | `Arquantix` | Marque (titre + footer) |
| `MAINT_TITLE` | `Site en maintenance` | Titre H1 |
| `MAINT_SUBTITLE` | (long défaut) | Paragraphe descriptif |
| `MAINT_ETA` | `(vide)` | Pastille "Retour estimé : …" (cachée si vide) |

Les valeurs sont injectées via les `environment` de la task def. Le script
`maintenance-on.sh --title ... --subtitle ... --eta ...` enregistre une nouvelle
revision de la task def et force un redeploy ECS.

## Commandes

Toutes prennent `AWS_PROFILE=arquantix-admin` en amont. Scripts disponibles dans
`scripts/aws/maintenance/` :

```bash
cd scripts/aws/maintenance

# Statut courant
AWS_PROFILE=arquantix-admin ./maintenance-status.sh

# Activer (message par défaut)
AWS_PROFILE=arquantix-admin ./maintenance-on.sh

# Activer avec message custom
AWS_PROFILE=arquantix-admin ./maintenance-on.sh \
  --title "Mise à jour technique" \
  --subtitle "Le site sera de retour dans quelques minutes." \
  --eta "10 minutes"

# Désactiver (service maintenance reste warm, ~7€/mois)
AWS_PROFILE=arquantix-admin ./maintenance-off.sh

# Désactiver + scaler à 0 (économie ~7€/mois, cold-start ~60s la fois suivante)
AWS_PROFILE=arquantix-admin ./maintenance-off.sh --scale-down
```

## Smoke tests

Pendant **MAINTENANCE ON**, attendu :

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://arquantix.com/        # 503
curl -s -o /dev/null -w "%{http_code}\n" https://arquantix.com/fr      # 503
curl -s -o /dev/null -w "%{http_code}\n" https://arquantix.com/blog    # 503
curl -s -o /dev/null -w "%{http_code}\n" https://arquantix.com/admin   # 307 (redirect /admin/login)
curl -s -o /dev/null -w "%{http_code}\n" https://arquantix.com/admin/login   # 200
curl -s -o /dev/null -w "%{http_code}\n" https://api.arquantix.com/    # 200
```

Pendant **MAINTENANCE OFF**, attendu :

```bash
curl -sL -o /dev/null -w "%{http_code} %{url_effective}\n" https://arquantix.com/
# → 200 https://arquantix.com/fr
```

## Mise à jour de l'image maintenance

L'image baked-in inclut le logo et le template HTML. Pour modifier le design :

```bash
# 1) Éditer services/arquantix/maintenance/html/index.html.template ou logo.svg
# 2) Build + push
cd services/arquantix/maintenance
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 411714852748.dkr.ecr.us-east-1.amazonaws.com
docker buildx build --platform linux/amd64 \
  -t 411714852748.dkr.ecr.us-east-1.amazonaws.com/arquantix-maintenance:latest \
  --push .

# 3) Force-new-deployment du service maintenance pour pull la nouvelle image
aws ecs update-service --region us-east-1 \
  --cluster arquantix-cluster --service arquantix-maintenance \
  --force-new-deployment
```

Ou via le workflow GitHub `arquantix-maintenance-deploy.yml` (déclenchement manuel).

## Limites & dette

- **Pas d'authentification IP-bypass** : les visiteurs (toi compris) voient le 503
  pendant maintenance. Si tu veux pouvoir tester le vrai site pendant que les
  visiteurs voient le 503, il faut une rule ALB prio 60 avec `source-ip` =
  ton IP publique → web TG. À ajouter au besoin.
- **Pas de CloudFront** : aucun cache CDN à invalider, mais aussi pas de TTFB
  optimisé. Si tu ajoutes CloudFront un jour, il faudra `aws cloudfront
  create-invalidation` après chaque bascule.
- **Cache navigateur** : géré côté Next.js via `headers()` dans
  `next.config.js`. Les pages HTML publiques retournent
  `Cache-Control: no-store, must-revalidate, max-age=0` → les visiteurs
  refetchent le HTML à chaque navigation et voient donc immédiatement la
  bascule maintenance. Les assets `/_next/static/*` gardent leur cache
  immuable (`max-age=31536000, immutable`) — pas d'impact perf.
  L'admin (`/admin/*`) est exclu de cette règle (Next.js applique déjà
  son propre `no-cache` sur les routes authentifiées).
- **Bascule via ALB seulement** : si le DNS Route53 lui-même perd l'ALB, il
  faudra toucher au DNS. Hors scope de ce mécanisme.
