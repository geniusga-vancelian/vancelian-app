# Alert UX Simplification Report

## Overview

Refonte complète de l'UX de création et de consultation des alertes prix Flutter.
Objectif : UX premium, simplifiée, en 3 interactions max.

---

## Before vs After

### Create Alert Bottom Sheet

| Aspect | Before | After |
|---|---|---|
| Direction selector | 2 chips texte long ("Monte au-dessus" / "Descend en-dessous") | Segmented control compact ("Au-dessus" / "En-dessous") avec icônes colorées (vert/rouge) |
| Price input | TextField basique avec label "Prix cible ($)" | Input premium avec symbole $ intégré, hint = prix actuel, bouton clear |
| Quick buttons | Aucun | +1%, +2%, +5% (up) / -1%, -2%, -5% (down) appliqués sur le prix actuel |
| Frequency | Switch "Alerte récurrente" + paragraphe explicatif | Segmented control minimaliste "Une seule fois" / "Toujours" |
| Validation | Erreur rouge générique | Hint contextuel orange avec icône info : "Le prix doit être supérieur au prix actuel" |
| Submit button | Bouton noir statique "Créer l'alerte" | Bouton coloré (vert/rouge selon direction) avec résumé dynamique : "Alerter si > 72,000 $" |
| Header | Titre simple + prix actuel texte | Badge asset coloré + titre + prix actuel |
| Interactions | 4+ (direction + toggle + prix + submit) | 3 max (direction + prix + confirm) |

### Alert List Screen

| Aspect | Before | After |
|---|---|---|
| Section headers | "Actives (3)" en gras | Label uppercase discret "ACTIVES" style institutionnel |
| Card design | ListTile standard avec margin | Card premium avec border colorée (active), shadow subtile |
| Direction icon | Trending up/down gris ou coloré | Arrow up/down dans cercle coloré (vert/rouge) |
| Price display | "BTC ↑ 70,000.00 $" | "BTC > 70,000 $" (notation financière) |
| Frequency badge | "↻ 3" en orange | Badge "Toujours" (orange) ou "Une fois" (gris) |
| Subtitle | Texte brut "Créé le..." | Info contextuelle enrichie : "3x déclenché · Dernier : 15 Mar 2026, 14:30" |
| Cancel button | IconButton close classique | Bouton discret dans container gris arrondi |
| Empty state | Icône + texte basique | Card centrée avec icône dans container, titre + description |
| Past alerts | Séparées "Déclenchées" + "Annulées" | Section unique "Historique" |

---

## UX Decisions

### 1. Segmented Control > Dropdown / Chips

Les segmented controls iOS-style sont plus intuitifs et plus rapides qu'un dropdown ou des chips textuels.
L'utilisateur voit immédiatement les 2 options sans interaction supplémentaire.

### 2. Quick % Buttons

Permettent de définir un prix cible en un tap.
Adaptés dynamiquement à la direction : +1/2/5% pour "Au-dessus", -1/2/5% pour "En-dessous".
Élimine le besoin de calcul mental.

### 3. Validation douce (hint orange vs erreur rouge)

Les erreurs rouges créent de l'anxiété.
Un hint orange informatif guide l'utilisateur sans le bloquer.
Le prix actuel est toujours visible comme référence.

### 4. Bouton contextuel

Le bouton de confirmation affiche un résumé de l'alerte ("Alerter si > 72,000 $").
L'utilisateur confirme visuellement ce qu'il crée avant de taper.
La couleur du bouton correspond à la direction (vert = au-dessus, rouge = en-dessous).

### 5. Fréquence simplifiée

"Alerte récurrente" avec un switch + paragraphe explicatif → remplacé par un simple choix binaire "Une seule fois" / "Toujours".
Plus clair, moins de surface UI.

### 6. Historique unifié

Les sections "Déclenchées" et "Annulées" sont fusionnées en "Historique".
L'état est communiqué par le style de la card (barrée, check icon, etc.) plutôt que par des sections séparées.

---

## Mapping to Backend

| UI | Backend field |
|---|---|
| "Au-dessus" | `direction = "up"` |
| "En-dessous" | `direction = "down"` |
| "Une seule fois" | `trigger_mode = "once"` |
| "Toujours" | `trigger_mode = "recurring"` |
| Prix saisi | `target_price` |
| Asset | `asset` |
| Source prix | `price_source = "mid"` (défaut, non exposé en UI) |

Aucune modification backend nécessaire. Le contrat API reste identique.

---

## Cleanup

Éléments supprimés de l'UX :

- **Switch "Alerte récurrente"** → remplacé par segmented control
- **Paragraphe explicatif** du mode récurrent → inutile avec le label "Toujours"
- **Chips direction verbose** ("Monte au-dessus" / "Descend en-dessous") → "Au-dessus" / "En-dessous"
- **Sections multiples historique** ("Déclenchées" + "Annulées") → section unique "Historique"
- **Erreurs rouges** → hints orange contextuels

---

## Future Extensibility

| Feature future | Préparation actuelle |
|---|---|
| Multi-asset alerts | Le `asset` est passé en paramètre, pas hardcodé |
| Price source selection (bid/ask) | Le champ `price_source` existe dans l'API et le modèle, masqué en UI |
| Order-type alerts (stop loss, take profit) | `action_type` et `order_payload` existent dans le backend |
| Cooldown configuration | `cooldown_seconds` existe dans l'API, peut être exposé en UI avancée |
| Distance to trigger (%) | Le calcul est trivial côté Flutter avec `currentPrice` et `targetPrice` |

---

## Files Modified

- `mobile/lib/features/alerts/presentation/screens/create_alert_bottom_sheet.dart` — refonte complète
- `mobile/lib/features/alerts/presentation/screens/alerts_list_screen.dart` — refonte complète

## Files NOT Modified (no changes needed)

- `mobile/lib/features/alerts/domain/models/price_alert.dart` — modèle inchangé
- `mobile/lib/features/alerts/data/price_alerts_api.dart` — API client inchangé
- Backend Python (router, engine, cache, models) — aucun changement requis
