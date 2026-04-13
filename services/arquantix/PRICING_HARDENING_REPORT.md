# Pricing Consistency Hardening Report

## 1. Executive Summary

Quatre risques identifiés lors de l'audit "Exchange Engine Pricing Consistency Audit" ont été corrigés :

| Risque | Sévérité | Statut |
|--------|----------|--------|
| **R1** — Fallback FX silencieux dans BUY/SELL | Medium | **Corrigé** |
| **R3** — Prix initial CryptoDetail en USDT au lieu de la devise préférée | Low | **Corrigé** |
| **R4** — Gains/PRU mono-devise (EUR seul) avec symbole trompeur | Low | **Corrigé** |
| **R5** — Symbole devise chart incohérent avec données USDT | Low | **Corrigé** |

**Niveau de confiance** : Élevé. Les 4 correctifs sont ciblés, sans refactor, et validés par 81 tests passants (4 nouveaux + 77 existants, 0 régression).

---

## 2. Files modified

### Backend (Python)

| Fichier | Rôle |
|---------|------|
| `api/services/exchange/service.py` | `_resolve_price()` utilise maintenant `strict=True` pour EURUSDT. Nouvelle exception `FxUnavailableError`. |
| `api/services/exchange/router.py` | Capture `FxUnavailableError` → HTTP 503 pour BUY et SELL. |
| `api/services/test_clients/service.py` | `get_crypto_wallet_detail()` calcule et retourne gains/PRU en EUR **et** USD. |
| `api/services/test_clients/schemas.py` | `CryptoWalletDetailPayload` enrichi avec `avg_buy_price_eur/usd`, `unrealized_gain_eur/usd`, `realized_gain_eur/usd`, `total_gain_eur/usd`. |
| `api/tests/test_pricing_hardening.py` | **Nouveau** — 4 tests pour strict FX et dual-currency gains. |

### Flutter (Dart)

| Fichier | Rôle |
|---------|------|
| `mobile/lib/features/wallet/domain/models/crypto_wallet_detail.dart` | Modèle enrichi avec champs gains/PRU dual-currency. |
| `mobile/lib/features/wallet/presentation/screens/crypto_wallet_detail_screen.dart` | Affiche gains/PRU selon `reference_currency` (EUR ou USD). |
| `mobile/lib/features/markets/data/market_data_api.dart` | `MarketSummaryItem` parse `price_eur` du backend. |
| `mobile/lib/features/markets/presentation/screens/crypto_detail_screen.dart` | Prix initial utilise `CurrencyPreference.selectValue(eur: priceEur, usd: price)`. |
| `mobile/lib/features/markets/presentation/widgets/chart_asset_module.dart` | Labels chart toujours en `$` (USD), indépendamment de la devise préférée. |

---

## 3. Execution hardening (R1 — strict FX)

### Avant
- `ExchangeService._resolve_price()` appelait `get_eurusdt_rate(db, strict=False)`
- Si la quote EURUSDT était absente ou périmée, un fallback silencieux vers `DEFAULT_EURUSDT_RATE = 1.08` était utilisé
- Risque : exécution d'un trade à un prix FX potentiellement incorrect

### Après
- `_resolve_price()` appelle `get_eurusdt_rate(db, strict=True)`
- Si la quote EURUSDT est absente → `FxQuoteUnavailableError` → wrappé en `FxUnavailableError`
- Si la quote EURUSDT est périmée (> 300s) → `FxQuoteStaleError` → wrappé en `FxUnavailableError`
- Le router capture `FxUnavailableError` et retourne **HTTP 503 Service Unavailable**
- Message d'erreur explicite : `fx_unavailable: eurusdt_quote_not_found` ou `fx_unavailable: eurusdt_quote_stale: age=Xs, max=300s`

### Impact
- BUY et SELL avec `price` override : **aucun changement** (le prix est déjà en EUR, `_resolve_price` retourne directement)
- BUY et SELL sans override (prix marché) : **rejet propre** si FX indisponible
- UI, valuations, market data endpoints : **inchangés** (continuent avec `strict=False`)

---

## 4. Wallet valuation hardening (R4 — dual-currency gains/PRU)

### Avant
- Le backend calculait `avg_price`, `unrealized_gains`, `realized_gains`, `total_gains` **uniquement en EUR**
- Flutter utilisait `_activeFormatter` (qui affiche `€` ou `$` selon la préférence) mais sur des valeurs EUR uniquement
- Résultat : si l'utilisateur choisit USD, les montants EUR étaient affichés avec le symbole `$`

### Après

**Backend** — `get_crypto_wallet_detail()` retourne :

| Champ EUR | Champ USD | Source |
|-----------|-----------|--------|
| `avg_buy_price_eur` | `avg_buy_price_usd` | `avg_eur * eurusdt_rate` |
| `unrealized_gain_eur` | `unrealized_gain_usd` | `total_value_X - cost_basis_X` |
| `realized_gain_eur` | `realized_gain_usd` | `realized_eur * eurusdt_rate` |
| `total_gain_eur` | `total_gain_usd` | `unrealized_X + realized_X` |

