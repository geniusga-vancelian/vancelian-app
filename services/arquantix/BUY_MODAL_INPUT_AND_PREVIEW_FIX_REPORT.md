# Buy Modal Input & Preview Fix Report

## Executive Summary

Deux corrections chirurgicales dans `buy_asset_modal_screen.dart` :

1. **Input focus** : la zone du montant ("0 €") est désormais explicitement tappable — un `GestureDetector` dédié wrape le `Stack` du montant et route `onTap` vers `_focusNode.requestFocus()`. Le clavier natif numérique s'ouvre/se rouvre à chaque tap.

2. **Suppression du calcul local** : le fallback `amountFiat / unitPrice` qui estimait le crypto localement a été entièrement supprimé. L'affichage crypto provient **exclusivement** de la preview backend (`estimated_crypto_net`). Sans preview, l'UI affiche "0 BTC" ou "Prix indisponible".

## Input Focus Fix

### Avant

Le `Stack` contenant le montant affiché et le `TextField` caché n'avait pas de handler tap dédié. Le focus ne pouvait être restauré que via le `GestureDetector` parent (toute la zone centrale), ce qui ne couvrait pas le cas où l'utilisateur tapait spécifiquement sur le texte du montant après fermeture du clavier.

### Après

```dart
Widget _buildAmountDisplay() {
  return GestureDetector(
    onTap: () => _focusNode.requestFocus(),
    behavior: HitTestBehavior.opaque,
    child: Stack(
      // ... montant + TextField caché
    ),
  );
}
```

Le `HitTestBehavior.opaque` garantit que toute la surface du `Stack` (y compris les zones transparentes entre le texte) est réactive au tap.

## Native Keyboard Behavior

| Scénario | Résultat |
|----------|----------|
| Ouverture de la modal | Clavier auto-ouvert (`autofocus: true` + `addPostFrameCallback`) |
| Tap sur "0 €" | Clavier ré-ouvert via `_focusNode.requestFocus()` |
| Tap après fermeture manuelle | Clavier ré-ouvert |
| Tap sur zone centrale (hors montant) | Clavier ré-ouvert (GestureDetector parent) |
| Type de clavier | `TextInputType.numberWithOptions(decimal: true)` |

## Preview Data Source Fix

### Avant

```dart
// Fallback local — SUPPRIMÉ
final estimated = (widget.unitPrice != null &&
        widget.unitPrice! > 0 &&
        _parsedAmount > 0)
    ? _parsedAmount / widget.unitPrice!
    : null;
```

Ce calcul `amountFiat / unitPrice` ne prenait en compte ni le ask, ni le spread, ni le FX, ni les fees. Il produisait une estimation trompeuse différente de ce que le backend exécuterait réellement.

### Après

L'affichage crypto provient **uniquement** de `_preview.estimatedCryptoNet`, qui est le résultat du `POST /api/app/exchange/buy/preview` backend. Ce preview utilise exactement la même logique que le BUY réel :

- `_resolve_price()` → ask + spread + FX EURUSDT
- `volume_raw = fiat_amount / price`
- `fee_crypto = volume_raw * fee_bps / 10000`
- `estimated_crypto_net = volume_raw - fee_crypto`

### États d'affichage

| Condition | Affichage |
|-----------|-----------|
| Aucun montant saisi | `0 BTC` |
| Preview en cours (loading) | Spinner + "Estimation..." |
| Preview reçue | `≈ 0.01602 BTC` + `(frais 0.00008 BTC)` |
| Preview en erreur | `Prix indisponible` |
| Montant modifié (debounce) | Spinner puis nouveau résultat |

## Local Estimation Removal

| Élément | Statut |
|---------|--------|
| `amountFiat / unitPrice` fallback | **SUPPRIMÉ** |
| `widget.unitPrice` paramètre | **CONSERVÉ** (backward compatible, non utilisé dans la logique) |
| Source unique de vérité | `BuyPreviewResult.estimatedCryptoNet` via backend |
| Debounce preview | 500ms (inchangé) |

## Validation Scenarios

| Test | Résultat attendu |
|------|-----------------|
| Tap sur "0 €" | Clavier numérique natif s'ouvre |
| Re-tap après fermeture clavier | Clavier se rouvre |
| Saisie "1000" | Preview backend → "≈ 0.01602 BTC" |
| Crypto affiché = preview backend | Oui, `estimated_crypto_net` exactement |
| Aucun calcul local visible | Confirmé — code supprimé |
| Cohérence avec admin web market execution | Oui — même `_resolve_price()` |
| Backend offline | "Prix indisponible" (pas d'estimation locale trompeuse) |

## Final Status

| Élément | État |
|---------|------|
| Montant tappable | **CORRIGÉ** |
| Clavier natif | **FONCTIONNEL** (ouverture + ré-ouverture) |
| Calcul local supprimé | **OUI** |
| Source unique = preview backend | **OUI** |
| Backward compatible | **OUI** (`unitPrice` param conservé) |
| Linters | **0 erreurs** |
| Fichier modifié | `buy_asset_modal_screen.dart` uniquement |
