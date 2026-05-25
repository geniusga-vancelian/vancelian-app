# Morpho USDC Volt — Checklist production

À valider **avant ouverture beta client**, puis avant rollout large.

## Architecture cible

```text
Privy              = login + embedded wallet optionnel
Reown / WalletConnect = wallets externes (MetaMask)
Morpho             = direct_morpho uniquement
Vancelian          = ledger + registry + reconciliation + monitoring
```

Références :
- Runbook beta : [MORPHO_BETA_RUNBOOK.md](./MORPHO_BETA_RUNBOOK.md)
- Runbook staging : [MORPHO_STAGING_RUNBOOK.md](./MORPHO_STAGING_RUNBOOK.md)
- Cron jobs : [MORPHO_CRON_JOBS.md](./MORPHO_CRON_JOBS.md)
- Sandbox local : [MORPHO_LOCAL_SANDBOX.md](./MORPHO_LOCAL_SANDBOX.md)
- Privy login : [PRIVY_PROD_GO_LIVE.md](./PRIVY_PROD_GO_LIVE.md)

---

## 1. Migrations & données

- [ ] Migration `20260524120000_add_portal_morpho_vault_config` appliquée
- [ ] Migration `20260524180000_add_morpho_vault_ledger` appliquée
- [ ] Migration `20260524200000_morpho_phase2_reconciliation` appliquée
- [ ] Migration `20260525120000_add_portal_external_wallet_nonces` appliquée
- [ ] Vaults publiés en CMS — **`direct_morpho` uniquement** (`is_published = true`)
- [ ] Aucun vault **`privy_earn` publié** (legacy autorisé en `is_published = false`)
- [ ] `pnpm morpho:sync-vault-registry` exécuté post-deploy
- [ ] `pnpm morpho:backfill-positions` exécuté si migration clients existants
- [ ] Première réconciliation : `pnpm morpho:reconcile` → mismatches investigués

### Données legacy (lecture seule)

Les anciennes transactions ledger `integration_mode = privy_earn` et colonnes associées (`privy_action_id`, etc.) sont des **données historiques en lecture seule**.  
**Ne pas supprimer.** Toute nouvelle exécution Morpho utilise `direct_morpho` avec `wallet_source` = `privy_embedded` ou `external_evm`.

---

## 2. Variables d'environnement (web BFF)

### Obligatoires prod

| Variable | Valeur attendue |
|----------|-----------------|
| `DATABASE_URL` | PostgreSQL prod |
| `JWT_SECRET_KEY` ou `AUTH_SECRET` | JWT portail (`person_id`) |
| `NEXT_PUBLIC_PRIVY_APP_ID` | Client Privy (login) |
| `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID` | `c81911c59a601f3c793d361a74c1486d` |
| `NEXT_PUBLIC_BASE_RPC_URL` | Alchemy Base RPC (prod) |
| `BASE_RPC_URL_PRIMARY` | Alchemy Base RPC (prod) |
| `BASE_RPC_URL_FALLBACK` | `https://mainnet.base.org` |

### Beta ouverte (plafonds faibles)

| Variable | Valeur prod beta |
|----------|------------------|
| `MORPHO_USDC_BETA_ENABLED` | `true` |
| `MORPHO_USDC_BETA_ALLOW_ALL_USERS` | `true` |
| `MORPHO_USDC_DEPOSITS_DISABLED` | `false` |
| `MORPHO_USDC_WITHDRAWS_DISABLED` | `false` |
| `MORPHO_USDC_BETA_MIN_DEPOSIT_USDC` | `10` (ajuster si besoin) |
| `MORPHO_USDC_BETA_MAX_DEPOSIT_USDC` | `100` |
| `MORPHO_USDC_BETA_MAX_USER_EXPOSURE_USDC` | `500` |
| `MORPHO_USDC_BETA_MAX_GLOBAL_EXPOSURE_USDC` | `5000` |

### Optionnelles

| Variable | Défaut | Description |
|----------|--------|-------------|
| `MORPHO_RECONCILIATION_TOLERANCE_RAW` | `10` | Tolérance réconciliation (raw USDC) |
| `MORPHO_ALERT_MISMATCH_TOLERANCE_RAW` | `1000000` | Alerte mismatch (= 1 USDC) |
| `MORPHO_PENDING_ALERT_MINUTES` | `15` | Alerte tx pending stale |
| `PRIVY_APP_SECRET` | — | Uniquement si features Privy server-side hors Morpho |

**Note :** `PRIVY_APP_SECRET` n'est **plus requis pour Morpho** (mode `direct_morpho` uniquement). Privy reste nécessaire pour le **login email OTP** côté client.

