# Buy Asset Modal Backend Integration Report

## Executive Summary

La modal "Buy Asset" Flutter est désormais **branchée de bout en bout** au vrai exchange engine backend Vancelian. L'utilisateur peut acheter du crypto depuis l'app mobile avec :

1. **Balance EUR réelle** chargée depuis l'endpoint `/api/app/cash`
2. **Preview live** via un nouvel endpoint `POST /api/app/exchange/buy/preview` qui utilise **exactement** le même `_resolve_price()` que le BUY réel (ask, spread, FX, fees)
3. **Exécution BUY réelle** via `POST /api/app/exchange/buy` qui déclenche le flux complet : débit EUR, création order, credit crypto position, ledger, settlement delta, audit
4. **Gestion d'états** complète : idle, preview loading, preview error, confirm loading, success (pop + refresh), error (banner)

## Files Modified

### Backend (Python)

| Fichier | Changement |
|---------|-----------|
| `api/services/exchange/service.py` | Ajout méthode `preview_buy()` réutilisant `_resolve_price()` |
| `api/services/test_clients/router.py` | Ajout endpoints `POST /exchange/buy/preview` et `POST /exchange/buy` |

### Next.js Proxy

| Fichier | Changement |
|---------|-----------|
| `web/src/app/api/mobile/flutter/exchange/buy/preview/route.ts` | **CRÉÉ** — proxy POST vers backend |
| `web/src/app/api/mobile/flutter/exchange/buy/route.ts` | **CRÉÉ** — proxy POST vers backend |

### Flutter

| Fichier | Changement |
|---------|-----------|
| `mobile/lib/core/config.dart` | Ajout `exchangeBuyPreviewUrl` et `exchangeBuyUrl` |
| `mobile/lib/features/wallet/data/exchange_api.dart` | **CRÉÉ** — `ExchangeApi`, `BuyPreviewResult`, `BuyResult` |
| `mobile/lib/features/wallet/presentation/screens/buy_asset_modal_screen.dart` | Réécrit avec intégration backend complète |
| `mobile/lib/features/wallet/presentation/screens/crypto_wallet_detail_screen.dart` | `_openBuyModal()` gère `didBuy == true` → refresh |

## Source Account Integration

### Flux de la balance EUR

```
BuyAssetModalScreen.initState()
  → CashApi().fetchCashData()
  → GET /api/mobile/flutter/cash
  → Next.js proxy → GET /api/app/cash
  → TestClientService.get_cash_data()
  → CustodyAccountRepository.find_client_account(client_id, "EUR")
  → CustodyBalanceRepository.get_by_account_id(account_id)
  → { available_balance, pending_balance }
```

### Affichage

- La pill "Compte Euro" affiche le **vrai solde disponible** (`available_balance`)
- Formaté via `NumberFormat.currency` (fr_FR pour EUR, en_US pour USD)
- Si le chargement échoue, affiche "—" sans bloquer l'UX

### Validation

```dart
bool get _isOverBalance =>
    _balanceLoaded && _eurBalance > 0 && _parsedAmount > _eurBalance;
```

Le montant saisi s'affiche en **rouge** si supérieur au solde disponible.

## Preview Endpoint / Logic

### Endpoint

```
POST /api/app/exchange/buy/preview
```

### Request

```json
{ "asset": "BTC", "amount_fiat": 1000 }
```

### Response

```json
{
  "asset": "BTC",
  "amount_fiat": 1000.0,
  "estimated_price": 62119.23,
  "estimated_crypto_gross": 0.01610,
  "fee_amount": 0.00008,
  "fee_asset": "BTC",
  "fee_bps": 50,
  "estimated_crypto_net": 0.01602,
  "currency": "EUR",
  "is_fresh": true
}
```

### Cohérence pricing

La méthode `preview_buy()` dans `ExchangeService` utilise **exactement** `_resolve_price(db, asset, override_price=None, side="buy")`, qui est le même appel que `buy()`.

Cela garantit :
- Même prix ask (ou mid + spread simulé)
- Même freshness guard (60s max)
- Même conversion FX EURUSDT
- Même calcul de fees (fee_bps × volume_raw / 10000)
- Même précision asset (ASSET_PRECISION)

### Debounce Flutter

La preview est appelée avec un **debounce de 500ms** après chaque changement de montant :

```dart
_debounceTimer = Timer(const Duration(milliseconds: 500), _fetchPreview);
```

Si le montant change avant que la réponse arrive, le résultat stale est ignoré.

## Buy Execution Integration

### Endpoint

```
POST /api/app/exchange/buy
```

### Request

```json
{ "asset": "BTC", "amount_fiat": 1000 }
```

### Flux backend

1. Le `bootstrap_router` récupère le `client_id` depuis le bootstrap client courant
2. Génère un `external_reference` unique : `mobile-buy-{uuid4()}`
3. Forge un `ExchangeBuyRequest` complet
4. Délègue à `ExchangeService.buy()` — le **vrai** exchange engine
5. Le flux complet s'exécute :
   - Idempotency check
   - Validate asset
   - Resolve price (ask, FX, freshness)
   - Compute crypto amount + fee
   - Lock + validate EUR balance
   - Create exchange_order
   - Custody transaction (EUR debit)
   - Ledger double entry
   - Update EUR balances
   - Credit crypto_position
   - Settlement delta
   - Finalize order + audit

