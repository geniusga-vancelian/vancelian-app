# Rapport — warm-up première interaction (Flutter mobile)

**Périmètre :** `services/arquantix/mobile` — Login0, navigation vers téléphone, champ mobile, modales auth.  
**Objectif :** réduire le jank perçu au **premier** tap / focus / modale sans allonger artificiellement le splash ni introduire de hacks UX douteux.

---

## 1. Causes probables identifiées (audit)

| Zone | Cause | Pourquoi le 2ᵉ usage est plus fluide |
|------|--------|--------------------------------------|
| **Polices Inter (`GoogleFonts`)** | Résolution + sous-cache de glyphes pour des combinaisons graisse × taille non encore utilisées | Polices déjà en mémoire process |
| **`CircleFlag` (SVG)** | Premier paint = parse SVG + clip par drapeau | Préchargement via `CircleFlag.preload` |
| **`Navigator.push` + arbre Login** | Premier build JIT + layout de `LoginPhoneScreen`, `AppTopNavBar`, `AppPhoneInput`, etc. | Arbres et chemins déjà compilés |
| **Keychain / secure storage** | Premier `read` sur `FlutterSecureStorage` (email mémorisé) peut coûter sur device réel | Deuxième lecture plus rapide |
| **Clavier IME** | Coût **natif** (non contournable en Dart) + relayout `resizeToAvoidBottomInset` | IME déjà « chaud » |
| **Modales / bottom sheets** | Première route modale + `AnimationController` DS | Layers déjà compilés pour le gabarit |

Référence détaillée existante : `mobile/docs/FIRST_INTERACTION_JANK.md`.

---

## 2. Stratégie de warm-up retenue

### Service central : `AppWarmupService`

- **Fichier :** `lib/core/app_warmup_service.dart`
- **API :** `AppWarmupService.instance.scheduleDuringIntro(BuildContext context)`
- **Propriétés :**
  - **Non bloquant :** `Future` lancée depuis `addPostFrameCallback` ; rend la main entre phases (`Duration.zero`).
  - **Borné :** timeout **450 ms** sur la lecture Keychain (email) ; abandon silencieux si dépassement.
  - **Priorisé :**
    1. **Phase UI** — `GoogleFonts.pendingFonts` (liste Inter étendue : titres page, CTA, corps) + `CircleFlag.preload` (ISO2 EU + US/CA/MA alignés picker).
    2. **Phase stockage** — `SessionService.readLastLoginEmail()` pour réchauffer le chemin Keychain avant le même appel dans `LoginPhoneScreen._loadPrefs`.
  - **Idempotent :** chaque phase ne s’exécute qu’une fois par processus.

### Déclenchement pendant l’animation logo

- **`BrandHeroIntroPage`** appelle `_scheduleAppWarmupIfNeeded()` :
  - au premier `initState` **sans** `bootstrapPending` (après `_startIntroAfterSplash`) ;
  - quand `bootstrapPending` passe à `false` (`didUpdateWidget`), avec `Login0` actif.
- **Suppression** du double déclenchement depuis `WelcomeLandingScreen` : une seule source (intro) pour éviter la confusion et garantir le warm-up dès que Login0 est visible.

### Compatibilité

- `lib/core/interaction_warmup.dart` délègue vers `AppWarmupService` (imports existants, tests, secours `LoginPhoneScreen` inchangés).

---

## 3. Ce qui a été préchargé / initialisé

| Élément | Détail |
|---------|--------|
| **Inter** | Graisses / tailles couvrant titres (`AppPageTitle` / `AppTypography.pageTitle`), sous-titres login, boutons, corps |
| **Drapeaux** | Liste fixe ISO2 (même périmètre que l’ancien `interaction_warmup`) |
| **Keychain** | Lecture `loginLastEmail` (best-effort, timeout) |

---

## 4. Ce qui a été volontairement laissé de côté

