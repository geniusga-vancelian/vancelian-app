# Morpho USDC Volt — Checklist production

À valider **avant ouverture beta client** (petit groupe), puis avant rollout large.

Références :
- Runbook staging : [MORPHO_STAGING_RUNBOOK.md](./MORPHO_STAGING_RUNBOOK.md)
- Cron jobs : [MORPHO_CRON_JOBS.md](./MORPHO_CRON_JOBS.md)
- Privy prod : [PRIVY_PROD_GO_LIVE.md](./PRIVY_PROD_GO_LIVE.md)

---

## 1. Migrations & données

- [ ] Migration `20260524120000_add_portal_morpho_vault_config` appliquée
- [ ] Migration `20260524180000_add_morpho_vault_ledger` appliçée
- [ ] Migration `20260524200000_morpho_phase2_reconciliation` appliquée
- [ ] Vaults publiés configurés en CMS (`portal_morpho_vault_configs`)
- [ ] `pnpm morpho:sync-vault-registry` exécuté post-deploy
- [ ] `pnpm morpho:backfill-positions` exécuté (migration clients existants)
- [ ] Première réconciliation : `pnpm morpho:reconcile` → mismatches investigués

---

## 2. Variables d'environnement (web BFF)

| Variable | Obligatoire | Description |
|----------|-------------|-------------|
| `DATABASE_URL` | Oui | PostgreSQL prod |
| `JWT_SECRET_KEY` ou `AUTH_SECRET` | Oui | JWT portail (`person_id`) |
| `NEXT_PUBLIC_BASE_RPC_URL` | Recommandé | RPC Base prod (Alchemy/Infura) — **pas** public node seul |
| `PRIVY_APP_SECRET` | Si `privy_earn` | API Privy Earn server-side |
| `NEXT_PUBLIC_PRIVY_APP_ID` | Oui | Client Privy |
| `MORPHO_RECONCILIATION_TOLERANCE_RAW` | Non | Défaut `10` (raw USDC units). Max recommandé : 100 |
| `MORPHO_ALERT_MISMATCH_TOLERANCE_RAW` | Non | Défaut `1000000` (= 1 USDC) |
| `MORPHO_PENDING_ALERT_MINUTES` | Non | Défaut `15` |

---

## 3. Infra externe

- [ ] **RPC Base prod** configuré, latence < 500 ms, quota suffisant
- [ ] **Morpho GraphQL** accessible (`https://api.morpho.org/graphql`)
- [ ] **Privy gas sponsorship Base** actif pour embedded wallets
- [ ] **PRIVY_APP_SECRET** actif si routes `/api/portal/privy/earn/*` utilisées
- [ ] Sponsoring tx : `sendTransaction` avec `sponsor: true` validé en prod

---

## 4. Cron / jobs récurrents

- [ ] Cron registry sync : toutes les **6h** (`pnpm morpho:sync-vault-registry`)
- [ ] Cron réconciliation : **quotidien 06:00 UTC** (`pnpm morpho:reconcile`)
- [ ] Backfill : **manuel uniquement** (post-migration ou incident)
- [ ] Logs cron redirigés vers fichier/monitoring (exit code ≠ 0 → alerte)

Voir [MORPHO_CRON_JOBS.md](./MORPHO_CRON_JOBS.md) pour exemple crontab.

---

## 5. Monitoring & alertes

- [ ] `/admin/morpho-vaults/monitoring` accessible (auth admin)
- [ ] Statut global **Healthy** avant go-live
- [ ] Aucune alerte **Critical** non résolue :
  - `morpho_graphql_unavailable`
  - `base_rpc_unavailable`
  - `pending_tx_stale` (≥ 3 → critical)
  - `reconciliation_mismatch_significant` (> 1 USDC)
- [ ] Alertes **Warning** documentées si acceptées (cost_basis_unknown, minor mismatch)

---

## 6. Tests fonctionnels prod (smoke)

- [ ] Runbook staging rejoué sur prod avec **1 USDC** max
- [ ] Dépôt + retrait partiel validés par un opérateur
- [ ] Disclaimer visible au 1er dépôt
- [ ] Double-submit impossible (UI)
- [ ] Wallet ownership : impossible d'utiliser un `privy_wallet_id` d'un autre user (403)
- [ ] Vault non publié → 404

---

## 7. Sécurité & conformité

- [ ] Idempotency obligatoire sur prepare/deposit/withdraw
- [ ] Receipt verification stricte avant « Confirmed »
- [ ] Pas de `0 USDC` hardcodé pour le rendement
- [ ] Disclaimers DeFi visibles (risques smart contract, liquidité, APY variable)

---

## 8. Rollback plan

En cas d'incident prod :

1. **Dépublier** tous les vaults Morpho (`isPublished = false`) — effet immédiat portail
2. **Ne pas** supprimer le ledger (`onchain_vault_transactions`) — audit trail
3. Communiquer aux beta users : retraits possibles si vault encore on-chain (direct Morpho)
4. Investiguer via monitoring + `pnpm morpho:reconcile`
5. Fix forward + republish vault par vault après validation staging

**Rollback code** : redeploy version précédente Next.js — migrations Prisma non destructives (pas de `down` en prod sans validation).

---

## 9. Sign-off

| Rôle | Nom | Date | OK |
|------|-----|------|-----|
| Dev / intégration | | | |
| QA staging runbook | | | |
| Ops (cron + env) | | | |
| Produit / compliance | | | |

**Décision** : ☐ Beta ouverte ☐ Reporté — motif : _______________
