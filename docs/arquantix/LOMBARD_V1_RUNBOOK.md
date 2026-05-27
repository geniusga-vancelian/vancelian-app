# Lombard V1 — Runbook ops & beta

Produit : **Avance de liquidité** — emprunt USDC contre cbBTC ou cbETH via Morpho Blue sur Base.

## Feature flags (web / ECS)

| Variable | Default | Description |
|----------|---------|-------------|
| `LOMBARD_V1_ENABLED` | `true` (unset) | Kill switch global. `false` désactive quote/prepare/confirm/position. |
| `LOMBARD_V1_BETA_ENABLED` | `false` | Active caps beta + allowlist (alias de `LOMBARD_V1_BETA_LIMITS_ENABLED`). |
| `LOMBARD_V1_BETA_LIMITS_ENABLED` | `false` | Idem caps sans allowlist obligatoire. |
| `LOMBARD_V1_BETA_MAX_BORROW_USDC_PER_WALLET` | `25000` | Plafond emprunt USDC par wallet (exposition on-chain cumulée + nouvel emprunt). |
| `LOMBARD_V1_BETA_MAX_TOTAL_BORROW_USDC_GLOBAL` | `250000` | Plafond global beta (somme expositions on-chain wallets Lombard). |
| `LOMBARD_V1_BETA_ALLOWED_WALLETS` | _(vide)_ | Allowlist optionnelle `0x...,0x...` (lowercase). Vide = tous wallets autorisés. |
| `LOMBARD_V1_RECONCILIATION_TOLERANCE_BPS` | `200` | Tolérance réconciliation post-confirm (2 %). |
| `LOMBARD_V1_DEBUG_PANEL_FOR_ADMINS` | `true` (unset) | Panel QA debug pour admins en prod. |
| `LOMBARD_V1_MOCK_ENABLED` | `false` | **Dev only** — mock Morpho sans TX réelle. **Interdit en prod** (startup fatal). |

### Mock local (dev uniquement)

| Variable | Default | Description |
|----------|---------|-------------|
| `LOMBARD_V1_MOCK_WALLET_BALANCE_CBBTC` | `0.10` | Balance cbBTC simulée |
| `LOMBARD_V1_MOCK_WALLET_BALANCE_CBETH` | `1.50` | Balance cbETH simulée |
| `LOMBARD_V1_MOCK_BORROW_APY_BPS` | `480` | APY emprunt mock (4,8 %) |
| `LOMBARD_V1_MOCK_LLTV_BPS` | `8600` | LLTV mock (86 %) |
| `LOMBARD_V1_MOCK_MARKET_LIQUIDITY_USDC` | `1000000` | Liquidité USDC mock |
| `LOMBARD_V1_MOCK_POSITION_ENABLED` | `false` | Expose positions mock depuis ledger après confirm |

```bash
# .env.local
LOMBARD_V1_MOCK_ENABLED=true
LOMBARD_V1_MOCK_POSITION_ENABLED=true
pnpm lombard:mock
```

Flow mock : markets → quote → prepare (`mockExecution: true`) → confirm sans signature wallet → position read-only depuis ledger.

### Variables production requises (si `LOMBARD_V1_ENABLED=true`)

Validées au startup (`[lombard:prod-env]`) et via `pnpm lombard:smoke:prod-env` :

| Variable | Notes |
|----------|-------|
| `LOMBARD_V1_ENABLED` | explicite recommandé |
| `LOMBARD_V1_BETA_ENABLED` | `true` en beta |
| `LOMBARD_V1_BETA_LIMITS_ENABLED` | `true` en beta |
| `LOMBARD_V1_BETA_ALLOWED_WALLETS` | CSV wallets autorisés |
| `LOMBARD_V1_BETA_MAX_BORROW_USDC_PER_WALLET` | ex. `25000` |
| `LOMBARD_V1_BETA_MAX_TOTAL_BORROW_USDC_GLOBAL` | ex. `250000` |
| `BASE_RPC_URL_PRIMARY` ou `BASE_RPC_URL` | RPC Base mainnet |
| `MORPHO_GRAPHQL_URL` | défaut `https://api.morpho.org/graphql` |
| `PRIVY_APP_ID` + `PRIVY_APP_SECRET` | auth portail |
| `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID` | wallet externe (MetaMask) |

