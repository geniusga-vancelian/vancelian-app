# Flutter Wallet History Chart Integration Report

## 1. Executive Summary

- **Chart branché sur le backend** : OUI — le widget `HistoricalWalletValueChart` appelle `GET /api/app/wallet/history?period=...` via le proxy Next.js et affiche la série retournée.
- **Mock retiré** : OUI — le hero sparkline n'affiche plus `mockLineChartData100` ; il est vide tant que les données réelles ne sont pas chargées, puis alimenté par la série historique du backend.
- **Niveau de confiance** : ÉLEVÉ — le flux complet (API → modèles → widget → hero) est cohérent et fonctionnel.

---

## 2. Files modified

| Fichier | Rôle |
|---------|------|
| `mobile/lib/features/wallet/presentation/widgets/historical_wallet_value_chart.dart` | Widget chart refactoré : shimmer loading, error avec bouton Réessayer, empty state, valeur actuelle + variation, transition fluide entre périodes |
| `mobile/lib/features/wallet/presentation/screens/crypto_wallet_detail_screen.dart` | Hero sparkline : remplacement du fallback mock par `SizedBox` vide quand les données ne sont pas encore chargées |

### Fichiers existants non modifiés (déjà corrects)

| Fichier | Rôle |
|---------|------|
| `mobile/lib/features/wallet/data/wallet_history_api.dart` | API client : `WalletHistoryApi.fetchHistory(period)` |
| `mobile/lib/core/config.dart` | URL config : `Config.walletHistoryUrl(period)` |
| `mobile/lib/core/currency_preference.dart` | Singleton devise de référence |
| `web/src/app/api/mobile/flutter/wallet/history/route.ts` | Proxy Next.js |

---

## 3. Data flow

### Endpoint utilisé
```
GET /api/app/wallet/history?period=1D|1W|1M|ALL
```

Le proxy Next.js (`/api/mobile/flutter/wallet/history`) forward vers le backend FastAPI.

### State local
Le widget `HistoricalWalletValueChart` gère son propre state :
- `_period` : période sélectionnée (défaut : `ALL`)
- `_data` : `WalletHistoryData?` (currency + points)
- `_loading` : chargement initial (affiche shimmer)
- `_switching` : changement de période (overlay subtil sur le chart existant)
- `_error` : message d'erreur si l'API échoue

### Refresh période
Quand l'utilisateur sélectionne une nouvelle période :
1. `_switching = true` → overlay semi-transparent avec petit spinner sur le chart existant
2. Appel API avec le nouveau `period`
3. Remplacement des données → le chart se redessine
4. Callback `onDataLoaded` → la sparkline du hero se met à jour

---

## 4. UI integration

### Position du chart
Première carte de contenu dans `CryptoWalletDetailScreen`, juste sous le hero orange, avant la carte "Key Information" et "Transactions history".

### Composition du widget chart

```
┌───────────────────────────────────────────┐
│ Historique de valeur                       │
│                                           │
│ 1 234,56 €    +5.2%    +61,23 €           │
│                                           │
│ [1D] [1W] [1M] [ALL]                     │
│                                           │
│ ╭────────────────────────────────╮        │
│ │         courbe lissée          ●        │
│ │     avec dégradé sous          │        │
│ ╰────────────────────────────────╯        │
└───────────────────────────────────────────┘
```

### Hero sparkline
- Le hero affiche une `LineChartModule` avec les données normalisées [0..1] issues du chart actif.
- Quand `_heroSparkline == null` (pas encore chargé) : `SizedBox(height: 80)` vide au lieu du mock.
- Dès que le chart charge ses données, `onDataLoaded` alimente le hero avec les vraies données.
- La sparkline du hero reflète toujours la période actuellement sélectionnée.

### Périodes
| Bouton | Appel API |
|--------|-----------|
| 1D | `period=1D` |
| 1W | `period=1W` |
| 1M | `period=1M` |
| ALL | `period=ALL` |

Le backend choisit la granularité réelle (1m, 5m, 1h, 4h, 1d). Le Flutter ne recalcule rien.

---

## 5. Currency integration

- **Source de vérité** : `CurrencyPreference.instance.currency` (singleton)
- **Formateur** : `NumberFormat.currency` avec locale fr_FR / € ou en_US / $
- **Valeur affichée** : la série backend est déjà dans la devise de référence du client (le backend lit `pe_clients.reference_currency` et convertit)
- **Symbole** : le widget utilise `_activeFormatter` pour afficher la valeur courante et la variation avec le bon symbole (€ ou $)
- **Aucun hardcode** : pas de symbole EUR en dur

---

## 6. UI states

### Loading (premier chargement)
- **Shimmer chart animé** : une courbe ondulée semi-transparente avec une animation pulse (1.4s, ease-in-out)
- Le shimmer utilise `AnimationController` + `CustomPaint` avec `_ShimmerChartPainter`
- Pas d'écran vide brutal

### Empty (aucun trade)
- Icône chart discrète (opacité 40%)
- Texte : "Aucun historique pour le moment"
- Centré dans un `SizedBox(height: 160)`

### Error (API échouée)
- Icône cloud_off
- Texte : "Données indisponibles"
- **Bouton "Réessayer"** avec tap handler vers `_load()`
- Style discret, cohérent avec le design existant

### Switching (changement de période)
- Le chart existant reste visible
- Overlay semi-transparent + petit spinner centré
- Transition fluide, pas de flash blanc

---

## 7. Final status

**Does CryptoWalletDetail now display real wallet historical value data according to backend period/granularity rules?**

**YES** — sans réserve.

- Le chart utilise uniquement les données du backend (`GET /api/app/wallet/history`)
- Aucun mock n'est affiché
- Les 4 périodes (1D, 1W, 1M, ALL) appellent le bon endpoint
- La granularité est gérée côté backend (1m, 5m, 1h, 4h, 1d)
- La devise affichée suit `reference_currency` (EUR ou USD)
- Les états loading / empty / error sont gérés proprement
- La sparkline du hero reflète les données réelles de la période active
- Le changement de période est fluide
