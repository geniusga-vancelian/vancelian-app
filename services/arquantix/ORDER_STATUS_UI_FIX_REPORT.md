# Order Status UI Fix Report

## Mapping ajouté

| `execution_status` | `status` | Label UI | Couleur | Icône |
|--------------------|----------|----------|---------|-------|
| `"executed"` | triggered | **Exécuté** | Vert | `check_circle` |
| `"partial"` | triggered | **Partiel** | Orange | `pie_chart` |
| `"failed"` | triggered | **Échoué** | Rouge | `error` |
| `"pending"` | triggered | **En cours** | Bleu | `hourglass_top` |
| `null` | triggered | **En cours** | Bleu | `hourglass_top` |
| — | cancelled | **Annulé** | Gris | — |
| — | active | **Actif** | Vert/Rouge (side) | bouton annuler |

**"Déclenché" supprimé** — ce n'est pas un état final, c'est un état transitoire interne.

## Fichiers modifiés

### 1. `trigger_order.dart` (modèle)

Ajout du getter `isPending` :

```dart
bool get isPending => executionStatus == 'pending' ||
    (isTriggered && executionStatus == null);
```

Couvre le cas normal (`pending`) et le edge case (`triggered` sans `execution_status`).

### 2. `orders_list_screen.dart` (UI)

| Composant | Avant | Après |
|-----------|-------|-------|
| `_StatusBadge` | 6 branches dont "Déclenché" | 6 branches : Exécuté → Partiel → Échoué → En cours → Annulé → Actif |
| `_StatusBadge` couleur échoué | Orange | **Rouge** |
| `_OrderCard` icône trailing | Pas d'icône pour pending | **Hourglass bleu** pour pending |
| `_OrderCard` icône failed | Orange | **Rouge** |
| `_subtitle` | Pas de cas pending | **"Exécution en cours · montant"** |
| `_subtitle` failure_reason | Brut (ex: `slippage_exceeded`) | **Humanisé** (ex: "Slippage trop élevé") |

## Labels et Validation Fixes

### Subtitles par statut

| Statut | Subtitle affiché |
|--------|-----------------|
| Actif | `"100,00 € · Slip max 0.5%"` |
| En cours | `"Exécution en cours · 100,00 €"` |
| Exécuté | `"Exécuté à 70,012.50 $ · 100,00 €"` |
| Partiel | `"Partiel : 50,00 / 100,00 €"` |
| Échoué | `"Échoué : Slippage trop élevé · 100,00 €"` |
| Annulé | `"Annulé · 100,00 €"` |

### Humanisation des raisons d'échec

| `failure_reason` brut | Label UI |
|-----------------------|----------|
| `slippage_exceeded` | Slippage trop élevé |
| `price_moved_beyond_safety` | Prix hors limites |
| `zero_fill` | Aucune exécution |
| `all_attempts_failed` | Tentatives épuisées |
| `missing_side_or_amount` | Paramètres manquants |
| `exchange_error` | Erreur exchange |
| `null` | Erreur |
| autre | affiché tel quel |

## Edge cases traités

| Cas | Comportement |
|-----|-------------|
| `status=triggered`, `execution_status=null` | Affiché "En cours" (bleu) via `isPending` |
| `status=triggered`, `execution_status=pending` | Affiché "En cours" (bleu) |
| `execution_status=failed`, `failure_reason=null` | Affiché "Échoué : Erreur" |
| `execution_status` inconnu | Tombe dans "Actif" (fallback) |

## Avant / Après

### Avant
- `status=triggered` + `execution_status=failed` → **"Déclenché"** (orange) — incorrect
- `status=triggered` + `execution_status=pending` → **"Déclenché"** (orange) — trompeur
- `failure_reason=slippage_exceeded` → affiché brut

### Après
- `status=triggered` + `execution_status=failed` → **"Échoué"** (rouge) + raison humanisée
- `status=triggered` + `execution_status=pending` → **"En cours"** (bleu) + hourglass
- `failure_reason=slippage_exceeded` → **"Slippage trop élevé"**

## Final Status

- **2 fichiers modifiés** : `trigger_order.dart`, `orders_list_screen.dart`
- **"Déclenché" entièrement supprimé** de la feature ordres
- **Mapping basé sur `execution_status`** — état final fiable
- **Raisons d'échec humanisées** pour l'UX
- **Edge case couvert** : `triggered` sans `execution_status`
