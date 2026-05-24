# Morpho USDC Volt — Déploiement production ECS (beta contrôlée)

Guide ops pour **app.vancelian.finance** + **console.vancelian.finance** sur AWS ECS Fargate.

**Statut cible** : beta contrôlée (pas rollout large).  
**Prérequis go-live** : 1 dépôt + 1 retrait réels validés en staging, monitoring Healthy, cron installé.

Références :
- [MORPHO_BETA_RUNBOOK.md](./MORPHO_BETA_RUNBOOK.md)
- [MORPHO_PRODUCTION_CHECKLIST.md](./MORPHO_PRODUCTION_CHECKLIST.md)
- [MORPHO_CRON_JOBS.md](./MORPHO_CRON_JOBS.md)
- [VANCELIAN_FINANCE_AWS.md](../vancelian/VANCELIAN_FINANCE_AWS.md)

---

## A. Architecture auditée (ne pas supposer deux services)

| Élément | Valeur prod |
|---------|-------------|
| Région | `us-east-1` |
| Compte AWS | `411714852748` |
| Cluster ECS | `arquantix-cluster` |
| **Service unique** | `vancelian-next` |
| Task family | `vancelian-next` |
| ECR | `411714852748.dkr.ecr.us-east-1.amazonaws.com/vancelian-next` |
| Client app | `https://app.vancelian.finance` |
| Admin / CMS | `https://console.vancelian.finance` |
| ALB | `vancelian-alb` → TG `vancelian-next-tg:3000` |
| CI/CD | `.github/workflows/vancelian-next-deploy.yml` (push `main`) |

**Important** : app et console partagent **le même service ECS** et la **même task definition**. Le routage est host-based (ALB + Next.js).

---

## B. Noms d’env — alignement code

Le code utilise les suffixes `*_USDC` (pas `*_RAW` seuls) pour les plafonds beta :

| Doc utilisateur | Variable réelle (code) |
|-----------------|------------------------|
| `MORPHO_USDC_MIN_DEPOSIT_RAW=10000000` | `MORPHO_USDC_BETA_MIN_DEPOSIT_USDC=10` |
| `MORPHO_USDC_MAX_DEPOSIT_RAW=100000000` | `MORPHO_USDC_BETA_MAX_DEPOSIT_USDC=100` |
| `MORPHO_USDC_MAX_USER_EXPOSURE_RAW=500000000` | `MORPHO_USDC_BETA_MAX_USER_EXPOSURE_USDC=500` |
| `MORPHO_USDC_MAX_GLOBAL_EXPOSURE_RAW=5000000000` | `MORPHO_USDC_BETA_MAX_GLOBAL_EXPOSURE_USDC=5000` |

RPC Base (runtime) :
- Secret : `BASE_RPC_URL` + `NEXT_PUBLIC_BASE_RPC_URL` (même ARN Secrets Manager)
- Fallback code si absent : `https://mainnet.base.org` (**non recommandé prod**)

---

## C. Secrets AWS (Secrets Manager)

### Existants (vérifiés)

| Secret SM | Variable ECS | Service actuel |
|-----------|--------------|----------------|
| `arquantix/prod/database-url` | `DATABASE_URL` | vancelian-next |
| `arquantix/prod/privy-app-id` | `PRIVY_APP_ID` | vancelian-next |
| `arquantix/prod/privy-app-secret` | — | **arquantix-api seulement** → à brancher sur vancelian-next |
| `arquantix/prod/jwt-secret-key` | `JWT_SECRET_KEY`, `AUTH_SECRET` | vancelian-next |

### À créer

| Secret SM | Variable ECS | Notes |
|-----------|--------------|-------|
| `arquantix/prod/base-rpc-url` | `BASE_RPC_URL`, `NEXT_PUBLIC_BASE_RPC_URL` | Alchemy / Infura / QuickNode — **pas** mainnet.base.org seul |

### Variables plain (task definition `environment[]`)

Beta, kill switch, réconciliation — injectées par `scripts/vancelian-sync-morpho-prod.sh`.

---

## D. Procédure de déploiement (ordre strict)

### D.1 — Code sur main

```bash
# Merge Phase 4 Morpho + push main
# → workflow vancelian-next-deploy (image ECR + rolling deploy)
```

Vérifier que `VANCELIAN_PRIVY_APP_ID` est défini dans GitHub Secrets (build `NEXT_PUBLIC_PRIVY_APP_ID`).

### D.2 — Brancher secrets / env Morpho

```bash
cd /path/to/vancelian-app

# Dry-run
DRY_RUN=1 ./scripts/vancelian-sync-morpho-prod.sh

# Prod beta (exemple — remplacer allowlist)
BASE_RPC_URL='https://base-mainnet.g.alchemy.com/v2/XXXX' \
MORPHO_USDC_BETA_ENABLED=true \
MORPHO_USDC_BETA_PERSON_IDS='uuid1,uuid2' \
MORPHO_USDC_BETA_EMAILS='beta1@example.com' \
MORPHO_USDC_DEPOSITS_DISABLED=false \
MORPHO_USDC_WITHDRAWS_DISABLED=false \
./scripts/vancelian-sync-morpho-prod.sh
```

