# Order Creation — USD Display Alignment Report

## Executive Summary

La feature ordres auto-exécutés (LIMIT / STOP) affiche désormais **tous les prix en USD ($)**, aligné sur la donnée marché native (Binance USDT). Les montants d'achat restent en EUR (devise de financement du wallet), les quantités de vente restent en unité crypto. Aucune autre surface de l'app n'est impactée.

## Screens Updated

### 1. `create_order_bottom_sheet.dart`

| Element | Avant | Après |
|---------|-------|-------|
| Header "Prix actuel" | `CurrencyFormatter.price()` (EUR/USD dynamique) | `CurrencyFormatter.priceUsd()` → toujours `$` |
| Label prix cible | `"Prix cible"` | `"Prix cible (USD)"` |
| Input prix — symbole | `CurrencyFormatter.symbol` (EUR/USD dynamique) | `CurrencyFormatter.usdSymbol` → toujours `$` |
| Input prix — hint | `CurrencyFormatter.priceRaw()` | `CurrencyFormatter.priceUsdRaw()` |
| Label montant (BUY) | `CurrencyFormatter.fiatLabel("Montant")` → "Montant (EUR)" ou "Montant (USD)" | `"Montant (EUR)"` — hardcodé |
| Label montant (SELL) | `"Quantité (BTC)"` | Inchangé |
| Input montant — prefix (BUY) | `CurrencyFormatter.symbol` → "€" ou "$" | `"€"` — hardcodé |
| Snackbar succès | `CurrencyFormatter.price()` | `CurrencyFormatter.priceUsd()` |

### 2. `orders_list_screen.dart`

| Element | Avant | Après |
|---------|-------|-------|
| Dialog annulation — prix | `CurrencyFormatter.price()` | `CurrencyFormatter.priceUsd()` |
| Card title — trigger price | `CurrencyFormatter.price()` | `CurrencyFormatter.priceUsd()` |
| Subtitle — execution price | `CurrencyFormatter.price()` | `CurrencyFormatter.priceUsd()` |
| Subtitle — amount (BUY) | `CurrencyFormatter.fiat()` / `.fiatRaw()` | `CurrencyFormatter.fiatEur()` / `.fiatEurRaw()` |
| Subtitle — unit (BUY) | `CurrencyFormatter.symbol` | `"€"` hardcodé |
| Distance % badge | Calculée vs `currentPrice` (USD natif) | Inchangé (déjà correct) |

### 3. `currency_formatter.dart`

Ajout de méthodes USD-spécifiques :

| Méthode | Signature | Usage |
|---------|-----------|-------|
| `priceUsd()` | `String priceUsd(double value)` | Prix marché formaté avec `$` |
| `priceUsdRaw()` | `String priceUsdRaw(double value)` | Prix marché sans symbole |
| `fiatEur()` | `String fiatEur(double value)` | Montant fiat EUR avec `€` |
| `fiatEurRaw()` | `String fiatEurRaw(double value)` | Montant fiat EUR sans symbole |
| `usdSymbol` | `const String` | Constante `$` |

## Currency Rules Applied

```
RULE 1: trigger_price    → always USD ($)
RULE 2: execution_price  → always USD ($)
RULE 3: current_price    → always USD ($)
RULE 4: suggestions      → computed from USD price, rounded to clean USD levels
RULE 5: distance %       → computed from USD prices
RULE 6: buy amount       → EUR (€) — wallet funding currency
RULE 7: sell quantity     → crypto unit (BTC, ETH...)
RULE 8: validation       → compared against currentPriceUsd
```

## Labels and Validation Fixes

| Label | Résultat |
|-------|----------|
| Prix actuel (header) | `"Prix actuel : 70,366.42 $"` |
| Prix cible (input label) | `"Prix cible (USD)"` |
| Prix cible (input prefix) | `$` |
| Montant achat (label) | `"Montant (EUR)"` |
| Montant achat (prefix) | `€` |
| Quantité vente (label) | `"Quantité (BTC)"` |
| Quantité vente (prefix) | `BTC` |

Validation :
- Direction `down` → prix cible doit être < prix actuel USD
- Direction `up` → prix cible doit être > prix actuel USD
- Messages d'erreur inchangés, comparaisons sur prix USD natifs

## Order List Alignment

| Affichage | Format |
|-----------|--------|
| Card title | `"BUY LIMIT @ 65,000 $"` |
| Exécuté | `"Exécuté à 65,012.50 $ · 100,00 €"` |
| Partiel (BUY) | `"Exécuté : 50,00 / 100,00 €"` |
| Partiel (SELL) | `"Exécuté : 0.3 / 0.5 BTC"` |
| Actif | `"100,00 € · Slip max 0.5%"` |
| Distance | `"+2.3 %"` (badge vert/rouge) |
| Dialog annulation | `"BUY LIMIT BTC @ 65,000 $"` |

## Remaining EUR Surfaces Unchanged

Les surfaces suivantes utilisent toujours `CurrencyFormatter.price()` / `.fiat()` (dynamique EUR/USD selon préférence utilisateur) et **ne sont pas impactées** :

- `create_alert_bottom_sheet.dart` — alertes simples
- `alerts_list_screen.dart` — liste des alertes
- Portfolio / wallet screens
- Global statistics / crypto statistics
- Dashboard / home screen

### 3. `crypto_wallet_detail_screen.dart`

| Element | Avant | Après |
|---------|-------|-------|
| `currentPrice` passé à `OrdersListScreen` | `_livePrice` (EUR si pref EUR) | `_livePriceUsd` (toujours USD natif) |
| `currentPrice` passé à `AlertsListScreen` | `_livePrice` | Inchangé — les alertes gardent la devise utilisateur |

Ajout du champ `_livePriceUsd` alimenté par `QuoteUpdate.price` (WebSocket) et `MarketSummaryItem.price` (REST).

### 4. `crypto_detail_screen.dart`

| Element | Avant | Après |
|---------|-------|-------|
| `currentPrice` passé à `OrdersListScreen` | `_livePrice ?? _summary?.price` (EUR si pref EUR) | `_livePriceUsd ?? _summary?.price` (toujours USD) |
| `currentPrice` passé à `AlertsListScreen` | `_livePrice ?? _summary?.price` | Inchangé |

Ajout du champ `_livePriceUsd` alimenté par `QuoteUpdate.price` (WebSocket) et `MarketSummaryItem.price` (REST).

## Final Status

- **5 fichiers modifiés** : `currency_formatter.dart`, `create_order_bottom_sheet.dart`, `orders_list_screen.dart`, `crypto_wallet_detail_screen.dart`, `crypto_detail_screen.dart`
- **0 fichier backend modifié** — le moteur reste inchangé
- **0 surface portfolio/stats/alertes impactée**
- **Feature ordres 100% USD côté prix** — de la source de données jusqu'à l'affichage
- **Montants BUY explicitement EUR**, **quantités SELL en crypto**
- **Root cause corrigée** : `currentPrice` passé aux ordres est désormais le prix USD natif (`QuoteUpdate.price`) et non plus la valeur convertie par `CurrencyPreference`
