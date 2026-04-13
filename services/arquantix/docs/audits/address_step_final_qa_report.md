# Rapport QA final — `address_step` (machine de surface UX)

**Date :** 2026-04-01  
**Périmètre :** Flutter `RegistrationAddressStep` + validation CTA `RegistrationFlowScreen` après refactor pays → recherche → champs ligne.  
**Méthode :** revue de code et traçage des transitions d’état ; les points « visuels » et device réels sont couverts par la checklist manuelle en fin de document.

---

## Executive summary

La machine de surface (`need_country` → `search_only` → `editing`) est **cohérente** avec l’UI : la clé `__reg_address_step_surface__` est dérivée des mêmes prédicats que l’affichage (`_effectiveResidenceIso2ForSearch`, `_searchEnabled`, `_addressFieldsVisible`). Le CTA **Continue** n’exige les champs d’adresse ligne (rue, CP, ville, ligne 2 si requis) que lorsque la surface vaut **`editing`** ; le pays reste toujours requis tant que le composant `address_step` est marqué requis.

Points à surveiller en production :

- **Fenêtre d’un frame (au plus)** après changement de pays : la surface patchée et le vidage des slugs passent en **post-frame** ; le CTA peut rester un instant aligné sur l’ancienne surface / anciennes valeurs avant la mise à jour du `_formData`.
- **Valeur pays non ISO2** mais chaîne non vide : l’UI est en `need_country`, mais la validation CTA ne distingue pas « ISO2 parseable » et « non vide » — risque théorique si une valeur hors contrat arrive dans `_formData`.
- La branche **réhydratation** dans `didUpdateWidget` appelle `_syncSurface()` de façon **synchrone** : acceptable dans le flow réel (parent déjà monté), à garder en tête si un test harness reconstruit le parent de façon agressive.

Globalement, la logique est **robuste** pour le parcours nominal Revolut-like ; les risques résiduels sont **mineurs** et surtout liés au timing du patch et aux données hors contrat.

---

## State machine validation

### Définition (implémentation)

| Surface | Condition dans `_syncSurface()` | Recherche UI | Champs ligne UI |
|--------|----------------------------------|--------------|-----------------|
| `need_country` | `_effectiveResidenceIso2ForSearch == null` | Non | Non |
| `search_only` | ISO2 valide + `search_enabled` + `!_addressFieldsVisible` | Oui | Non |
| `editing` | ISO2 valide + (`!search_enabled` **ou** `_addressFieldsVisible`) | Oui si `search_enabled` | Oui |

Référence : `registration_address_step.dart` (`_syncSurface`, `_computeInitialAddressFieldsVisible`, `_showSearchSection`, `_buildAddressFields`).

### Scénarios fonctionnels (validation par code)

| Scénario | Résultat attendu | Statut |
|----------|------------------|--------|
| Arrivée sans pays | `need_country`, pas de `TextField` recherche, pas d’`AppTextInput` ligne | OK |
| Choix d’un pays ISO2 autorisé | `search_only` si recherche activée ; sinon `editing` + champs ligne tout de suite | OK |
| Recherche active | Autocomplete uniquement si `_canRunPlacesAutocomplete` (pays valide) | OK |
| Sélection d’une suggestion | `_addressFieldsVisible = true`, préremplissage, sources `google_places` / hybride à l’édition | OK |
| « Je n’ai pas trouvé mon adresse » | `_revealManualAddressFields` : lignes + métadonnées vidées, `editing`, override manuel | OK |
| Changement de pays (ISO différent) | `_resetForCountryChange` : overlay fermé, debounce annulé, recherche vidée, `setState` immédiat sur visibilité ; post-frame : `_syncSurface`, clear lignes, `_patchSources`, `_syncSurface` | OK |
| Réhydratation `formData` (lignes déjà remplies, même ISO) | `didUpdateWidget` : si `_computeInitialAddressFieldsVisible()` et champs encore masqués → `setState` + `_syncSurface` | OK |
| `search_enabled: false` | Init / reset pays : `_addressFieldsVisible` true dès pays valide ; surface `editing` | OK |

### Changement de pays — flicker / glitch

- **UI** : le `setState` dans `_resetForCountryChange` met à jour **immédiatement** `_addressFieldsVisible` (masquage des champs en mode recherche) et nettoie l’overlay / la recherche locale. Les **contrôleurs** et le **`formData` parent** sont alignés **au frame suivant** via `_clearAddressLinesOnly` dans un `addPostFrameCallback`.
- **Effet utilisateur** : pas de « flash » prolongé des champs : ils disparaissent dès le premier frame après changement d’ISO. Une **courte incohérence** peut exister entre texte encore présent dans les contrôleurs et widgets déjà retirés de l’arbre (un frame) ; les contrôleurs sont vidés juste après.
- **Recommandation manuelle** : enchaîner rapidement pays A → B → A sur device et vérifier l’absence de scintillement ou de double overlay.

---

## CTA validation

Fichier : `registration_flow_screen.dart`, getter `_allRequiredFilled`, branche `address_step`.

Ordre de décision :

1. Slug pays (bindings) : doit être **non null** et **non vide** (string trim).
2. Si `surface != kRegAddressSurfaceEditing` → **ne pas** exiger rue, CP, ville, ligne 2 (on `continue` vers le composant suivant dans la boucle).
3. Si `surface == kRegAddressSurfaceEditing` → exiger tous les slugs d’adresse (sauf pays déjà OK, sauf ligne 2 si optionnelle).

