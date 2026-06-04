# Transaction quote freshness — spec (Swap portal LI.FI)

## Objectif

Ne jamais signer une route LI.FI potentiellement stale issue de l’écran Review. L’écran Review affiche une **estimation** ; l’exécution démarre par une **quote fraîche** et une vérification de delta.

## Flux cible (Swap self-trading)

```
Setup (montant)     → quote indicative (POST /quote)
Review              → récap utilisateur (snapshot en mémoire)
Confirm → Processing:
  1. POST /confirm-execute (refresh LI.FI + compare + prepare)
  2. Si delta OK     → signatures (approve + swap) + poll
  3. Si delta trop   → 409 swap.price_changed → retour Review
```

### Étapes Processing (UI)

| # | Libellé | Phase technique |
|---|---------|-----------------|
| 1 | Vérification du prix | `verifying_price` |
| 2 | Signature | `approving` / `signing` |
| 3 | Échange | `submitting` |
| 4 | Réception | `bridging` / `completed` |

## Règles métier

- **TTL quote DB** : `QUOTE_TTL_SECONDS = 120` (inchangé).
- **Refresh** : ré-appel LI.FI sur le **même** `swap_id` (pas de nouvelle ligne).
- **Comparaison** : `fresh_receive < review_receive × (1 − slippage_bps/10000)` → `swap.price_changed`.
- **Slippage** : `slippage_bps` du swap (défaut 50 = 0,5 %).
- **Retry serveur** : 3 tentatives LI.FI sur refresh (backoff court).
- **Retry client** : 3 tentatives sur erreurs réseau / 502 avant échec.
- **Abandon** : `POST /abandon` si l’utilisateur quitte après échec wallet (statut `FAILED`, message produit).

## API

### `POST /api/swaps/confirm-execute`

Body :

```json
{
  "swap_id": "uuid",
  "review_estimated_receive": "0.14889",
  "review_amount_in": "10"
}
```

Réponse 200 :

```json
{
  "freshness": "verified",
  "quote": { "...SwapQuoteResponse..." },
  "execute": { "...SwapExecuteResponse..." }
}
```

Réponse 409 (`swap.price_changed`) :

```json
{
  "code": "swap.price_changed",
  "message": "Le prix a légèrement changé...",
  "quote": { "...fresh quote..." },
  "delta_bps": 120,
  "slippage_bps": 50
}
```

### `POST /api/swaps/{swap_id}/refresh-quote`

Refresh seul (debug / bundle legs).

### `POST /api/swaps/{swap_id}/abandon`

Marque le swap abandonné côté client (signature refusée, etc.).

## Phase 2 — Bundles (invest / withdraw / rebalance)

Avant **chaque signature** de leg LI.FI :

1. Snapshot leg (montants affichés à l’invest / retrait / réalloc) :
   - **Invest** : `entry_asset_consumed` → `review_amount_in`, `crypto_received` → `review_estimated_receive`
   - **Withdraw** : `quantity_sold` / `entry_asset_received`
   - **Rebalance sell** : idem withdraw ; **buy** : `entry_asset_spent` / `quantity_bought`
2. `POST /api/swaps/confirm-execute` (via `bundleLegConfirmAndPrepare` + retry réseau).
3. Si **409** `swap.price_changed` : 1 retry automatique avec quote fraîche ; sinon leg **skippable** (invest) ou erreur (withdraw/rebalance).

Backend :

- `execute_leg` ne appelle plus `prepare_execute` à la création (quote seule, `amount_to` = estimation LI.FI).
- Resume invest : `crypto_received` hydraté depuis `swap.estimated_receive`.

Fichiers : `bundleLegQuoteConfirm.ts`, `useBundleLifiInvest.ts`, `useBundleLifiWithdraw.ts`, `useBundleLifiRebalance.ts`, `bundle_lifi_leg_service.py`.

## Hors scope

- Navigation perf (cache écran, lazy Web3).
- Exchange mobile (`MARKET_QUOTE_STALE`).

## Fichiers

| Couche | Fichiers |
|--------|----------|
| API | `swap_quote_freshness.py`, `lifi_quote_service.refresh_quote`, `lifi_execute_service.confirm_execute`, `routes.py` |
| Web | `swapClient.ts`, `swapQuoteConfirm.ts`, `PortalSwapExecutionController`, `swapSteps.ts`, `swapUiCopy.ts` |
| Tests | `test_swap_quote_freshness.py` |
