# Flutter — Confirmation Fixed Bottom Bar Fix

## Problème initial

Le bottom bar de l'écran Confirmation n'avait pas le même comportement que
l'écran Montant (référence) :

1. Pas de `SafeArea` sur le body → gestion bottom inset manuelle fragile
2. Pas de `color: AppColors.pageBackground` sur le Container → fond potentiellement transparent
3. Bouton back circle + bouton CTA en Row → layout différent du screen Montant
4. Typo du bouton en `bodyMedium` au lieu de `titleMedium` (≠ screen Montant)
5. `borderRadius: 16` hardcodé vs `AppRadius.button` (déjà corrigé précédemment)

## Correction

### Structure layout — avant / après

**Avant :**

```
Scaffold
├─ appBar: AppTopNavBar
└─ body: Column                          ← pas de SafeArea
   ├─ Expanded(SingleChildScrollView)
   └─ Container(no bg color)             ← bottom bar
      └─ Row [backCircle, button]        ← layout custom
```

**Après :**

```
Scaffold
├─ appBar: AppTopNavBar
└─ body: SafeArea(top: false)            ← bottom inset géré
   └─ Column
      ├─ Expanded(SingleChildScrollView)
      └─ Container(color: pageBackground) ← bottom bar avec fond
         └─ SizedBox(h:52, w:∞)           ← full width, comme Montant
            └─ ElevatedButton
```

### Changements détaillés

| Aspect | Avant | Après |
|--------|-------|-------|
| SafeArea body | Absente | `SafeArea(top: false)` |
| Bottom bar fond | Transparent | `AppColors.pageBackground` |
| Bottom bar contenu | `Row[backCircle, button]` | `SizedBox(52×∞)` + bouton full width |
| Bottom padding | `viewPadding.bottom > 0 ? 8 : 16` | Géré par `SafeArea` |
| Typo bouton | `bodyMedium` w600 | `titleMedium` w600 (= screen Montant) |
| Elevation disabled | `4` (fixe) | `0` quand `_executing` |

### Parité avec le screen Montant

Le screen Montant (`lending_invest_input_screen.dart`) utilise :

```dart
Scaffold(
  body: SafeArea(
    child: Column(
      children: [
        ...header/content...,
        Expanded(child: ...),
        _buildBottomBar(),          // ← fixé en bas
      ],
    ),
  ),
)
```

```dart
_buildBottomBar() → Container(
  padding: EdgeInsets.fromLTRB(lg, 12, lg, ...),
  decoration: BoxDecoration(border: Border(top: ...)),
  child: SizedBox(
    height: 52,
    width: double.infinity,
    child: ElevatedButton(...)
  ),
)
```

Le screen Confirmation reproduit maintenant exactement cette structure :
- `SafeArea` gère les insets
- `Column[Expanded(scroll), bottomBar]` sépare scroll et fixed
- Bouton full width, même hauteur (52px), même typo (`titleMedium` w600)
- Même padding et même bordure top

## Non-régression

| Invariant | Vérifié |
|-----------|---------|
| Logique preview | Inchangée |
| Logique invest | Inchangée |
| Steps module | Inchangé |
| Legal footer | Inchangée |
| CTA label | Inchangé |
| Navigation | Inchangée |
| Flutter analyze | **0 issues** |

## Compilation

```
$ flutter analyze lending_invest_preview_screen.dart
No issues found!
```