Effet :
- Nouvelle **revision** task definition `vancelian-next`
- Rolling deployment sans downtime
- `PRIVY_APP_SECRET` branché sur vancelian-next

### D.3 — Migrations Prisma (prod)

**Jamais** `prisma db push` en prod.

```bash
./scripts/vancelian-morpho-ecs-run-job.sh migrate
```

Migrations Morpho attendues :
- `20260524180000_add_morpho_vault_ledger`
- `20260524200000_morpho_phase2_reconciliation`

### D.4 — Initialisation Morpho

```bash
./scripts/vancelian-morpho-ecs-run-job.sh sync-registry
./scripts/vancelian-morpho-ecs-run-job.sh backfill    # manuel, post-migration
./scripts/vancelian-morpho-ecs-run-job.sh reconcile
```

Vérifier : https://console.vancelian.finance/admin/morpho-vaults/monitoring → **Healthy** (ou Warning documenté).

### D.5 — Cron production (EventBridge)

```bash
./scripts/vancelian-morpho-eventbridge-setup.sh
```

| Job | Schedule | Commande |
|-----|----------|----------|
| Registry sync | `cron(0 */6 * * ? *)` | `sync-morpho-vault-registry.ts` |
| Réconciliation | `cron(0 6 * * ? *)` | `run-morpho-vault-reconciliation.ts` |
| Backfill | **Manuel** | `backfill-morpho-vault-positions.ts` |

Alternative one-shot : `./scripts/vancelian-morpho-ecs-run-job.sh reconcile`

---

## E. Vérifications domaines & Privy

| Check | URL / action |
|-------|----------------|
| HTTPS app | `curl -sS -o /dev/null -w '%{http_code}' https://app.vancelian.finance/health` → 200 |
| HTTPS console | `https://console.vancelian.finance/health` → 200 |
| Privy allowed origins | Dashboard Privy → `https://app.vancelian.finance` |
| Redirect URLs | Login / embedded wallet callbacks app domain |
| WAF | app/console protégés par allowlist IP équipe |
| Vault publié | CMS `/admin/morpho-vaults` |

---

## F. Smoke tests production beta

### Allowlisté

1. Login Privy sur app.vancelian.finance
2. Invest → Volt USDC visible
3. Dépôt **10 USDC** (min beta)
4. Receipt + ledger `success`
5. Position + historique OK
6. Retrait partiel puis max
7. Monitoring Healthy, pending=0, mismatches critiques=0

### Non allowlisté

- Vaults vides + message beta privée
- Routes API Morpho → 403

### Kill switch (test puis revert)

```bash
MORPHO_USDC_DEPOSITS_DISABLED=true \
MORPHO_USDC_WITHDRAWS_DISABLED=false \
./scripts/vancelian-sync-morpho-prod.sh
```

Vérifier dépôts bloqués, retraits OK. Puis remettre `MORPHO_USDC_DEPOSITS_DISABLED=false`.

---

## G. Rollback

| Niveau | Action |
|--------|--------|
| **Soft** | `MORPHO_USDC_DEPOSITS_DISABLED=true` (retraits actifs) |
| **Hide product** | allowlist vide ou dépublier vaults CMS |
| **Infra** | rollback task definition revision N-1 via ECS console |
| **Interdit** | bloquer retraits sauf urgence on-chain ; `docker compose down -v` ; nouvelle DB |

---

## H. Livrable post-deploy (checklist)

- [ ] ECS service `vancelian-next` — task def revision notée
- [ ] Secrets : `base-rpc-url`, `privy-app-secret` branchés
- [ ] Env beta + réconciliation injectées
- [ ] `prisma migrate deploy` OK
- [ ] sync-registry + reconcile OK
- [ ] EventBridge schedules actifs
- [ ] app + console HTTPS OK
- [ ] smoke dépôt/retrait allowlisté OK
- [ ] kill switch testé
- [ ] monitoring Healthy
- [ ] risques restants documentés

---

## I. État audit (session ops)

Task definition courante au moment de l’audit : `vancelian-next:29`.

**Manquant avant go-live Morpho** :
- `PRIVY_APP_SECRET` non injecté sur vancelian-next (présent sur arquantix-api)
- `BASE_RPC_URL` / secret dédié absent
- Variables Morpho beta / réconciliation absentes
- Code Phase 4 à merger + deploy image
- Cron EventBridge non installé

**Déjà OK** :
- Service ACTIVE (1/1)
- Health 200 app + console
- `DATABASE_URL`, `PRIVY_APP_ID`, JWT, storage branchés
