# Matrice CI / deploy — `services/arquantix/web`

Le code Next.js sous `services/arquantix/web/` alimente plusieurs cibles (portail app, console admin, coming-soon legacy). **Un push `main` ne doit pas tout redeployer.**

## Politique (depuis mai 2026)

| Workflow | Déclencheur | Cible | Rôle |
|----------|-------------|-------|------|
| **Vancelian Next - Deploy to ECS** | `push` → `main` + paths `web/**` | ECS `vancelian-next` · `app.vancelian.finance` | **Deploy auto prod portail** |
| **Arquantix Web CI** | `pull_request` + paths `web/**` | — | Lint / typecheck / tests avant merge |
| **Arquantix Web - Deploy to ECS** | `workflow_dispatch` | ECS `arquantix-web` · `console.vancelian.finance` | Deploy console **manuel** |
| **Arquantix Coming Soon** | `workflow_dispatch` | ECS `arquantix-coming-soon` · me-central-1 | Legacy **manuel** |
| **Arquantix - Push to ECR** | `workflow_dispatch` | ECR `arquantix-coming-soon` | Legacy **manuel** |
| **Arquantix API (FastAPI) - Build & push ECR** | `push` → paths `api/**` | ECS `arquantix-api` + **`arquantix-market-ws`** (Binance quotes WS) | Deploy auto API + worker marché |

## Pourquoi plusieurs workflows existaient

Historiquement, un seul dossier `services/arquantix/web/` servait plusieurs produits. Chaque workflow écoutait `services/arquantix/web/**` → **un commit portail déclenchait 4 builds Docker** (vancelian-next, arquantix-web, coming-soon, push ECR) + CI, avec des échecs parasites sur des cibles non concernées.

## Deploy manuel (GitHub Actions)

1. Ouvrir [Actions](https://github.com/geniusga-vancelian/vancelian-app/actions).
2. Choisir le workflow (ex. **Arquantix Web - Deploy to ECS**).
3. **Run workflow** → branche `main` → tag image optionnel (défaut : SHA du commit).

### Console admin après un fix portail

Si le changement doit aussi être visible sur `console.vancelian.finance` :

```
Actions → Arquantix Web - Deploy to ECS → Run workflow
```

### Coming-soon / ECR legacy

Uniquement si besoin explicite (pages statiques / infra me-central-1) :

```
Actions → Arquantix Coming Soon - Deploy to ECR & ECS
Actions → Arquantix - Push to ECR
```

## Chemins surveillés (auto-deploy portail)

`vancelian-next-deploy.yml` se déclenche sur :

- `services/arquantix/web/**`
- `services/arquantix/mobile/assets/crypto_svgs/**`
- `.github/workflows/vancelian-next-deploy.yml`

## Jobs prod one-shot (migrations, seed Ledgity, etc.)

Voir aussi :

- `scripts/vancelian-morpho-ecs-run-job.sh` — migrate, ledgity-seed, ledgity-reconcile
- `scripts/vancelian-import-ledgity-vault-configs-prod.sh`
- `scripts/vancelian-sync-ledgity-prod.sh`

## Évolution possible

Si console et portail divergent durablement :

- scinder le code (`services/vancelian/web` vs packages partagés), ou
- orchestrateur unique avec détection de changement / label de commit `[deploy:console]`.
