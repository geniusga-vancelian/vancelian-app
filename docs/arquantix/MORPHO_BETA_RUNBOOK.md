# Morpho USDC Volt — Runbook beta contrôlée

Ouverture progressive du vault Morpho USDC avec plafonds, kill switch et surveillance support.

## Architecture

```text
Privy              = login + embedded wallet optionnel
Reown / WalletConnect = wallets externes (MetaMask)
Morpho             = direct_morpho uniquement
Vancelian          = ledger + registry + reconciliation + monitoring
```

**Références**
- Staging : [MORPHO_STAGING_RUNBOOK.md](./MORPHO_STAGING_RUNBOOK.md)
- Production : [MORPHO_PRODUCTION_CHECKLIST.md](./MORPHO_PRODUCTION_CHECKLIST.md)
- Cron : [MORPHO_CRON_JOBS.md](./MORPHO_CRON_JOBS.md)
- Sandbox local : [MORPHO_LOCAL_SANDBOX.md](./MORPHO_LOCAL_SANDBOX.md)
- Monitoring admin : `/admin/morpho-vaults/monitoring`

---

## Variables d'environnement (beta ouverte à tous)

Pour une **beta ouverte à tous les utilisateurs** avec plafonds faibles :

```bash
MORPHO_USDC_BETA_ENABLED=true
MORPHO_USDC_BETA_ALLOW_ALL_USERS=true
MORPHO_USDC_BETA_MIN_DEPOSIT_USDC=0
MORPHO_USDC_BETA_MAX_DEPOSIT_USDC=100
MORPHO_USDC_BETA_MAX_USER_EXPOSURE_USDC=500
MORPHO_USDC_BETA_MAX_GLOBAL_EXPOSURE_USDC=5000
MORPHO_USDC_DEPOSITS_DISABLED=false
MORPHO_USDC_WITHDRAWS_DISABLED=false
```

| Variable | Défaut | Rôle |
|----------|--------|------|
| `MORPHO_USDC_BETA_ENABLED` | `false` | Active les plafonds beta |
| `MORPHO_USDC_BETA_ALLOW_ALL_USERS` | `false` | Si `true`, pas d'allowlist (beta ouverte) |
| `MORPHO_USDC_BETA_PERSON_IDS` | — | UUIDs autorisés (CSV) — ignoré si `ALLOW_ALL_USERS=true` |
| `MORPHO_USDC_BETA_EMAILS` | — | Emails autorisés (CSV) |
| `MORPHO_USDC_BETA_PROFILE_TAG` | — | Tag dans `profile_json.tags` |
| `MORPHO_USDC_BETA_MIN_DEPOSIT_USDC` | `0` | Dépôt minimum (`0` = aucun) |
| `MORPHO_USDC_BETA_MAX_DEPOSIT_USDC` | `0` | Dépôt max par transaction (`0` = aucun) |
| `MORPHO_USDC_BETA_MAX_USER_EXPOSURE_USDC` | `0` | Exposition max utilisateur (`0` = aucune) |
| `MORPHO_USDC_BETA_MAX_GLOBAL_EXPOSURE_USDC` | `0` | Cap global beta (`0` = aucun) |
| `MORPHO_USDC_DEPOSITS_DISABLED` | `false` | Kill switch dépôts |
| `MORPHO_USDC_WITHDRAWS_DISABLED` | `false` | Kill switch retraits |

**WalletConnect / RPC (prod)**

```bash
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=c81911c59a601f3c793d361a74c1486d
NEXT_PUBLIC_BASE_RPC_URL=<Alchemy Base RPC>
BASE_RPC_URL_PRIMARY=<Alchemy Base RPC>
BASE_RPC_URL_FALLBACK=https://mainnet.base.org
```

**Logs support (stdout JSON, préfixe `[morpho:support]`)**
- `morpho.tx_failed` / `morpho.tx_reverted`
- `morpho.withdraw_failed` / `morpho.deposit_failed`
- `morpho.reconciliation_mismatch` (> 1 USDC)
- `morpho.tx_pending_stale` (> 15 min)
- `morpho.beta_limit_exceeded`

---

## 1. Procédure d'ouverture beta

1. **Valider staging** — runbook staging OK, monitoring **Healthy**.
2. **Publier les vaults** — CMS `/admin/morpho-vaults`, mode **`direct_morpho` uniquement**.
3. **Sync registry** :
   ```bash
   cd services/arquantix/web
   pnpm morpho:sync-vault-registry
   ```
4. **Configurer la beta ouverte** :
   ```bash
   MORPHO_USDC_BETA_ENABLED=true
   MORPHO_USDC_BETA_ALLOW_ALL_USERS=true
   MORPHO_USDC_DEPOSITS_DISABLED=false
   MORPHO_USDC_WITHDRAWS_DISABLED=false
   ```
5. **Vérifier Reown** — domaine `app.vancelian.finance` vérifié (voir checklist prod).
6. **Redéployer** le web avec les nouvelles variables.
7. **Smoke test** :
   - Login → `/app/wallets` → lier MetaMask (optionnel)
   - Invest → vault visible → sélecteur wallet (Vancelian / MetaMask)
   - Dépôt 10 USDC min → retrait partiel
   - Monitoring admin → section **Beta Morpho USDC** cohérente
8. **Activer cron** réconciliation quotidienne (voir `MORPHO_CRON_JOBS.md`).

---

## 2. Surveillance quotidienne (5–10 min)

| Check | Où | Seuil |
|-------|-----|-------|
| Statut global | `/admin/morpho-vaults/monitoring` | **Healthy** idéal |
| Beta users / assets / yield | Section Beta Morpho USDC | Tendance stable |
| Tx pending > 15 min | Alertes | **0** |
| Mismatches > 1 USDC | Dernière réconciliation | **0** |
| Cap global beta | vs `MORPHO_USDC_BETA_MAX_GLOBAL_EXPOSURE_USDC` | < 80 % |

```bash
pnpm morpho:reconcile
```

---

## 3. Kill switch

**Suspendre les dépôts uniquement**
```bash
MORPHO_USDC_DEPOSITS_DISABLED=true
MORPHO_USDC_WITHDRAWS_DISABLED=false
```

**Suspendre tout**
```bash
MORPHO_USDC_DEPOSITS_DISABLED=true
MORPHO_USDC_WITHDRAWS_DISABLED=true
```

---

## 4. Données legacy

Les lignes ledger historiques `integration_mode = privy_earn` restent en base (**lecture seule**).  
Aucune nouvelle opération Morpho ne doit utiliser ce mode.

---

## 5. Critères passage rollout large

| Critère | Cible |
|---------|-------|
| Mismatch critique (> 1 USDC) | 0 |
| Monitoring | **Healthy** |
| Support | Briefé (risques DeFi, wallets externes, gas user-paid) |

**Passage rollout** : `MORPHO_USDC_BETA_ENABLED=false` + relever ou retirer plafonds selon décision produit.

---

## 6. Checklist go / no-go beta (résumé)

- [ ] Staging validé
- [ ] Vaults `direct_morpho` publiés
- [ ] `MORPHO_USDC_BETA_ALLOW_ALL_USERS=true` + plafonds configurés
- [ ] WalletConnect Project ID + domaine Reown vérifié
- [ ] RPC Base prod (Alchemy) configuré
- [ ] Kill switch testé
- [ ] Cron réconciliation planifié
- [ ] Smoke test embedded + MetaMask externe
