# Currency Fix Report

## Objectif

Supprimer tous les symboles monétaires hardcodés (`$`, `€`) dans les écrans de trading (alertes et ordres) et les remplacer par un formatage dynamique basé sur la devise de référence de l'utilisateur.

## État existant

Le projet disposait déjà de :

- **`CurrencyPreference`** (`core/currency_preference.dart`) — Singleton qui gère la devise de référence de l'utilisateur (EUR ou USD), synchronisé avec le backend
- **`CurrencyFormatter`** (`core/currency_formatter.dart`) — Utilitaire statique avec méthodes `price()`, `fiat()`, `priceRaw()`, `fiatRaw()`, `fiatLabel()`, `priceLabel()`, `symbol`
- **`pe_clients.reference_currency`** — Champ backend stockant la préférence (EUR par défaut)

Les écrans d'alertes (`create_alert_bottom_sheet.dart`, `alerts_list_screen.dart`) utilisaient **déjà** `CurrencyFormatter`.

## Fichiers corrigés

### Flutter — `orders_list_screen.dart`

| Avant | Après |
|-------|-------|
| `'@ ${_formatPrice(order.triggerPrice)} \$'` | `'@ ${CurrencyFormatter.price(order.triggerPrice)}'` |
| `'${_fmtPrice.format(o.amount)} €'` | `CurrencyFormatter.fiat(o.amount)` |
| `'Exécuté à ${_formatPrice(o.executionPrice!)} \$'` | `'Exécuté à ${CurrencyFormatter.price(o.executionPrice!)}'` |
| `o.isBuy ? '€' : o.asset` (unit pour partial) | `o.isBuy ? CurrencyFormatter.symbol : o.asset` |
| `_formatAmount(filled)` / `_formatAmount(requested)` | `CurrencyFormatter.fiatRaw(filled)` / `CurrencyFormatter.fiatRaw(requested)` |

Supprimés :
- `_fmtPrice` (local NumberFormat)
- `_fmtDate` (non utilisé)
- `_formatPrice()` (helper local)
- `_formatAmount()` (helper local)
- Import `package:intl/intl.dart` (plus nécessaire)

### Backend — `engine.py` (notifications)

| Avant | Après |
|-------|-------|
| `f"{asset} a franchi {price:,.2f} $"` | `f"{asset} a franchi {price:,.2f} USD"` |
| `(prix actuel : {current:,.2f} $)` | `(prix actuel : {current:,.2f} USD)` |

Les prix de marché crypto proviennent de Binance en USDT. Le symbole `$` ambigu est remplacé par `USD` explicite.

## Fichiers déjà conformes (aucun changement)

- `create_alert_bottom_sheet.dart` — Utilise déjà `CurrencyFormatter.price()`, `.symbol`, `.priceRaw()`
- `alerts_list_screen.dart` — Utilise déjà `CurrencyFormatter.price()`
- `create_order_bottom_sheet.dart` — Utilise déjà `CurrencyFormatter.price()`, `.fiatLabel()`, `.symbol`, `.priceRaw()`

## CurrencyFormatter — API existante

```dart
CurrencyFormatter.price(84250.5)    // → "84 250,50 €" ou "84,250.50 $"
CurrencyFormatter.fiat(100.0)       // → "100,00 €" ou "100.00 $"
CurrencyFormatter.priceRaw(84250.5) // → "84 250,50" ou "84,250.50"
CurrencyFormatter.fiatRaw(100.0)    // → "100,00" ou "100.00"
CurrencyFormatter.symbol            // → "€" ou "$"
CurrencyFormatter.code              // → "EUR" ou "USD"
CurrencyFormatter.fiatLabel("Montant")  // → "Montant (EUR)" ou "Montant (USD)"
CurrencyFormatter.priceLabel("Prix")    // → "Prix (EUR)" ou "Prix (USD)"
```

Le format s'adapte automatiquement à la locale (fr_FR pour EUR, en_US pour USD).

## Compatibilité

- Aucun breaking change
- Les notifications backend utilisent désormais "USD" au lieu de "$"
- Le payload des notifications contient toujours les valeurs numériques brutes pour le rendu côté client
