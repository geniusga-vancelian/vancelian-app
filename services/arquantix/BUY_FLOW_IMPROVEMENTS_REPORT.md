# Buy Flow Improvements Report

## Executive Summary

Trois améliorations incrémentales appliquées au flow BUY mobile **sans casser l'existant** :

1. **Backend — Normalisation HTTP errors** : Un mapper centralisé (`error_mapper.py`) convertit chaque `ExchangeError` en un code HTTP sémantique (409/400/404/503) avec un body stable `{status, error_code, message}`. Les deux endpoints mobile (preview + buy) utilisent ce mapper.

2. **Flutter — Écran de confirmation post-trade** : Après un BUY réussi, un overlay premium animé (blur + fade + scale) affiche le résumé de l'achat pendant 1.5 secondes avant de fermer automatiquement la modal.

3. **Flutter — Sécurisation preview vs BUY** : Un `_previewReceivedAt` timestamp empêche toute exécution avec un prix stale (> 3s). Si la preview est périmée au clic, le bouton passe en mode "Vérification du prix…" et re-fetch automatiquement avant d'exécuter.

## HTTP Error Normalization

### Mapper centralisé

Fichier créé : `api/services/exchange/error_mapper.py`

```python
_ERROR_MAP = {
    UnsupportedAssetError:          (400, "UNSUPPORTED_ASSET"),
    InsufficientFundsError:         (409, "INSUFFICIENT_FUNDS"),
    InsufficientCryptoBalanceError: (409, "INSUFFICIENT_CRYPTO_BALANCE"),
    DuplicateOrderError:            (409, "DUPLICATE_ORDER"),
    AccountNotFoundError:           (404, "ACCOUNT_NOT_FOUND"),
    MarketQuoteStaleError:          (503, "MARKET_QUOTE_STALE"),
    PriceUnavailableError:          (503, "PRICE_UNAVAILABLE"),
    FxUnavailableError:             (503, "FX_UNAVAILABLE"),
}
```

### Response body (stable)

```json
{
  "status": "failed",
  "error_code": "INSUFFICIENT_FUNDS",
  "message": "insufficient_funds: available=1000, requested=2000"
}
```

### Endpoints mis à jour

| Endpoint | Avant | Après |
|----------|-------|-------|
| `POST /exchange/buy/preview` | Mix HTTPException + dict 200 | `raise_exchange_error()` uniforme |
| `POST /exchange/buy` | Mix HTTPException + dict 200 | `raise_exchange_error()` uniforme |

### Backward compatibility

Le Flutter `exchange_api.dart` parse maintenant :
- Les réponses HTTP 4xx/5xx avec `detail.error_code`
- Les anciennes réponses 200 avec `error` (fallback)
- Les anciennes réponses 200 avec `status: "failed"` (fallback)

## Success Overlay UX

### Widget : `_BuySuccessOverlay`

| Élément | Détail |
|---------|--------|
| Background | `BackdropFilter` blur 8px + overlay noir 45% |
| Container | Blanc arrondi 24px, ombre emerald douce |
| Icône | Cercle emerald (✓) 56×56 |
| Titre | "Achat exécuté" — bold |
| Crypto | "+0.01602 BTC" — emerald 28px bold |
| Fiat | "≈ 1 000,00 €" — gris secondaire |
| Frais | "Frais : 0.00008 BTC" — 12px gris |
| Animation entrée | Fade + Scale (easeOutBack) 250ms |
| Durée | 1.5 secondes puis auto-close |
| Après close | `Navigator.of(context).pop(true)` → refresh parent |

### Flow complet

```
Utilisateur clique Confirmer
  → [Vérification du prix…] (si preview > 3s)
  → [Exécution…]
  → BUY réussi
  → clavier masqué (_focusNode.unfocus())
  → showGeneralDialog(_BuySuccessOverlay)
  → 1.5s → auto-pop overlay
  → Navigator.pop(true) → CryptoWalletDetailScreen._load() + _loadHeroSparkline()
```

## Preview Race Condition Fix

### Problème résolu

Race condition entre saisie → debounce preview → clic Confirmer :
un utilisateur qui change le montant puis clique immédiatement sur Confirmer pouvait exécuter un BUY avec un prix stale (preview d'un montant précédent).

### Solution : `_previewReceivedAt` + freshness guard

```dart
static const _previewMaxAge = Duration(seconds: 3);

bool get _isPreviewFresh {
  if (_preview == null || _previewReceivedAt == null) return false;
  return DateTime.now().difference(_previewReceivedAt!) < _previewMaxAge;
}
```

### Comportement au clic Confirmer

```
if (!_isPreviewFresh) {
  → confirmPhase = refreshingPrice
  → re-fetch preview immédiate (sans debounce)
  → si erreur : afficher erreur, rester idle
  → si OK : mettre à jour preview + timestamp
}
confirmPhase = executing
→ executeBuy()
```

### Cas couverts

| Scénario | Résultat |
|----------|----------|
| Preview < 3s, clic Confirmer | Exécution directe |
| Preview > 3s, clic Confirmer | Re-fetch, puis exécution |
| Preview en cours, clic Confirmer | Bouton désactivé |
| Preview erreur, clic Confirmer | Bouton désactivé |
| Montant changé, debounce en cours | Bouton désactivé (preview null) |

## UI State Improvements

### Enum `_ConfirmPhase`

```dart
enum _ConfirmPhase { idle, refreshingPrice, executing }
```

### Labels du bouton

| Phase | Label | Visuel |
|-------|-------|--------|
| `idle` | "Confirmer" | Texte seul |
| `refreshingPrice` | "Vérification du prix…" | Spinner + texte |
| `executing` | "Exécution…" | Spinner + texte |

### Bouton pendant les phases actives

- Background reste `AppColors.indigo` (pas grisé)
- `onPressed: null` (empêche le double-tap)
- Spinner blanc 18px + label blanc

## Files Modified

### Backend

| Fichier | Changement |
|---------|-----------|
| `api/services/exchange/error_mapper.py` | **CRÉÉ** — mapper centralisé |
| `api/services/test_clients/router.py` | Simplifié : imports nettoyés, handlers uniformisés via `_raise_exchange_error()` |

### Flutter

| Fichier | Changement |
|---------|-----------|
| `mobile/lib/features/wallet/data/exchange_api.dart` | Parse `error_code` + `detail` body, `errorCode` dans `BuyResult` |
| `mobile/lib/features/wallet/presentation/screens/buy_asset_modal_screen.dart` | `_ConfirmPhase`, `_previewReceivedAt`, `_BuySuccessOverlay`, freshness guard, UX labels |

### Non modifié (non-régression)

- `exchange/service.py` — aucun changement
- `exchange/router.py` (admin) — aucun changement
- `exchange/schemas.py` — aucun changement
- `crypto_wallet_detail_screen.dart` — aucun changement
- `config.dart` — aucun changement

## Final Status

| Axe | État |
|-----|------|
| HTTP error normalization | **FAIT** — mapper centralisé, codes sémantiques |
| Success overlay | **FAIT** — blur + fade + scale, 1.5s auto-close |
| Race condition fix | **FAIT** — `_previewReceivedAt` + re-fetch guard 3s |
| UX bouton (3 phases) | **FAIT** — idle / refreshingPrice / executing |
| Backward compatibility | **OUI** — parse ancien + nouveau format |
| Non-régression | **OUI** — aucun fichier critique modifié |
| Linters | **0 erreurs** |