| Sujet | Raison |
|-------|--------|
| **Ouverture clavier cachée pendant le splash** | Hack UX, risque App Store / ressenti bizarre ; rejeté |
| **Pré-instanciation cachée de `LoginPhoneScreen`** | Pas de navigation fantôme ; risque d’effets de bord (focus, lifecycle) |
| **Warm-up explicite de `Modale` / `showModalBottomSheet`** | Coût surtout au premier *show* réel ; pas de route sans contexte utilisateur propre |
| **`FlutterView.performWarmup`** (API expérimentale) | Non portable / version dépendante ; réservé si profiling le impose |
| **JetBrains Mono** (registration plus tard) | Hors premier écran téléphone ; allongerait la phase UI sans gain immédiat sur Login0 |

---

## 5. Ajustements annexes (inputs / handlers)

- **`LoginPhoneScreen`** : `FocusNode` créé avec l’écran et passé à `AppPhoneInput` (`phoneFocusNode`) pour éviter la création lazy du nœud interne au premier build du champ.
- **Boutons Login0** : `JankTrace.tap` puis `Navigator.push` — pas de travail lourd synchrone avant le push (inchangé ; vérifié).
- **`AppPhoneInput`** : instrumentation optionnelle `TRACE_JANK` pour le **premier** focus téléphone (début → premier frame).

---

## 6. Mesure / instrumentation

| Signal | Où |
|--------|-----|
| `flutter run --dart-define=TRACE_JANK=true` | `[TRACE_JANK]` tap → premier frame route ; modale ; **warmup_complete** (durée totale + phases ui/storage) ; premier focus téléphone |
| Debug / profile | `[AppWarmup] done Xms (ui=…ms storage=…ms)` (une ligne par exécution complète) |

Pas de surcharge en release si `TRACE_JANK` est absent ; logs `[AppWarmup]` utiles en debug/profile pour valider rapidement sur iPhone réel.

---

## 7. Impact attendu sur UX

- **Premier tap** « Créer un compte » / « Me connecter » : moins de pic polices + drapeaux + premier accès Keychain décalé sur la fenêtre Login0 (~2 s d’animation).
- **Premier focus** champ téléphone : légère réduction côté Dart (FocusNode prêt) ; le coût IME reste **natif**.
- **Modales** : gain indirect si les polices des feuilles sont déjà couvertes par la phase UI ; pas de garantie totale sans réduire la durée d’animation DS (hors scope).

---

## 8. Limites restantes

- **IME iOS** : premier affichage clavier reste coûteux ; seul le système peut le « préchauffer » sans hack.
- **Premier `Navigator.push`** : coût de construction d’arbre non nul même avec warm-up.
- **Réseau** : image hero Login0 / BFF config inchangés dans ce rapport.
- **Durée totale warm-up** : si Keychain est lent (première fois appareil), le timeout tronque à 450 ms — le second appel dans `LoginPhoneScreen` paiera le reste.

---

## 9. Recommandation de test (profile puis release)

1. **Profile mode** sur **iPhone réel** : `flutter run --profile --dart-define=TRACE_JANK=true`.
2. Vérifier les logs `[AppWarmup]` (temps global raisonnable, typiquement &lt; 1 s) et `[TRACE_JANK]` : **1er** push login vs **2e** (écart attendu réduit).
3. Tester **cold start** puis **tap rapide** sur « Me connecter » **pendant** l’animation logo (scénario le plus dur).
4. Répéter **sans** `--dart-define` pour valider le ressenti sans bruit console.
5. Si le jank persiste surtout **clavier** ou **blur** : cibler avec **Instruments** / Xcode **Time Profiler** + trace Flutter (hors scope de ce rapport).

---

## 10. First Navigation Jank (First Slide)

### Cause identifiée

Sur **iPhone**, le premier `Navigator.push` depuis Login0 utilisait par défaut **`MaterialPageRoute`** (Material 3). La **première** transition de page paie à la fois :

