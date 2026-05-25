# Ledgity — Activation live production (accès ouvert)

Production = environnement de dev live contrôlé : **accès ouvert**, plafonds faibles, monitoring + réconciliation actifs, kill switch disponible.

**Wallets autorisés** : Privy embedded + MetaMask / WalletConnect (Reown) — pas de restriction MetaMask-only.

---

## 1. Variables ECS / production

```env
LEDGITY_VAULTS_ENABLED=true
LEDGITY_BETA_ENABLED=false
LEDGITY_DEPOSITS_DISABLED=false
LEDGITY_WITHDRAWS_DISABLED=false

LEDGITY_MAX_DEPOSIT_RAW=10000000
LEDGITY_MAX_USER_EXPOSURE_RAW=50000000
LEDGITY_MAX_GLOBAL_EXPOSURE_RAW=500000000
LEDGITY_MIN_DEPOSIT_RAW=1000000

LEDGITY_RECONCILIATION_TOLERANCE_RAW=10
LEDGITY_ALERT_MISMATCH_TOLERANCE_RAW=1000000
LEDGITY_PENDING_ALERT_MINUTES=15

# Sandbox / mock — TOUJOURS false en prod
MORPHO_LOCAL_SANDBOX_ENABLED=false
EXTERNAL_WALLET_LOCAL_MOCK_ENABLED=false
LEDGITY_LOCAL_SANDBOX_ENABLED=false
LIFI_LOCAL_SANDBOX_ENABLED=false
LIFI_SWAPS_MOCK=false
```

Plafonds (6 décimales) :

| Variable | Valeur | Humain |
|----------|--------|--------|
| `LEDGITY_MAX_DEPOSIT_RAW` | 10000000 | 10 USDC/EURC / tx |
| `LEDGITY_MAX_USER_EXPOSURE_RAW` | 50000000 | 50 / utilisateur |
| `LEDGITY_MAX_GLOBAL_EXPOSURE_RAW` | 500000000 | 500 global |

**Beta désactivée** : pas d’allowlist (`LEDGITY_BETA_*` ignorée pour l’accès ; plafonds via `LEDGITY_MAX_*_RAW`).

---

## 2. Déploiement ECS

1. Pousser le code sur `main` (workflow `vancelian-next-deploy`).
2. Appliquer les env vars :

```bash
BASE_RPC_URL_PRIMARY='https://base-mainnet.g.alchemy.com/v2/<KEY>' \
  ./scripts/vancelian-sync-ledgity-prod.sh
```

Dry-run :

```bash
DRY_RUN=1 ./scripts/vancelian-sync-ledgity-prod.sh
```

3. Migrations prod si besoin :

```bash
cd services/arquantix/web && npx prisma migrate deploy
```

---

## 3. RPC production

```env
BASE_RPC_URL_PRIMARY=https://base-mainnet.g.alchemy.com/v2/<ALCHEMY_KEY>
BASE_RPC_URL_FALLBACK=https://mainnet.base.org
NEXT_PUBLIC_BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/<ALCHEMY_KEY>
```

Monitoring attendu (`/admin/ledgity-vaults/monitoring`) :

- `activeProvider` = alchemy (ou QuickNode)
- **aucune** alerte `rpc_public_primary`

---

## 4. WalletConnect / Reown

Checklist manuelle sur [app.vancelian.finance](https://app.vancelian.finance) :

- [ ] Domain verification Reown OK pour `app.vancelian.finance`
- [ ] MetaMask : connect + signature tx Ledgity
- [ ] WalletConnect : connect + signature
- [ ] Privy embedded : dépôt + retrait
- [ ] Ledger `wallet_source` = `external_evm` ou `privy_embedded` dans `metadata_json`

---

## 5. Smoke tests live

### lyUSDC

| # | Test | Wallet |
|---|------|--------|
| 1 | Dépôt 10 USDC | MetaMask |
| 2 | Dépôt 10 USDC | Privy embedded |
| 3 | Retrait partiel | MetaMask ou Privy |
| 4 | Retrait total (≤ maxWithdraw) | idem |
| 5 | Ledger `success` | — |
| 6 | `pnpm ledgity:reconcile` → matched | — |
| 7 | Monitoring **Healthy** | — |

### lyEURC

| # | Test |
|---|------|
| 1 | Dépôt 10 EURC |
| 2 | Retrait partiel / total |
| 3 | PPS cohérent UI ↔ on-chain |
| 4 | `convertToAssets` cohérent |
| 5 | Liquidité : retrait > maxWithdraw → erreur métier |

Après **chaque batch** :

```bash
cd services/arquantix/web && npm run ledgity:reconcile
```

---

## 6. Kill switch

### Soft (dépôts off, retraits OK)

```env
LEDGITY_DEPOSITS_DISABLED=true
```

Redéployer ECS ou hot-update env. Vérifier : prepare deposit → 503, withdraw OK.

Remettre :

```env
LEDGITY_DEPOSITS_DISABLED=false
```

### Hard (tout off sauf retraits ledger existants)

```env
LEDGITY_VAULTS_ENABLED=false
```

**Ne jamais** `LEDGITY_WITHDRAWS_DISABLED=true` sauf incident critique.

---

## 7. Rollback

| Niveau | Action |
|--------|--------|
| Soft | `LEDGITY_DEPOSITS_DISABLED=true` |
| Complet | `LEDGITY_VAULTS_ENABLED=false` |
| Retraits | Toujours laisser actifs sauf urgence |

---

## 8. Monitoring

URL : [console.vancelian.finance/admin/ledgity-vaults/monitoring](https://console.vancelian.finance/admin/ledgity-vaults/monitoring)

Attendu post-smoke :

- `globalStatus` = **healthy**
- `rpc` = alchemy
- `pps_unavailable` = 0
- `pending_tx_stale` = 0
- `ledger_onchain_mismatch` = 0

Cron : voir [LEDGITY_CRON_JOBS.md](./LEDGITY_CRON_JOBS.md) (06:15 UTC).

---

## 9. Risques restants

| Risque | Mitigation |
|--------|------------|
| Liquidité RWA / retrait différé | `maxWithdraw` + message utilisateur + alerte `liquidity_low` |
| PPS / RPC indisponible | Monitoring Critical, pas de panic utilisateur |
| Écart ledger | Réconciliation quotidienne + alertes |
| Exposition | Plafonds 10 / 50 / 500 |
| Sandbox en prod | Guard boot fatal (`productionSandboxGuard`) |

---

## Références

- [LEDGITY_AUDIT.md](./LEDGITY_AUDIT.md)
- [LEDGITY_PRODUCTION_CHECKLIST.md](./LEDGITY_PRODUCTION_CHECKLIST.md)
- [LEDGITY_CRON_JOBS.md](./LEDGITY_CRON_JOBS.md)