Cela correspond à l’objectif « le CTA ne dépend des champs ligne **que** lorsqu’ils sont affichés / que la surface est `editing` ».

### Cas limites

| Cas | Comportement |
|-----|----------------|
| `__reg_address_step_surface__` absent (premier frame avant `postFrameCallback` d’`initState`) | Traitée comme non-`editing` → pas d’exigence sur les lignes tant que le pays n’est pas rempli ; si pays déjà en session, une **fenêtre courte** peut laisser le CTA actif sans lignes (acceptable si l’utilisateur ne clique pas instantanément). |
| Surface `editing` + lignes encore non vidées après changement de pays (même frame) | Théoriquement le CTA peut encore voir d’anciennes valeurs **un instant** ; le post-frame les vide et rescinde la surface. |
| Pays non ISO2 mais string non vide | Surface côté widget : `need_country`. CTA : pays « rempli » + surface souvent pas `editing` → lignes non requises ; **alignement métier** à confirmer si le backend exige strictement un ISO2 à cette étape. |

---

## Rehydratation / back navigation

- **Controllers + `formData`** : les contrôleurs sont détenus par l’écran parent ; une réentrée sur l’écran avec `formData` prérempli et même `comp.id` déclenche `didUpdateWidget`. Si au moins une des clés `address_line_1` / `postal_code` / `city` est non vide dans `formData`, `_computeInitialAddressFieldsVisible()` est vraie et la branche de révélation remonte `_addressFieldsVisible` et repatche la surface en `editing` si applicable.
- **Changement d’écran puis retour** : tant que `_formData` conserve les slugs et que l’ISO pays est inchangé, les champs réapparaissent avec les valeurs des contrôleurs synchronisées par les `onFieldChanged` historiques.
- **Changement de pays depuis une session restaurée** : même chemin que le scénario « changement de pays » (reset + post-frame clear).

À valider manuellement : retour arrière système / stack puis avant : pas de double overlay, pas de fuite de `OverlayEntry` (le code appelle `_removeSuggestionsOverlay` sur reset et dispose).

---

## Remaining UX risks

1. **Désalignement CTA / surface pendant ≤ 1 frame** après changement de pays (voir section CTA).
2. **Pays affiché « rempli » mais non ISO2** (libellé libre) : divergence possible entre perception utilisateur (« j’ai choisi un pays ») et état `need_country` + CTA.
3. **`didUpdateWidget` (même ISO)** avec `_syncSurface()` synchrone sur révélation : faible risque en prod ; si un jour un parent déclenche des rebuilds imbriqués inhabituels, surveiller les assertions Flutter (pattern déjà atténué pour le reset pays en post-frame).
4. **Rate limit / erreur API** : inchangés ; pas de régression surface identifiée, mais le CTA peut rester activé en `search_only` alors que l’utilisateur « bloqué » côté recherche doit passer par le mode manuel — comportement voulu.

---

## Manual QA checklist

Cocher sur **device** (iOS + Android si possible), au moins une locale FR et une EN.

### Surface & parcours

- [ ] **Sans pays** : titre + pays + texte d’aide ; pas de barre de recherche ; pas de champs rue/CP/ville ; CTA désactivé ou logique équivalente si pays requis ailleurs.
- [ ] **Choix pays valide** : barre de recherche apparaît ; pas de champs ligne tant qu’aucune suggestion / pas de manuel ; CTA possible **sans** rue/CP/ville.
- [ ] **Recherche** : suggestions / loading / vide / erreur dans l’overlay ; filtre pays cohérent avec la résidence.
- [ ] **Suggestion choisie** : champs ligne visibles, préremplis, éditables ; CTA exige les champs requis.
- [ ] **Mode manuel** : lien / première ligne overlay ; champs vides ; sources manuelles ; CTA suit les règles `editing`.
- [ ] **Changement de pays** (après saisie ou suggestion) : overlay fermé, recherche vidée, champs masqués puis données effacées ; pas de flicker gênant ; pas de suggestion « fantôme ».
- [ ] **Réhydratation** : rouvrir l’étape avec données session / `formData` déjà rempli → champs visibles si données ligne présentes ; surface `editing`.
- [ ] **`search_enabled: false`** : après pays, champs ligne directement visibles ; pas de recherche ; surface `editing`.

### CTA

- [ ] En `search_only` / `need_country` : pas d’obligation de remplir rue/CP/ville (sauf si d’autres composants de l’écran les exigent).
- [ ] En `editing` : obligation alignée sur les champs affichés (y compris ligne 2 si non optionnelle).

### Régression

- [ ] `metadata_slug` jamais visible dans l’UI.
- [ ] Soumission / payload inchangé côté slugs et sources (`google_places`, `manual`, `hybrid`) attendus par le backend.

---

## Références code

- Widget : `mobile/lib/features/registration/widgets/registration_address_step.dart` (`_syncSurface`, `_resetForCountryChange`, `didUpdateWidget`, `_buildCountrySection`, `_buildSearchSection`, `_buildAddressFields`).
- CTA : `mobile/lib/features/registration/screens/registration_flow_screen.dart` (`_allRequiredFilled`, branche `address_step`).
- Tests widget : `mobile/test/registration/registration_address_step_test.dart`.
