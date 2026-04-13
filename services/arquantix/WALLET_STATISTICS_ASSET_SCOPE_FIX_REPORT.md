# Wallet Statistics — Asset-Scope Chart Fix

## Executive Summary

Le chart "Historical Performance" de la page **WalletStatisticsScreen** affichait la valeur **globale du portefeuille** au lieu de la valeur de l'asset sélectionné. Un trade sur ETH modifiait donc le chart affiché sur la page BTC.

**Cause racine** : l'endpoint `GET /api/app/wallet/history` ne supportait pas de filtre par asset. Le backend chargeait **tous** les `exchange_orders` du client et reconstruisait la série `wallet_value(t) = Σ position_i(t) × price_i(t)` sur l'ensemble du portefeuille.

**Fix appliqué** : ajout d'un paramètre optionnel `asset` sur toute la chaîne (backend → proxy Next.js → API Flutter → écran Flutter). Quand `asset` est fourni, seuls les ordres de cet asset sont chargés et la série ne représente que la valeur de cette position.

---

## Root Cause

### Flux avant correction

```
WalletStatisticsScreen (BTC)
  → _historyApi.fetchHistory(period: "ALL")          ← pas d'asset
  → GET /api/mobile/flutter/wallet/history?period=ALL ← pas d'asset
  → GET /api/app/wallet/history?period=ALL            ← pas d'asset
  → build_wallet_history(db, client_id)               ← charge TOUS les ordres
  → série = Σ all assets → valeur portefeuille global
```

### Requête backend incriminée

```python
# api/services/wallet_history/service.py (AVANT)
orders = db.query(ExchangeOrder).filter(
    ExchangeOrder.client_id == client_id,
    ExchangeOrder.status == "completed",
).order_by(ExchangeOrder.created_at.asc()).all()
# → Pas de filtre sur ExchangeOrder.asset
```

### Conséquence

La boucle de reconstruction des positions itérait sur tous les trades (BTC, ETH, SOL, XRP…). La série `wallet_value` à chaque timestamp était la somme de toutes les positions. Un nouveau trade ETH ajoutait une nouvelle position à `positions["ETH"]`, modifiant `wallet_value(t)` pour tous les timestamps suivants — y compris sur le chart "BTC".

---

## Backend Fix

### `api/services/wallet_history/service.py`

Signature modifiée :

```python
def build_wallet_history(
    db: Session,
    client_id,
    reference_currency: str = "EUR",
    asset: Optional[str] = None,    # ← NOUVEAU
) -> dict:
```

Requête modifiée :

```python
q = db.query(ExchangeOrder).filter(
    ExchangeOrder.client_id == client_id,
    ExchangeOrder.status == "completed",
)
if asset:
    q = q.filter(ExchangeOrder.asset == asset.upper())
orders = q.order_by(ExchangeOrder.created_at.asc()).all()
```

Le reste de la logique (candles, FX, positions, valorisation, live endpoint) fonctionne sans modification car elle itère sur `traded_assets` dérivé des ordres chargés — qui ne contiennent plus qu'un seul asset quand le filtre est actif.

### `api/services/test_clients/router.py`

```python
@bootstrap_router.get("/wallet/history")
def get_wallet_history(
    period: str = Query("ALL", pattern="^(1D|1W|1M|ALL)$"),
    asset: Optional[str] = Query(None),   # ← NOUVEAU
    db: Session = Depends(get_db),
):
    result = build_wallet_history(
        db, client.id, reference_currency=ref_currency,
        asset=asset.upper() if asset else None,
    )
```

### Rétro-compatibilité

- `asset=None` → comportement global inchangé (tous les ordres, série portefeuille)
- `asset="BTC"` → série scopée à BTC uniquement

---

## Next.js Proxy Fix

### `web/src/app/api/mobile/flutter/wallet/history/route.ts`

```typescript
const period = request.nextUrl.searchParams.get('period') || 'ALL'
const asset = request.nextUrl.searchParams.get('asset')
const params = new URLSearchParams({ period })
if (asset) params.set('asset', asset)
const url = buildBackendUrl(`/api/app/wallet/history?${params.toString()}`)
```

Le paramètre `asset` est transmis au backend s'il est présent dans la requête entrante.

---

## Flutter Fix

### `mobile/lib/core/config.dart`