---

## 3. Reown / WalletConnect (MetaMask)

- [ ] Projet Reown créé — Project ID `c81911c59a601f3c793d361a74c1486d`
- [ ] **Verify domain** `app.vancelian.finance` dans le dashboard Reown
- [ ] *(Dev)* `http://localhost:3000` autorisé si tests locaux MetaMask
- [ ] Modal WalletConnect s'ouvre sur `/app/wallets`
- [ ] MetaMask se connecte sans erreur domain
- [ ] Signature de vérification wallet externe fonctionne (`POST /api/portal/wallets/external/verify`)
- [ ] Wallet MetaMask **connecté** = wallet **vérifié** lié au compte avant transaction Morpho/LI.FI
- [ ] Message UX visible : gas payé par l'utilisateur en mode wallet externe

---

## 4. Infra externe

- [ ] **RPC Base prod** (Alchemy) — latence < 500 ms, quota suffisant
- [ ] **Morpho GraphQL** accessible (`https://api.morpho.org/graphql`)
- [ ] **Privy login** actif (`NEXT_PUBLIC_PRIVY_APP_ID` + allowed origins)
- [ ] *(Option)* Privy gas sponsorship Base pour embedded wallet — **non bloquant** si MetaMask externe disponible

---

## 5. Cron / jobs récurrents

- [ ] Cron registry sync : toutes les **6h** (`pnpm morpho:sync-vault-registry`)
- [ ] Cron réconciliation : **quotidien 06:00 UTC** (`pnpm morpho:reconcile`)
- [ ] Logs cron → alerte si exit code ≠ 0

Voir [MORPHO_CRON_JOBS.md](./MORPHO_CRON_JOBS.md).

---

## 6. Monitoring & alertes

- [ ] `/admin/morpho-vaults/monitoring` accessible (auth admin)
- [ ] Statut global **Healthy** avant go-live
- [ ] Aucune alerte **Critical** non résolue

---

## 7. Tests fonctionnels prod (smoke)

- [ ] Login portail Privy
- [ ] Lier wallet MetaMask (`/app/wallets`) + vérification signature
- [ ] Invest → sélecteur wallet → dépôt **1–10 USDC** max
- [ ] Retrait partiel validé
- [ ] *(Option)* Dépôt via embedded Privy wallet
- [ ] Disclaimer visible au 1er dépôt
- [ ] Double-submit impossible (idempotency)
- [ ] Wallet ownership : adresse non liée → 403
- [ ] Vault non publié → 404

**Tests automatisés avant deploy :**

```bash
cd services/arquantix/web
npm run test:morpho-vault
node --import tsx --test src/lib/wallet/externalWallet.test.ts
```

---

## 8. Sécurité & conformité

- [ ] Idempotency obligatoire sur prepare/deposit/withdraw
- [ ] Receipt verification stricte avant « Confirmed »
- [ ] Wallet externe : signature ownership + nonce anti-replay
- [ ] Ledger enregistre `wallet_source` (`privy_embedded` | `external_evm`)
- [ ] Disclaimers DeFi visibles (risques smart contract, liquidité, APY variable, gas user-paid)

---

## 9. Rollback plan

1. **Dépublier** tous les vaults Morpho (`isPublished = false`)
2. Kill switch : `MORPHO_USDC_DEPOSITS_DISABLED=true`
3. **Ne pas** supprimer le ledger — audit trail
4. Investiguer via monitoring + `pnpm morpho:reconcile`
5. Fix forward + republish vault par vault

---

## 10. Checklist prod finale (go / no-go)

| # | Item | OK |
|---|------|-----|
| 1 | Migrations appliquées (incl. external wallet nonces) | ☐ |
| 2 | Vaults `direct_morpho` publiés, aucun `privy_earn` publié | ☐ |
| 3 | Env RPC + WalletConnect configurés | ☐ |
| 4 | Reown domain `app.vancelian.finance` vérifié | ☐ |
| 5 | Beta `ALLOW_ALL_USERS=true` + plafonds faibles | ☐ |
| 6 | Smoke test MetaMask + embedded | ☐ |
| 7 | `npm run test:morpho-vault` vert | ☐ |
| 8 | Cron réconciliation actif | ☐ |
| 9 | Monitoring **Healthy** | ☐ |
| 10 | Support briefé | ☐ |

**Décision** : ☐ Beta ouverte ☐ Reporté — motif : _______________

| Rôle | Nom | Date | OK |
|------|-----|------|-----|
| Dev / intégration | | | |
| QA | | | |
| Ops | | | |
| Produit / compliance | | | |