- la **compilation / premier usage** du pipeline d’animation Material (zoom / fade selon plateforme) ;
- le **premier build** complet de `LoginPhoneScreen` (arbre : `AppTopNavBar`, `AppPageTitle`, `AppPhoneInput` + `CircleFlag`, etc.) **pendant** l’animation ;
- des appels **`GoogleFonts.inter` dans `build`** pour le sous-titre et le lien « Autres options… », donc résolution de styles **à chaque rebuild** au mauvais endroit pour le premier frame.

Les transitions suivantes réutilisent les mêmes chemins de rendu et shaders déjà amortis — d’où la disparition ou la forte réduction du jank.

### Éléments déclenchés au premier push (rappel)

| Élément | Rôle |
|---------|------|
| `MaterialPageRoute` → première transition M3 | Coût shader / layer initial |
| Construction `LoginPhoneScreen` | `initState`, premier `build` |
| `GoogleFonts.inter` dans `build` | Travail évitable sur le hot path |
| Secours `scheduleInteractionWarmup` au 1er frame | Concurrence possible avec la fin du slide |

### Correctifs appliqués

1. **Route dédiée `authSlideRoute`** (`lib/core/navigation/auth_slide_route.dart`)  
   - **iOS** : `CupertinoPageRoute` — transition alignée sur le navigateur système, en général mieux amortie au **premier** slide.  
   - **Autres plateformes** : `MaterialPageRoute` **inchangé**.

2. **Login0** (`welcome_landing_screen.dart`)  
   - « Me connecter » et « Créer un compte » passent par `authSlideRoute` — **aucun** `await` ni logique métier avant le `push` (inchangé ; `JankTrace.tap` seulement).

3. **`LoginPhoneScreen`**  
   - Styles sous-titre + lien : **`GoogleFonts.inter` résolus dans `initState`**, stockés dans `late final TextStyle`, plus d’appels dans `build`.  
   - Secours **`scheduleInteractionWarmup`** : décalé au **deuxième** `addPostFrameCallback` pour ne pas concurrencer le premier frame / la fin de l’animation de slide.

### Préchargé (inchangé côté warm-up global)

- Toujours via `AppWarmupService` : Inter (dont combinaisons utiles au login), drapeaux, Keychain email.  
- Aucun asset image additionnel sur l’écran téléphone (pas de `precacheImage` spécifique — pas d’image locale sur cette page).

### Volontairement non modifié

- **Pas** de widget offstage / navigation cachée pour pré-monter `LoginPhoneScreen`.  
- **Pas** de changement de `PageTransitionsTheme` global dans `AppTheme` (évite les effets de bord sur tout le `MaterialApp`).  
- **Autres** entrées vers `LoginPhoneScreen` (profil, API session, etc.) : peuvent réutiliser `authSlideRoute` plus tard pour cohérence ; hors scope minimal Login0.

### Impact sur la fluidité perçue

- **iOS** : premier slide Login0 → téléphone plus proche du comportement natif ; moins de travail Dart dans le premier `build` ; moins de contention avec le warm-up secours sur le même frame.  
- **Android / desktop** : même route Material qu’avant ; gain surtout via styles mis en cache dans `initState`.

---

## 11. First Frame & Shader Warmup Optimization

### Causes exactes du jank restant (avant cette passe)

- **Compilation GPU (Skia)** au premier dessin d’un type d’opération (coins arrondis, `saveLayer` + flou, dégradés) : coût typique 20–200 ms par famille de shaders, souvent visible comme **micro-saccade** sur la première animation ou la première feuille.
- **Premier** `showModalBottomSheet` / overlay : premier chemin de layout + `ClipRRect` + `Material` + barre type grabber — **sans** préparation, tout tombe sur le premier tap.
- Le warm-up **polices + drapeaux + Keychain** ne suffit pas à couvrir le **pipeline GPU** ni le **premier** arbre de feuille DS.

### Corrections apportées

