# Flutter Registration Real Runtime Hookup — Implementation Report

## Executive Summary

Flutter est désormais branché sur le Registration Flow Engine runtime réel. Aucun écran n'est codé en dur par juridiction — tout est piloté dynamiquement par l'API backend. Le flow EU (Personal Info → Residency → Consent) est navigable de bout en bout dans Flutter en utilisant les endpoints runtime existants.

### Résultats clés
- **4 fichiers créés/réécrits**, **3 fichiers de tests** avec **39 tests** tous verts
- **10 component_types** supportés dans le renderer
- **Bugs critiques corrigés** : TextEditingController recréé à chaque build (perte d'input), mauvaises clés JSON dans _applyScreenData
- **Debug panel** intégré en mode développement

---

## API Layer

### Fichier : `mobile/lib/features/registration/data/registration_api.dart`

Client HTTP dédié avec gestion structurée des erreurs.

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `getActiveFlow(jurisdiction)` | `GET /api/registration/flows/active` | Récupère le flow actif |
| `startSession(...)` | `POST /api/registration/sessions/start` | Démarre une session |
| `getCurrentScreen(sessionId)` | `GET /api/registration/sessions/{id}/screen` | Écran courant |
| `submitScreen(sessionId, answers)` | `POST /sessions/{id}/submit` | Soumet les réponses |
| `nextScreen(sessionId)` | `POST /sessions/{id}/next` | Avance |
| `prevScreen(sessionId)` | `POST /sessions/{id}/prev` | Recule |
| `completeSession(sessionId)` | `POST /sessions/{id}/complete` | Termine la session |

### Gestion d'erreurs
- `ApiResult<T>` encapsule `data`, `statusCode`, `errorMessage`, `fieldErrors`
- **422** : Parse les erreurs de validation backend (format `"slug: message"`) et Pydantic
- **409** : Step bloqué — message affiché dans un banner
- **401/403** : Erreur d'authentification
- **0** : Erreur réseau (timeout, connection refused)

---

## Models

### Fichier : `mobile/lib/features/registration/data/registration_models.dart`

5 modèles Dart avec parsing null-safe aligné sur le contrat API :

| Modèle | Clés JSON parsées |
|--------|-------------------|
| `RegistrationComponent` | `id`, `component_type`, `component_key`, `position`, `props`, `binding_slug`, `field_definition_id`, `validation` |
| `RegistrationScreen` | `id`, `screen_key`, `title`, `subtitle`, `layout_type`, `components` |
| `RegistrationStep` | `id`, `step_key`, `title`, `description`, `is_blocking`, `status` |
| `RegistrationStepState` | `step_id`, `status`, `started_at`, `completed_at` |
| `RegistrationSessionState` | `session_id`, `status`, `flow_version`, `progress_percent`, `is_last_screen`, `current_step`, `screen`, `collected_data`, `step_states` |

Propriétés dérivées :
- `isFirstScreen` : `progress_percent == 0`
- `isCompleted` : `status == 'completed'`
- `RegistrationComponent.label`, `.isRequired`, `.placeholder`, `.options`

---

## Renderer Mapping

### Fichier : `mobile/lib/features/registration/widgets/registration_flow_renderer.dart`

| component_type | Widget DS | Notes |
|---------------|-----------|-------|
| `text_input` | `AppTextInput` | keyboard type déduit de `props.input_type` |
| `phone_input` | `AppTextInput` | keyboard = `TextInputType.phone` |
| `checkbox` | `AppCheckbox` | binding bool |
| `select` | `AppSelect` | bottom sheet avec options |
| `country_picker` | `AppCountryPicker` | 193 pays ISO 3166-1 + recherche |
| `date_picker` | `AppDatePicker` | Material DatePicker, stocke ISO 8601 |
| `multi_select` | `AppMultiSelect` | bottom sheet multi-check + chips |
| `section_title` | `Text` styled | Inter Bold 20px |
| `legal_content` | Styled container | Fond gris, texte secondaire |
| `info_box` | Info card | Fond bleu clair + icône info |

### Bug critique corrigé
L'ancien renderer créait un `TextEditingController` dans `_controllerFor()` à chaque `build()`. Résultat : chaque `setState()` détruisait l'input utilisateur. 

**Fix** : Les controllers sont maintenant gérés dans `RegistrationFlowScreen._controllers` (un `Map<String, TextEditingController>`) et passés au renderer via le paramètre `controllers`. Ils sont synchronisés à chaque changement d'écran via `_syncControllers()` et disposés proprement dans `dispose()`.

---

## Runtime Screen

### Fichier : `mobile/lib/features/registration/screens/registration_flow_screen.dart`

### Lifecycle
1. `initState()` → `_startFlow()` → `POST /sessions/start` → reçoit premier écran
2. Chaque écran est rendu dynamiquement par `RegistrationFlowRenderer`
3. "Continue" → `POST /submit` avec `_formData` → backend auto-avance
4. Dernier écran → "Complete" → `POST /submit` puis `POST /complete`
5. Écran de succès affiché, `Navigator.pop(true)`

### Features
- **Barre de progression** : `LinearProgressIndicator` piloté par `progress_percent`
- **Step indicators** : barres horizontales colorées (vert = completed, indigo = current, gris = pending)
- **Titre et sous-titre** : rendus depuis `screen.title` / `screen.subtitle`
- **Préremplissage** : `collected_data` de l'API alimente `_formData` pour les champs déjà soumis
- **Erreurs field-level** : 422 parse les slugs et affiche sous chaque champ concerné
- **Erreur globale** : banner rouge pour 409 ou erreurs non-field
- **Back** : flèche ← appelle `POST /prev`, close × si premier écran
- **Loading state** : spinner pendant submit, boutons désactivés

### Bug critique corrigé
L'ancien `_applyScreenData` lisait `data['current_screen']` (inexistant) au lieu de `data['screen']`, et `data['step_title']` au lieu de `data['current_step']['title']`. Également, `data['prefill']` au lieu de `data['collected_data']`. Toutes les clés sont maintenant alignées sur le contrat API réel.

---

## Field Binding

Chaque composant est relié à son `binding_slug` via `_formData`:

```
Map<String, dynamic> _formData = {
  'first_name': 'Gael',
  'country_of_residence': 'FR',
  'terms_and_conditions': true,
};
```

- Au chargement : prérempli depuis `collected_data` retourné par l'API
- Au submit : envoyé tel quel via `{'answers': _formData}`
- Totalement générique — aucun slug hardcodé

---

## Error Handling

| Code | Comportement Flutter |
|------|---------------------|
| 200/201 | Parse et applique le nouvel état session |
| 422 | Parse `detail` → erreurs rattachées aux champs via `fieldErrors[slug]` |
| 409 | Message global : "Veuillez compléter les informations requises..." |
| 401/403 | Message d'erreur standard |
| 0 | "Connection error: ..." |
| 500 | "Server error (500)" |

---

## EU E2E Validation

Le flow EU vertical slice est consommable de bout en bout :

| Step | Screen | Composants | Types |
|------|--------|-----------|-------|
| Personal Info | Your Information | first_name, last_name, email, phone_number | text_input (×3), phone_input |
| Residency | Residency | country_of_residence, nationality, date_of_birth | country_picker (×2), date_picker |
| Consent (non-blocking) | Legal | legal_content, terms_and_conditions, privacy_policy | legal_content, checkbox (×2) |

---

## Debug Panel

En mode `kDebugMode`, un panneau debug collapsible s'affiche en bas du scroll :

- `session_id` (tronqué)
- `status`, `flow_version`, `progress`
- `step` courant et `step_status`
- `screen` courant, `is_last`
- `step_states` : liste avec statut de chaque step
- `formData` : état local du formulaire
- `collected_data` : toutes les données collectées côté backend

Le panneau utilise JetBrains Mono, fond dark, accents warning pour les labels.

---

## Tests Added

| Fichier | Tests | Couverture |
|---------|-------|------------|
| `test/registration/registration_models_test.dart` | 12 | Parsing Component, Screen, Step, StepState, SessionState, null-safety, derived props |
| `test/registration/registration_api_test.dart` | 8 | ApiResult states (200, 201, 422, 409, 401, 403, 0), construction |
| `test/registration/registration_renderer_test.dart` | 19 | Mapping 10 types → widgets, erreurs field, onFieldChanged, unknown type, options parsing |
| **Total** | **39** | **Tous verts** |

---

## Files Created/Modified

### Created
| Fichier | Rôle |
|---------|------|
| `mobile/lib/features/registration/data/registration_api.dart` | Client HTTP runtime |
| `mobile/lib/features/registration/data/registration_models.dart` | Modèles Dart typés |
| `mobile/test/registration/registration_models_test.dart` | Tests modèles |
| `mobile/test/registration/registration_api_test.dart` | Tests API client |
| `mobile/test/registration/registration_renderer_test.dart` | Tests renderer |

### Rewritten (corrections critiques)
| Fichier | Changements |
|---------|-------------|
| `mobile/lib/features/registration/widgets/registration_flow_renderer.dart` | Controllers externalisés, modèles typés, info_box ajouté |
| `mobile/lib/features/registration/screens/registration_flow_screen.dart` | Clés JSON corrigées, API layer, debug panel, step indicators, préremplissage, completion screen |

---

## Backward Compatibility

- ✅ Admin preview non touché
- ✅ Runtime backend inchangé
- ✅ Composants DS existants réutilisés tels quels
- ✅ Flow EU seedé inchangé
- ✅ Aucun écran hardcodé par juridiction

---

## Remaining Gaps

| Gap | Priorité | Description |
|-----|----------|-------------|
| Token auth | P1 | Pas de header Authorization — à ajouter quand le flow auth est prêt |
| Internationalisation | P2 | Labels en dur côté backend — i18n à implémenter dans le flow engine |
| Offline resilience | P3 | Pas de cache local — retry uniquement |
| File upload | P2 | Composant `file_upload` non supporté dans le renderer |
| Animations | P3 | Transitions entre écrans basiques |
| Multi-juridiction | P1 | Le point d'entrée est paramétré, mais le routing Flutter n'expose pas encore le choix de juridiction |
| Visibility rules | P2 | Les règles de visibilité sont évaluées côté backend (composants non visibles exclus de la réponse), mais pas encore supportées côté Flutter pour du dynamisme local |