### Response

```json
{
  "status": "completed",
  "order_id": "...",
  "asset": "BTC",
  "amount_crypto": "0.01602",
  "amount_fiat": "1000",
  "price": "62119.23",
  "fee_amount": "0.00008",
  "fee_asset": "BTC",
  "client_eur_balance_after": "149778.96",
  "crypto_position_after": "0.03204"
}
```

### Erreurs gérées

| Erreur backend | HTTP | Message Flutter |
|---------------|------|-----------------|
| `InsufficientFundsError` | 200 (status=failed) | "Solde insuffisant" |
| `MarketQuoteStaleError` | 503 | "Prix du marché expiré" |
| `PriceUnavailableError` | 503 | "Prix indisponible" |
| `FxUnavailableError` | 503 | "Prix indisponible" |
| `UnsupportedAssetError` | 400 | "Asset non supporté" |
| `AccountNotFoundError` | 404 | "Erreur lors de l'achat" |
| `DuplicateOrderError` | 200 (status=ignored) | (ignoré silencieusement) |

## UI State Handling

| État | Affichage |
|------|-----------|
| **Idle** | Montant "0 €", conversion "0 BTC", bouton grisé |
| **Saisie** | Montant formaté, conversion locale (fallback unitPrice) |
| **Preview loading** | Spinner + "Estimation..." sous le montant |
| **Preview OK** | "≈ 0.01602 BTC" + "(frais 0.00008 BTC)" |
| **Preview error** | Banner rouge avec message |
| **Over balance** | Montant en rouge, bouton grisé |
| **Confirm loading** | Spinner blanc dans le bouton, bouton non-cliquable |
| **Buy success** | `Navigator.pop(true)` → refresh page parent |
| **Buy error** | Banner rouge avec message humanisé |

### Anti-double-submit

```dart
Future<void> _onConfirm() async {
  if (!_isValid || _buyLoading) return;
  setState(() { _buyLoading = true; _buyError = null; });
  // ... exécution
}
```

Le flag `_buyLoading` empêche toute re-soumission pendant l'appel.

## Refresh After Success

### Mécanisme

```dart
// Dans BuyAssetModalScreen._onConfirm():
if (result.isSuccess) {
  Navigator.of(context).pop(true);  // ← retourne true
  return;
}

// Dans CryptoWalletDetailScreen._openBuyModal():
final didBuy = await BuyAssetModalScreen.show(...);
if (didBuy == true && mounted) {
  _load();              // reload wallet detail + positions
  _loadHeroSparkline(); // reload hero chart
}
```

### Ce qui est rafraîchi

- `_load()` : re-fetch `CryptoPositionsApi.fetchDetail(asset)` + `MarketDataApi.getMarketSummary()` → position, total value, P&L, prix actualisés
- `_loadHeroSparkline()` : re-fetch `WalletHistoryApi.fetchHistory(mode: 'performance_value')` → courbe performance mise à jour

Les pages "All Crypto" et "Statistics" seront cohérentes au prochain chargement naturel (elles fetch à chaque initState).

## Validation Rules

| Condition | Résultat |
|-----------|----------|
| `_parsedAmount == 0` | Bouton grisé |
| `_parsedAmount > _eurBalance` (si balance chargée) | Montant rouge, bouton grisé |
| `_preview == null` | Bouton grisé |
| `_preview.hasError` | Bouton grisé |
| `_buyLoading` | Bouton avec spinner |
| Toutes conditions OK | Bouton indigo actif |

```dart
bool get _isValid =>
    _parsedAmount > 0 &&
    _balanceLoaded &&
    (_eurBalance <= 0 || _parsedAmount <= _eurBalance) &&
    _preview != null &&
    !_preview!.hasError &&
    !_buyLoading;
```

## Final Status

| Élément | État |
|---------|------|
| Balance EUR réelle | **BRANCHÉ** via CashApi |
| Preview endpoint | **CRÉÉ** — `POST /api/app/exchange/buy/preview` |
| Preview pricing = BUY pricing | **GARANTI** — même `_resolve_price()` |
| Preview debounce | **500ms** |
| BUY endpoint mobile | **CRÉÉ** — `POST /api/app/exchange/buy` |
| BUY réel exchange engine | **BRANCHÉ** — flux complet |
| Proxy Next.js | **CRÉÉ** — preview + buy |
| Flutter API service | **CRÉÉ** — `ExchangeApi` |
| États UI (6 états) | **IMPLÉMENTÉS** |
| Anti-double-submit | **OUI** |
| Refresh après succès | **OUI** — `Navigator.pop(true)` + `_load()` + `_loadHeroSparkline()` |
| Erreurs humanisées | **OUI** — 5 codes gérés |
| Linters | **0 erreurs** |
| UI design préservé | **OUI** — aucun changement de layout |
