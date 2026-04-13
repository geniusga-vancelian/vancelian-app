# Audit « first interaction jank » (Flutter mobile)

Document de diagnostic et plan de correction pour la latence au **premier** tap / focus / modale, avec références de code dans `services/arquantix/mobile`.

---

## 1. Synthèse exécutive

| Priorité | Cause racine probable | Pourquoi le 2ᵉ usage est fluide |
|----------|----------------------|--------------------------------|
| P0 | **Warmup polices + drapeaux trop tard** : avant correction, `scheduleInteractionWarmup` ne partait qu’après le 1er frame de `LoginPhoneScreen` avec **600 ms de délai** — un tap rapide sur Login0 arrivait **avant** la fin du warmup. | Après chargement, `GoogleFonts` et `CircleFlag` sont en cache process. |
| P0 | **Google Fonts (`GoogleFonts.inter`, etc.)** : résolution / sous-ensemble de glyphes au **premier** usage d’une combinaison graisse × taille non couverte par le thème. | Polices déjà résolues en mémoire. |
| P1 | **`CircleFlag` (SVG)** : premier paint = parse SVG + clip circulaire par drapeau ; liste pays = N drapeaux visibles. | Assets SVG déjà en cache (`CircleFlag.preload`). |
| P1 | **`Navigator.push` + construction d’arbre** : `LoginPhoneScreen` agrège `AppTopNavBar`, `AppPhoneInput`, `AppPrimaryButton`, modales potentielles — coût JIT + layout premier passage. | Arbres et chemins de rendu déjà compilés. |
| P2 | **Clavier + `resizeToAvoidBottomInset` + `AnimatedContainer`** : premier focus téléphone → IME natif + **relayout** ; deux `AnimatedContainer` (250 ms) sur la ligne pays + numéro. | Clavier déjà « warm » ; animations moins coûteuses. |
| P2 | **Modales / feuilles** : `Modale` utilise `AnimationController` **600 ms** ; `showModalBottomSheet` matérialise une nouvelle route + overlay. | Shaders / layers déjà compilés pour ce gabarit. |
| P3 | **`BackdropFilter` / blur** (shell, nav) : premier blur peut coûter cher sur certaines GPU. | Cache pipeline de rendu. |

---

## 2. Navigation / routes

### Mesure (intégrée)

- **`lib/core/jank_trace.dart`** : avec `--dart-define=TRACE_JANK=true` en debug, `JankTrace.tap` / `markRouteFirstFrame` mesurent **tap → premier frame** de la route poussée.
- Les logs affichent **`#n`** pour comparer **1er vs 2e** push (`login`, `register`, etc.).

### Preuves code

- **Login0 → téléphone** : `welcome_landing_screen.dart` — `JankTrace.tap('login'|'register')` puis `Navigator.push` → `LoginPhoneScreen`.
- **Premier frame cible** : `login_phone_screen.dart` — `JankTrace.markRouteFirstFrame('LoginPhoneScreen')` en `addPostFrameCallback` après `initState`.

### Ce qui est payé au premier affichage Login / Register

- Construction de **`LoginPhoneScreen`** (même widget pour les deux ; `signUpMode` change le flux API seulement).
- **`AppPhoneInput`** : `CircleFlag` + `TextField` + `AnimatedContainer` ×2.
- **`AppPrimaryButton`** : `GoogleFonts.inter` dans le style du label (voir `app_primary_button.dart`).
- **`_loadPrefs`** : `SessionService.readLastLoginEmail` — **async**, volontairement **après** le premier frame pour ne pas bloquer l’UI.

### Quick wins

- **Warmup dès Login0 prêt** : `welcome_landing_screen.dart` appelle `scheduleInteractionWarmup` en post-frame quand `!bootstrapPending`, et quand `bootstrapPending` passe à `false` (`didUpdateWidget`). Réduit le coût **sur** le premier `push` si l’utilisateur attend au moins un frame après l’écran d’accueil.
- Garder **`TRACE_JANK`** pour valider la régression sur device réel.

### Corrections plus profondes

- Remplacer progressivement les `GoogleFonts.*` **dans** `build` par `Theme.of(context).textTheme` + `copyWith` là où le style suit déjà Inter du thème (`core/theme/app_theme.dart` + `AppTypographyTheme`).

---

## 3. Inputs / clavier

### Analyse ciblée (`AppPhoneInput`)

Fichier : `lib/design_system/components/app_phone_input.dart`.

- **Premier focus** : ouverture clavier IME (coût **natif**), + `setState` sur `_hasFocus` (bordure indigo), + `onChanged` → `setState` à chaque frappe.
- **AnimatedContainer** (250 ms) sur les deux moitiés : travail d’animation + layout quand l’état focus change.
- **Pas de formatter lourd** côté champ : numéro libre ; normalisation à l’envoi.
- **Theme local** autour du `TextField` (`textSelectionTheme`) : léger rebuild du sous-arbre au premier paint.

### Mesure manuelle recommandée

- **DevTools > Performance** : enregistrer du tap sur le champ jusqu’à frame stable après ouverture clavier.
- Option : ajouter un `Timeline`/`debugPrint` dans `_onFocusChange` (non commité) pour mesurer focus → `SchedulerBinding.instance.endOfFrame`.

