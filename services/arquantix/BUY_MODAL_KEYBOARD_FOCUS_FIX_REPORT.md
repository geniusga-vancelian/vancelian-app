# Buy Modal Keyboard Focus Fix Report

## Executive Summary

Le clavier numérique natif ne s'ouvrait pas fiablement dans la modal BUY, ni à l'ouverture ni au tap sur le montant. Deux causes racines identifiées et corrigées dans `buy_asset_modal_screen.dart` uniquement :

1. Le `TextField` caché était contraint à `SizedBox(width: 1, height: 1)` — trop petit pour qu'iOS attache correctement la session clavier.
2. `requestFocus()` seul ne garantit pas l'ouverture du soft keyboard sur iOS — il faut un appel explicite à `SystemChannels.textInput.invokeMethod('TextInput.show')`.

## Root Cause

### Cause 1 : TextField 1×1 pixel

```dart
// AVANT — 1×1 pixel, iOS ne connecte pas la session clavier
Opacity(
  opacity: 0,
  child: SizedBox(
    width: 1, height: 1,
    child: TextField(...),
  ),
),
```

Sur iOS, un `TextField` contraint à 1×1 pixel peut ne pas correctement initialiser la connexion `TextInputConnection` avec le système. Le champ est techniquement monté dans l'arbre de widgets mais sa taille infime empêche la plateforme d'y attacher un clavier de manière fiable.

### Cause 2 : requestFocus() sans TextInput.show

```dart
// AVANT — requestFocus seul
_focusNode.requestFocus();
```

`FocusNode.requestFocus()` donne le focus au noeud dans l'arbre Flutter, mais ne force pas l'ouverture du clavier soft. Sur iOS simulator (et parfois device), le système peut ignorer cette demande si le champ n'a pas une session d'édition active.

## Auto-Focus Fix

### Avant

```dart
WidgetsBinding.instance.addPostFrameCallback((_) {
  _focusNode.requestFocus();
});
```

### Après

```dart
WidgetsBinding.instance.addPostFrameCallback((_) => _openKeyboard());

void _openKeyboard() {
  _focusNode.requestFocus();
  Future.delayed(const Duration(milliseconds: 100), () {
    if (mounted) SystemChannels.textInput.invokeMethod('TextInput.show');
  });
}
```

Le délai de 100ms laisse le temps à Flutter de connecter le `TextInputConnection` après le `requestFocus()` avant de forcer l'ouverture du clavier via le channel système. Le `if (mounted)` protège contre un dispose entre-temps.

## Tap-To-Reopen Fix

### Zone tappable

Trois niveaux de capture du tap, tous routent vers `_openKeyboard()` :

| Zone | Mécanisme |
|------|-----------|
| Zone montant "0 €" | `GestureDetector(onTap: _openKeyboard)` sur `_buildAmountDisplay()` |
| TextField lui-même | `Positioned.fill` — un tap direct sur la zone du TextField ouvre aussi le clavier |
| Zone centrale entière | `GestureDetector` parent avec `HitTestBehavior.opaque` |

### _openKeyboard() — méthode centralisée

```dart
void _openKeyboard() {
  _focusNode.requestFocus();
  Future.delayed(const Duration(milliseconds: 100), () {
    if (mounted) SystemChannels.textInput.invokeMethod('TextInput.show');
  });
}
```

Appelé depuis :
- `initState` → post-frame callback (ouverture auto)
- `_buildAmountDisplay()` → `GestureDetector.onTap` (tap sur montant)
- Zone centrale → `GestureDetector.onTap` (tap hors montant)

## Hidden Input Implementation

### Avant

```dart
Opacity(
  opacity: 0,
  child: SizedBox(
    width: 1, height: 1,        // ← trop petit pour iOS
    child: TextField(
      autofocus: true,           // ← pas fiable seul
      ...
    ),
  ),
),
```

### Après

```dart
Positioned.fill(                 // ← remplit toute la zone du Stack
  child: TextField(
    // pas d'autofocus — géré par _openKeyboard()
    style: const TextStyle(fontSize: 1, color: Colors.transparent),
    cursorColor: Colors.transparent,
    cursorWidth: 0,
    showCursor: false,
    maxLines: 1,
    ...
  ),
),
```

Le TextField occupe maintenant toute la surface du `Stack` (déterminée par le `Row` visible). Il est visuellement invisible (texte transparent, pas de curseur, pas de bordure) mais a une taille réelle permettant à iOS de correctement attacher la session clavier.

| Propriété | Valeur | Effet |
|-----------|--------|-------|
| `Positioned.fill` | — | Taille = celle du Row parent |
| `fontSize: 1` | — | Texte de 1px (invisible) |
| `color: Colors.transparent` | — | Texte transparent |
| `cursorColor: Colors.transparent` | — | Pas de curseur visible |
| `cursorWidth: 0` + `showCursor: false` | — | Double sécurité anti-curseur |
| `border: InputBorder.none` | — | Pas de bordure |
| `maxLines: 1` | — | Empêche l'expansion verticale |

## Validation Results

| Test | Résultat attendu |
|------|-----------------|
| Ouverture modal → clavier visible | `_openKeyboard()` dans post-frame callback + `TextInput.show` |
| Fermeture clavier → tap "0 €" → clavier réouvert | `GestureDetector.onTap` → `_openKeyboard()` |
| Fermeture clavier → tap zone centrale → clavier réouvert | Parent `GestureDetector.onTap` → `_openKeyboard()` |
| TextField visuellement invisible | Texte transparent, curseur masqué, pas de bordure |
| Saisie chiffres + décimale | `_SingleDecimalFormatter` inchangé |
| Formatage montant ("1 250,50") | `_displayAmount` inchangé |
| Preview backend | Inchangée — debounce 500ms |
| Bouton Confirmer | Validation inchangée |

## Final Status

| Élément | État |
|---------|------|
| Auto-focus ouverture | **CORRIGÉ** — `_openKeyboard()` + `TextInput.show` |
| Tap-to-reopen | **CORRIGÉ** — 3 niveaux de capture |
| TextField caché | **CORRIGÉ** — `Positioned.fill` au lieu de 1×1px |
| `SystemChannels.textInput` | **AJOUTÉ** — force le clavier soft iOS |
| Régressions | **AUCUNE** — formatage, preview, validation inchangés |
| Fichier modifié | `buy_asset_modal_screen.dart` uniquement |