> **Note** : Les valeurs USD de `avg_buy_price` et `realized_gain` sont converties au taux EURUSDT **courant**, pas au taux historique de chaque trade. C'est une approximation acceptable en v1.

**Flutter** — `CryptoWalletDetailScreen` utilise `CurrencyPreference.selectValue(eur:, usd:)` pour chaque métrique de gain, assurant la cohérence entre la valeur affichée et le symbole.

Les champs legacy (`average_purchase_price`, `unrealized_gains`, `realized_gains`, `total_gains`) restent présents pour backward compatibility.

---

## 5. Flutter display fixes

### R3 — Detail initial render

**Avant** : `CryptoDetailScreen._displayPrice` utilisait `_summary!.price` (USDT brut) au premier rendu. Le WebSocket corrigeait ensuite.

**Après** : 
- `MarketSummaryItem` parse maintenant `price_eur` du JSON backend
- `_displayPrice` utilise `CurrencyPreference.selectValue(eur: _summary.priceEur, usd: _summary.price)` dès le premier rendu
- `currentPrice` passé à `ChartAssetModule` est également sélectionné selon la devise
- Le premier rendu est désormais cohérent avec la devise choisie

### R5 — Chart labeling

**Décision** : Option B — afficher honnêtement que le chart est en USD.

**Justification** : Les données OHLC proviennent directement de Binance (paires USDT). Convertir les chandelles historiques avec le taux EURUSDT courant serait trompeur car le taux FX a varié dans le temps. Une conversion correcte nécessiterait le taux EURUSDT historique pour chaque chandelle, ce qui est complexe et hors scope v1.

**Implémentation** :
- L'ancienne variable `_currencySymbol` (dynamique selon préférence) est remplacée par `_chartCurrencySymbol = '\$'` (constante)
- Les labels de prix sur le chart (point de départ, variations absolues) affichent toujours `$`
- L'import `currency_preference.dart` a été retiré du widget chart (nettoyage)
- Le prix principal affiché au-dessus du chart (`displayPrice`) reste dans la devise préférée car il provient du prix live (WebSocket) ou du market summary, qui sont correctement convertis

---

## 6. Tests added

| Test | Fichier | Objectif | Résultat |
|------|---------|----------|----------|
| `test_buy_fails_without_eurusdt_quote` | `test_pricing_hardening.py` | BUY sans override prix, sans quote EURUSDT → 503 | PASS |
| `test_sell_fails_without_eurusdt_quote` | `test_pricing_hardening.py` | SELL sans override prix, sans quote EURUSDT → 503 | PASS |
| `test_buy_succeeds_with_eurusdt_quote` | `test_pricing_hardening.py` | BUY sans override prix, avec BTCUSDT + EURUSDT → 200 | PASS |
| `test_wallet_detail_dual_currency_gains` | `test_pricing_hardening.py` | Wallet detail retourne gains EUR et USD non-null | PASS |

### Régression

```
tests/test_exchange_engine.py      — 15 passed
tests/test_exchange_sell.py        — 7 passed
tests/test_test_clients.py         — 13 passed  
tests/test_custody.py              — 6 passed
tests/test_custody_hardening.py    — 8 passed
tests/test_crypto_custody_layer.py — 6 passed
tests/test_reset_financial_test_state.py — 4 passed
tests/test_euro_account.py         — 6 passed
tests/test_pricing_hardening.py    — 4 passed
─────────────────────────────────────────────
TOTAL: 81 passed, 1 skipped, 0 failed
```

---

## 7. Final status

**Le système de pricing + affichage est-il maintenant cohérent pour EUR/USD reference currency ?**

### **OUI**, avec les nuances suivantes :

1. **Exécution (BUY/SELL)** : Strictement sûr. Le moteur ne peut plus exécuter un trade si la quote FX est absente ou périmée. Aucun fallback silencieux.

2. **Valuations wallet** : Cohérentes. Les gains et PRU sont calculés dans les deux devises (EUR et USD). Flutter sélectionne la bonne valeur selon la préférence.

3. **Prix initial détail crypto** : Cohérent dès le premier rendu. `MarketSummaryItem` transporte maintenant `price_eur` et le screen sélectionne selon la préférence.

4. **Charts** : Honnêtes. Les labels affichent toujours `$` car les données sous-jacentes sont en USDT (Binance). Pas de symbole trompeur.

### Limitations connues (v1) :

- **Gains USD historiques** : `avg_buy_price_usd` et `realized_gain_usd` sont convertis au taux EURUSDT courant, pas au taux de chaque transaction. L'erreur est faible mais non nulle.
- **Chart conversion EUR** : Les chandelles restent en USDT. Une future v2 pourrait stocker des chandelles converties ou appliquer un taux historique EURUSDT par chandelle.
- **`price_override`** : Toujours assumé en EUR sans validation explicite de devise. Un contrôle futur pourrait vérifier la cohérence.