### Quick wins

- Warmup **polices** + **drapeaux** avant le focus (voir §6).
- Si le profiling montre encore des pics : envisager **une seule** `AnimatedContainer` englobant la ligne, ou durée plus courte (sans changer le design de façon visible).

---

## 4. Modales / bottom sheets

### Exemple instrumenté

- **Picker pays** : `app_phone_input.dart` — `JankTrace.tap('modal_phone_country')` avant `showModalBottomSheet` ; `JankTrace.markModalFirstFrame('PhoneCodePickerSheet')` après le premier frame du sheet.

### Autres coûts typiques

- **`Modale` custom** (`modale.dart`) : `AnimationController` **600 ms** — sensation « lourde » + premier coût de compilation des layers.
- **Premier** `showModalBottomSheet` système : thème + route + MediaQuery `viewInsets`.

### Quick wins

- Warmup **GoogleFonts** pour tailles utilisées dans `AppSearchInput` / titres de feuilles.
- Réduire **duration** des animations feuilles custom (produit) si le ressenti reste lent — à valider UX.

---

## 5. Fonts / assets / SVG / images

| Élément | Où | Premier usage |
|---------|-----|----------------|
| **Inter** (multi graisses / tailles) | `GoogleFonts.inter` partout, `AppTypographyTheme`, `app_primary_button`, écrans login… | Résolution + sous-cache glyphes |
| **JetBrains Mono** | `registration_flow_screen.dart` | Idem, souvent plus tard dans le flux |
| **`CircleFlag`** | `app_phone_input`, pickers | Parse SVG + clip |
| **Images réseau** | Login0 (`CachedNetworkImage`) | Décode + cache disque (hors premier tap bouton si déjà affiché) |

### Stratégie de préchargement (légère)

Fichier : **`lib/core/interaction_warmup.dart`**

- `GoogleFonts.pendingFonts([...])` — combinaisons Inter les plus fréquentes sur auth / listes.
- `CircleFlag.preload([iso2...])` — jeu fixe EU + US/CA (aligné picker).

**Idempotent** : une seule exécution réussie par processus.

---

## 6. Widgets / build / initState

| Zone | Risque | Détail |
|------|--------|--------|
| `LoginPhoneScreen.initState` | Moyen | Post-frame trace + warmup (OK) ; `_loadPrefs` async (OK). |
| `_PhoneCodePickerSheet.initState` | Faible | `ScrollController` + recherche — coût modéré. |
| `AppTypography` getters | Moyen | Chaque getter appelle `GoogleFonts.inter(...)` — préférer styles **réutilisés** depuis `Theme` quand possible. |

---

## 7. Shaders / rendering

- **`BackdropFilter` + `ImageFilter.blur`** : présent dans `app_bottom_nav.dart`, `layout_page_level2/3`, `blurred_filter_bar`, etc. Premier blur sur une surface peut être coûteux ; peu lié au **premier tap Login** si l’écran courant n’affiche pas encore ces widgets.
- **Login0** : stack image + fondu — coût plutôt **décodage image** que blur (pas de `BackdropFilter` sur Login0 dans le flux analysé).

Warmup shader **global** : `FlutterView.performWarmup` (API expérimentale / version dépendante) — à n’utiliser que si le profiling le justifie ; **pas** ajouté par défaut ici.

---

## 8. Fichiers touchés par les correctifs récents

| Fichier | Rôle |
|---------|------|
| `lib/features/auth/presentation/screens/welcome_landing_screen.dart` | Warmup post-frame quand Login0 est actif (`bootstrapPending` false). |
| `lib/features/security/login/presentation/login_phone_screen.dart` | Warmup secours immédiat post-frame ; suppression du délai 600 ms. |
| `lib/core/interaction_warmup.dart` | Préchargement polices + drapeaux. |
| `lib/core/jank_trace.dart` | Compteur de taps ; trace modale. |
| `lib/design_system/components/app_phone_input.dart` | Trace picker pays. |
| `docs/FIRST_INTERACTION_JANK.md` | Ce document. |

---

## 9. Ordre de priorité d’implémentation

1. **Warmup sur Login0** + suppression du délai 600 ms sur l’écran téléphone (**fait**).
2. **Mesurer** avec `TRACE_JANK=true` sur device réel (1er vs 2e push, picker pays).
3. **Réduire `GoogleFonts` dans le hot path** : boutons et champs déjà partiellement alignés sur `Theme` — poursuivre sur `AppPrimaryButton` / écrans login si les traces le confirment.
4. **Modales** : ajuster durée animation `Modale` si UX OK ; `RepaintBoundary` sur listes très longues si besoin.
5. **Clavier** : affiner `AnimatedContainer` seulement si mesures focalisées le montrent.

---

## 10. Commandes utiles

```bash
cd services/arquantix/mobile
flutter run --dart-define=TRACE_JANK=true
```

Observer `[TRACE_JANK]` et `[interaction_warmup]`.

---

## 11. Correctifs historiques (référence)

- `AppPhoneInput` / `AppSheetListItem` : styles basés sur `Theme.of(context).textTheme` où applicable (réduction résolutions `GoogleFonts` au vol).
- `main.dart` : `_warmStartServices` post-frame pour ne pas bloquer le cold start (`AppInfoService`, `intl`).