**Interdit prod :** `LOMBARD_V1_MOCK_ENABLED=true` → le process Next refuse de démarrer.

### Emergency disable

1. Set `LOMBARD_V1_ENABLED=false` sur le service web Arquantix.
2. Redéployer / restart ECS task.
3. Vérifier `GET /api/portal/lombard/markets` → `{ enabled: false }`.
4. Les positions on-chain existantes restent visibles en read-only si réactivé ; aucune nouvelle ouverture.

## Marchés Morpho (Base)

| Collateral | Market ID |
|------------|-----------|
| cbBTC / USDC | `0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836` |
| cbETH / USDC | `0x0ca10126f6c94cbd9cf0a48cc9516ae5e3dec5aa68303e6d988ee37c5149bf0d` |

Validation runtime : GraphQL Morpho + hash `marketParams.id` (pas de hardcode LLTV/oracle).

## Plafonds utilisateur V1

- **Max LTV Vancelian** : 70 % (blocage quote/prepare)
- **Warning UX** : > 60 % projected LTV (quote/prepare retourne `warnings[]`)
- **Morpho LLTV** : ~86 % cbBTC, ~77 % cbETH (liquidation protocolaire — affiché en détail)

## Risque liquidation (support client)

Message client :

> Si la valeur de votre garantie baisse trop, une partie de votre crypto peut être vendue automatiquement pour rembourser l'emprunt.

- Vancelian bloque à 70 % pour garder une marge avant LLTV Morpho.
- Zones santé : Comfortable ≤ 50 %, To monitor ≤ 60 %, High risk ≤ 70 %.

## Réconciliation post-confirm

Après `POST /api/portal/lombard/confirm` (toutes TX success) :

1. Lecture metadata ledger (`borrow_amount_raw`, `guarantee_amount_raw`)
2. Lecture position Morpho on-chain
3. Comparaison borrow + collateral
4. Metadata ledger enrichie :
   - `reconciliation_status`: `confirmed` | `confirmed_with_delta`
   - deltas en bps si hors tolérance
5. Log structuré `[lombard:support]` code `lombard.reconciliation_delta`

## Monitoring admin

```bash
curl -s -b "session=..." https://<host>/api/admin/lombard/monitoring | jq
```

Retourne :

- positions actives + LTV
- total emprunté / collateral USD
- compte positions > 60 % et > 70 % LTV
- ledger : pending / failed / reverted / confirmed_with_delta

## Support playbook

| Symptôme | Action |
|----------|--------|
| `lombard.disabled` | Vérifier `LOMBARD_V1_ENABLED` |
| `lombard.beta.wallet_not_allowlisted` | Ajouter wallet à `LOMBARD_V1_BETA_ALLOWED_WALLETS` |
| `lombard.beta.wallet_borrow_cap` | User au plafond wallet — repay hors scope V1 ou augmenter cap |
| `lombard.balance_changed` | User a bougé cbBTC/cbETH entre quote et prepare — refaire quote |
| `lombard.insufficient_liquidity` | Liquidité USDC insuffisante sur marché Morpho — réduire montant |
| `reconciliation_delta` | Comparer monitoring + Morpho UI ; investiguer slippage / partial fill |
| TX pending > 15 min | Admin monitoring `ledger.pendingCount` ; vérifier Base RPC + tx hash |

## Logs support

Stdout JSON prefix `[lombard:support]` :

- `lombard.beta_limit_exceeded`
- `lombard.pre_borrow_warning`
- `lombard.reconciliation_delta`

## Rollout beta recommandé

1. `LOMBARD_V1_ENABLED=true`
2. `LOMBARD_V1_BETA_ENABLED=true`
3. Caps conservateurs (25k / wallet, 250k global)
4. Allowlist wallets internes
5. Monitoring admin quotidien
6. Élargir allowlist puis retirer allowlist

QA checklist live : [`LOMBARD_V1_QA_CHECKLIST.md`](./LOMBARD_V1_QA_CHECKLIST.md)

Smoke : `pnpm lombard:smoke` (Morpho live) · `pnpm lombard:mock` (local mock) · `pnpm lombard:smoke:prod-env` (checklist prod).

## Hors scope V1

Repay, borrow more, add guarantee, withdraw guarantee — Phase 3.