1. **`PaintingBinding.shaderWarmUp`** (`lib/core/startup/arquantix_shader_warm_up.dart`)  
   - Configuré **avant** `WidgetsFlutterBinding.ensureInitialized()` dans `main.dart` (hors **web** : `ShaderWarmUp.execute` est essentiellement no-op sur web).  
   - Implémentation `ArquantixShaderWarmUp` : dessins ciblés sur `Canvas` (RRect, clip, cercle, gradient linéaire, `saveLayer` + `ImageFilter.blur` léger) pour forcer la compilation des shaders fréquents **au démarrage** plutôt qu’au premier slide / sheet.  
   - **Contrepartie produit** : léger coût supplémentaire sur le **premier** frame raster (souvent 100–200 ms après install / wipe de cache shader — documenté par Flutter) ; en échange, premier geste utilisateur plus stable.

2. **Primer overlay « feuille DS »** (`lib/core/startup/first_frame_interaction_primer.dart`)  
   - **Pas** de pré-instanciation de `LoginPhoneScreen` (évite double effet Keychain / lifecycle).  
   - Une **OverlayEntry** hors écran (`Positioned` négatif, `Opacity: 0`, `IgnorePointer`) avec gabarit proche de `BottomSheetContainer` (rayons 32/60), grabber, `Material` + `ClipRRect` + ligne de texte `bodyLarge` du thème.  
   - Insertion puis retrait au **frame suivant** — une peinture pour amortir le premier bottom sheet **réel** (picker pays, options connexion, etc.).  
   - Intégré dans `AppWarmupService` entre la phase polices/drapeaux et la phase Keychain ; idempotent ; **désactivé** sur web (`kIsWeb`).

### Impact mesuré (méthode)

- Logs `[AppWarmup] … overlay=Xms` et `[TRACE_JANK] warmup_complete … overlay=…` (si `TRACE_JANK=true`).  
- Comparaison subjective **profile** iPhone : premier slide + premier sheet après cette passe vs build précédent.

### Limitations restantes

- **Aucune** garantie « zéro frame dépassé » : IME natif, réseau, ou shaders très spécifiques non couverts par le warm-up canvas peuvent encore picoter une fois.  
- **Pré-instanciation** des écrans métier **non** faite (choix volontaire : pas de hack navigation / pas de double session).  
- **Net worth / source of wealth** : si ces feuilles vivent hors des gabarits rayons 32/60 ou avec beaucoup de logique métier au premier `build`, un pic résiduel est possible — affiner avec profiling ciblé si besoin.

---

## 12. Fichiers modifiés / ajoutés (résumé)

| Fichier | Rôle |
|---------|------|
| `lib/main.dart` | `PaintingBinding.shaderWarmUp` (non-web) avant `ensureInitialized` |
| `lib/core/startup/arquantix_shader_warm_up.dart` | Implémentation `ShaderWarmUp` (Skia) |
| `lib/core/startup/first_frame_interaction_primer.dart` | Overlay hors écran type feuille DS |
| `lib/core/app_warmup_service.dart` | Phase overlay + logs `overlay=` ; orchestration complète |
| `lib/core/jank_trace.dart` | `warmupComplete` avec durée `overlay` |
| `lib/core/interaction_warmup.dart` | Délégation vers `AppWarmupService` |
| `lib/core/navigation/auth_slide_route.dart` | **Cupertino** sur iOS, **Material** ailleurs — Login0 → téléphone |
| `lib/features/auth/presentation/widgets/brand_hero_intro/brand_hero_intro_page.dart` | Planification warm-up |
| `lib/features/auth/presentation/screens/welcome_landing_screen.dart` | `authSlideRoute` pour login / signup |
| `lib/features/security/login/presentation/login_phone_screen.dart` | `FocusNode`, styles Inter en `initState`, warm-up secours frame 2 |
| `lib/design_system/components/app_phone_input.dart` | Trace focus (TRACE_JANK) |

---

*Document généré dans le cadre du chantier warm-up première interaction — approche premium, mesurée, diff minimal.*