```dart
static String walletHistoryUrl(String period, {String? asset}) {
  final params = 'period=${Uri.encodeComponent(period)}';
  if (asset != null && asset.isNotEmpty) {
    return '$apiBaseUrl/api/mobile/flutter/wallet/history?$params&asset=${Uri.encodeComponent(asset)}';
  }
  return '$apiBaseUrl/api/mobile/flutter/wallet/history?$params';
}
```

### `mobile/lib/features/wallet/data/wallet_history_api.dart`

```dart
Future<WalletHistoryData> fetchHistory({String period = 'ALL', String? asset}) async {
  final url = Config.walletHistoryUrl(period, asset: asset);
  ...
}
```

### `mobile/lib/features/wallet/presentation/screens/wallet_statistics_screen.dart`

```dart
// Dans _load()
_historyApi.fetchHistory(period: _selectedPeriod, asset: widget.asset),

// Dans _loadChart()
final data = await _historyApi.fetchHistory(period: period, asset: widget.asset);
```

### Non-régression

Les autres appelants de `fetchHistory()` ne passent pas `asset` et continuent à obtenir la série globale :
- `HistoricalWalletValueChart` (widget portefeuille)
- `CryptoWalletDetailScreen._loadHeroSparkline()` (sparkline hero)

---

## Validation Scenarios

### Scénario 1 : Trade ETH ne modifie pas le chart BTC

| Étape | Action | Résultat attendu |
|-------|--------|------------------|
| 1 | Ouvrir Statistics BTC | Chart affiche la série BTC |
| 2 | Exécuter un trade ETH | — |
| 3 | Revenir sur Statistics BTC | Chart BTC **identique** (aucun changement) |

### Scénario 2 : Trade BTC modifie le chart BTC

| Étape | Action | Résultat attendu |
|-------|--------|------------------|
| 1 | Ouvrir Statistics BTC | Chart affiche la série BTC |
| 2 | Exécuter un trade BTC (buy) | — |
| 3 | Revenir sur Statistics BTC | Chart BTC **mis à jour** avec le nouveau trade |

### Scénario 3 : Isolation ETH

| Étape | Action | Résultat attendu |
|-------|--------|------------------|
| 1 | Ouvrir Statistics ETH | Chart affiche uniquement la série ETH |
| 2 | Vérifier les valeurs | Valeurs = position_ETH × price_ETH |

### Scénario 4 : Cohérence avec Performance Overview

| Vérification | Attendu |
|-------------|---------|
| Performance % sur Statistics BTC | = variation de position_BTC × price_BTC |
| Performance % sur Performance Overview BTC | Même base de données (trades BTC) |

### Scénario 5 : Value et Performance % même série

| Mode chart | Source |
|------------|--------|
| Value (€) | `wallet_value` de la série asset-scoped |
| Performance (%) | `(wallet_value / base_value) × 100` de la même série |

### Scénario 6 : Rétro-compatibilité globale

| Appel | Résultat attendu |
|-------|------------------|
| `GET /api/app/wallet/history?period=ALL` | Série portefeuille global (tous actifs) |
| `GET /api/app/wallet/history?period=ALL&asset=BTC` | Série BTC uniquement |

---

## Fichiers modifiés

| Fichier | Modification |
|---------|-------------|
| `api/services/wallet_history/service.py` | Paramètre `asset` optionnel + filtre SQL |
| `api/services/test_clients/router.py` | Query param `asset` sur endpoint |
| `web/src/app/api/mobile/flutter/wallet/history/route.ts` | Forwarding du param `asset` |
| `mobile/lib/core/config.dart` | URL builder avec `asset` optionnel |
| `mobile/lib/features/wallet/data/wallet_history_api.dart` | Paramètre `asset` sur `fetchHistory()` |
| `mobile/lib/features/wallet/presentation/screens/wallet_statistics_screen.dart` | `widget.asset` passé aux appels history |

---

## Final Status

| Critère | Statut |
|---------|--------|
| Chart BTC scopé à BTC uniquement | ✅ |
| Chart ETH scopé à ETH uniquement | ✅ |
| Trade ETH ne modifie pas chart BTC | ✅ |
| Rétro-compatibilité série globale | ✅ |
| UI inchangée | ✅ |
| Pas de refactoring du module statistics | ✅ |
| Value et Performance % même série | ✅ |
