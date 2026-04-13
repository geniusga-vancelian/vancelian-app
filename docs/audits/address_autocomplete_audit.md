# Audit : Smart Address Input (Google Places) — alignement avec l’existant Vancelian / Arquantix

**Date (contexte)** : avril 2026  
**Périmètre** : `services/arquantix` (API FastAPI + app Flutter registration). Aucun code produit dans le cadre de cet audit.

---

## Executive summary

L’onboarding **adresse / résidence** repose aujourd’hui sur le **Registration Flow Engine** : écrans configurés en base, composants dynamiques (`text_input`, `country_picker`, etc.), soumission via **`POST /api/registration/sessions/{id}/submit`**, persistance dans **`registration_session_data`** (JSONB + colonne **`source`**) puis projection vers **`persons.profile_json["collected"]`** à la complétion. Il n’existe **pas** d’intégration Google Places ni d’endpoint proxy d’autocomplétion.

Pour une expérience type Revolut **sans casser** la gouvernance ni le mapping profil, l’intégration la plus cohérente est : **(1)** proxy FastAPI dédié (clé Google serveur uniquement) ; **(2)** nouveau **`component_type`** côté moteur (ex. `address_autocomplete`) avec props listant les `binding_slug` existants (`address_line_1`, `postal_code`, `city`, `country_of_residence`, etc.) ; **(3)** widget Flutter dans **`RegistrationFlowRenderer`** réutilisant **`AppTextInput`**, **`AppCountryPicker`**, **`AppPrimaryButton`**, état **`StatefulWidget`** comme le flux actuel (pas de Riverpod dans le `pubspec` actuel).

**Risques principaux** : extension des types de composants (governance + admin + Flutter doivent rester alignés) ; traçabilité Google vs saisie manuelle (`source` / métadonnées) ; pays résidence déjà validé par **`jurisdiction_policy_submit`** — l’adresse Google ne doit pas contourner cette règle.

---

## Current onboarding flow

### Vue d’ensemble

1. **Flutter** : [`RegistrationFlowScreen`](services/arquantix/mobile/lib/features/registration/screens/registration_flow_screen.dart) charge le flux (start session → GET screen → rendu des composants).
2. **Backend runtime** : [`api/services/registration/runtime_router.py`](services/arquantix/api/services/registration/runtime_router.py) — préfixe **`/api/registration`** (flows actifs, sessions, submit, next/prev, interactions SMS, complete).
3. **Moteur** : [`RegistrationSessionService`](services/arquantix/api/services/registration/service.py) — validation des champs requis, règles de visibilité, politiques juridictionnelles au submit, avancement d’écran/étape, **projection** vers `Person`.

### Types d’écrans côté client

- Formulaires dynamiques (`screen_type` form) via [`RegistrationFlowRenderer`](services/arquantix/mobile/lib/features/registration/widgets/registration_flow_renderer.dart).
- Écrans **interaction** (ex. SMS OTP) via panneaux dédiés + API `interaction/*`.
- Écrans **permission_prompt** (Face ID / notifications) avec layout DS dédié dans `registration_flow_screen.dart`.

### Entrée dans le flux (mobile)

- Écran de test / lancement : [`registration_test_launcher_screen.dart`](services/arquantix/mobile/lib/features/registration/screens/registration_test_launcher_screen.dart) (résolution juridiction, navigation vers `RegistrationFlowScreen`).

### Seeds / exemples d’étape « résidence »

- [`api/alembic/versions/085_seed_registration_flows.py`](services/arquantix/api/alembic/versions/085_seed_registration_flows.py) : step `residence` avec `country_of_residence` (`country_picker`), `city`, `address_line_1`, `postal_code`, `nationality`, etc.
- [`api/alembic/versions/087_seed_eu_vertical_slice.py`](services/arquantix/api/alembic/versions/087_seed_eu_vertical_slice.py) : variante EU (même logique : champs texte + pickers).

---

## Current address data flow

### 1. Saisie et soumission

- L’utilisateur remplit les composants ; les valeurs vivent dans **`_formData`** (Map) dans `RegistrationFlowScreen`, synchronisées avec des **`TextEditingController`** par slug.
- **Submit** : [`RegistrationApi.submitScreen`](services/arquantix/mobile/lib/features/registration/data/registration_api.dart) → `POST /api/registration/sessions/{id}/submit` avec `answers: { slug: value, ... }`.

### 2. Persistance session

- Table **`registration_session_data`** ([`database.RegistrationSessionData`](services/arquantix/api/database.py)) :
  - `field_slug` (texte)
  - `value_json` (JSONB)
  - **`source`** (texte, défaut `user_input`)

Chaque slug métier (ex. `address_line_1`) = une ligne (contrainte d’unicité `(session_id, field_slug)`).

### 3. Validation transverse au submit

- [`validate_jurisdiction_policies_on_submit`](services/arquantix/api/services/registration/jurisdiction_policy_submit.py) : selon **`policy_scope`** résolu (composant / field definition), contrôle notamment :
  - **téléphone** (normalisation + allowlist)
  - **nationalité** (pays autorisé)
  - **résidence** : si `scope == "residence"` et slug présent dans `answers`, vérif **`is_residence_country_allowed`** pour le pays ISO2 saisi.

Les champs **ville / rue / code postal** ne passent pas par ce bloc « residence » au sens `policy_scope` ; la **conformité pays résidence** repose sur le **`country_picker`** avec `policy_scope: "residence"` dans les seeds.

### 4. Projection profil (fin de parcours)

- [`_project_to_person`](services/arquantix/api/services/registration/service.py) : copie chaque entrée `RegistrationSessionData` vers :
  - **`profile_json["collected"][slug]`** par défaut ;
  - **`profile_json["compliance"][slug]`** si [`session_slug_to_compliance`](services/arquantix/api/services/registration/interaction_helpers.py) retourne vrai (ex. slugs `*_verified`, `phone_verified`, etc.) — **pas** les champs d’adresse postale classiques.

`Person.profile_json` est initialisé avec `collected`, `computed`, `compliance` (structure déjà prévue pour séparer données collectées / compliance).

### 5. Moteur « onboarding » séparé (post-person)

- [`api/services/onboarding/routes.py`](services/arquantix/api/services/onboarding/routes.py) : `/api/persons/{person_id}/onboarding/next-step` et `submit-step` — **distinct** du registration flow runtime ; utile à connaître pour ne pas confondre les deux pipelines.

---

## Relevant frontend files

| Fichier | Rôle |
|---------|------|
| [`mobile/lib/features/registration/screens/registration_flow_screen.dart`](services/arquantix/mobile/lib/features/registration/screens/registration_flow_screen.dart) | Orchestration flux : chargement session, `_formData`, submit/next/prev, erreurs globales, CTA bas, cas permission / interaction / formulaire. |
| [`mobile/lib/features/registration/widgets/registration_flow_renderer.dart`](services/arquantix/mobile/lib/features/registration/widgets/registration_flow_renderer.dart) | Mapping `component_type` → DS : `AppTextInput`, `AppPhoneInput`, `AppCountryPicker`, `AppSelect`, `AppCheckbox`, etc. |
| [`mobile/lib/features/registration/data/registration_api.dart`](services/arquantix/mobile/lib/features/registration/data/registration_api.dart) | Client HTTP `http` vers `/api/registration/...`. |
| [`mobile/lib/features/registration/data/registration_models.dart`](services/arquantix/mobile/lib/features/registration/data/registration_models.dart) | `RegistrationScreen`, `RegistrationComponent`, `RegistrationSessionState`. |
| [`mobile/lib/design_system/components/app_text_input.dart`](services/arquantix/mobile/lib/design_system/components/app_text_input.dart) (et voisins) | Champs alignés design system. |
| [`mobile/lib/features/registration/screens/registration_test_launcher_screen.dart`](services/arquantix/mobile/lib/features/registration/screens/registration_test_launcher_screen.dart) | Lancement tests / démo flux. |

**Gestion d’état** : **`StatefulWidget`** + `setState` sur `RegistrationFlowScreen` ; pas de **Riverpod** dans [`mobile/pubspec.yaml`](services/arquantix/mobile/pubspec.yaml) (dépendance `http` déjà présente).

**États UX réutilisables** : `_loading`, `_submitting`, `_errorMessage`, `_fieldErrors`, overlay `CircularProgressIndicator`, `AppPrimaryButton` pour CTA — modèle à calquer pour appels autocomplete (loading local au widget ou au champ).

---

## Relevant backend files

| Fichier / module | Rôle |
|------------------|------|
| [`api/services/registration/runtime_router.py`](services/arquantix/api/services/registration/runtime_router.py) | Contrat API registration runtime. |
| [`api/services/registration/service.py`](services/arquantix/api/services/registration/service.py) | Cœur session : submit, validation required, projection, complete. |
| [`api/services/registration/governance.py`](services/arquantix/api/services/registration/governance.py) | `INPUT_COMPONENT_TYPES`, `CONTENT_COMPONENT_TYPES`, health publish, validation famille composant. |
| [`api/services/registration/admin_router.py`](services/arquantix/api/services/registration/admin_router.py) | CRUD flows / steps / screens / components (admin). |
| [`api/services/registration/jurisdiction_policy_submit.py`](services/arquantix/api/services/registration/jurisdiction_policy_submit.py) | Politiques pays téléphone / résidence / nationalité au submit. |
| [`api/services/registration/execution_events.py`](services/arquantix/api/services/registration/execution_events.py) | Taxonomie événements d’exécution registration (audit append-only). |
| [`api/services/registration/policy_scope.py`](services/arquantix/api/services/registration/policy_scope.py) | Résolution `policy_scope` pour les composants. |
| [`api/database.py`](services/arquantix/api/database.py) | `RegistrationSession`, `RegistrationSessionData`, `Person`, `FieldDefinition`, etc. |
| [`api/main.py`](services/arquantix/api/main.py) | Montage des routers (registration, persons, field-definitions, jurisdiction-configs, aml-risk, …). |
| [`api/services/field_definitions/routes.py`](services/arquantix/api/services/field_definitions/routes.py) | `GET /api/field-definitions` (catalogue). |
| [`api/services/persons/routes.py`](services/arquantix/api/services/persons/routes.py) | API identité / person (hors registration runtime). |
| [`api/services/onboarding/routes.py`](services/arquantix/api/services/onboarding/routes.py) | Onboarding steps par `person_id` (moteur séparé). |
| [`api/services/jurisdiction_configs/routes.py`](services/arquantix/api/services/jurisdiction_configs/routes.py) | Configs juridiction (schémas Pydantic dédiés). |
| [`api/services/aml_risk/routes.py`](services/arquantix/api/services/aml_risk/routes.py) | Risque AML sur personne. |
| [`api/data/field_definitions_master.csv`](services/arquantix/api/data/field_definitions_master.csv) | Master list des slugs métier (catégorie `address`, etc.). |

**Google Places** : aucune occurrence pertinente dans l’API Arquantix au moment de l’audit.

---

## Existing schemas and persistence

### Registration (données de session)

- **Modèle** : `RegistrationSessionData` — `field_slug`, `value_json`, `source`.
- **Contrat submit** : dictionnaire clé/valeur arbitraire pour les slugs liés aux composants visibles ; types réels dans JSONB (souvent string pour texte).

### Person (profil long terme)

- **`persons.profile_json`** : JSONB avec au minimum les clés **`collected`**, **`computed`**, **`compliance`** utilisées par la projection registration.
- **`persons.kyc_status`**, **`persons.jurisdiction`** : colonnes dédiées.

### Field definitions

- Table **`field_definitions`** : `slug`, `field_type`, `category`, `component_type_default`, `required_default`, **`policy_scope`**, `options_json`.
- Alignement catalogue / gouvernance testé par la suite de tests registration (ex. field catalog alignment).

### DTOs / schémas

- Registration runtime : modèles Pydantic dans `runtime_router.py` (`StartSessionRequest`, `SubmitScreenRequest`, …).
- Person / onboarding / jurisdiction : `schemas.py`, `schemas_jurisdiction.py`, `schemas_aml_risk.py` selon route.

### Audit

- **`registration_execution_events`** + helpers `safe_log_registration_event` (traçabilité navigation, validation, téléphone, etc.).
- **`audit_events`** liés aux personnes (autre couche, à ne pas confondre avec les événements registration).

---

## Compliance / KYC implications

1. **Google ≠ preuve légale** : les valeurs restent des **données déclaratives** jusqu’à parcours KYC documentaire / fournisseur. Le produit doit continuer à autoriser **édition manuelle** et conserver une **traçabilité** (origine saisie).
2. **`RegistrationSessionData.source`** : colonne prête à distinguer `user_input` vs une future valeur du type `google_places` (ou métadonnées dans `value_json` / slug dédié).
3. **Projection `compliance`** : réservée aux slugs correspondant à [`session_slug_to_compliance`](services/arquantix/api/services/registration/interaction_helpers.py) ; les slugs d’adresse postale vont dans **`collected`** — cohérent avec « pas encore vérifié KYC ».
4. **Sumsub / KYC provider** : référencé dans la documentation interne comme **phase ultérieure** ; pas d’intégration Sumsub live identifiée comme consommant automatiquement `address_line_1` dans ce périmètre audit. Risque futur : **re-synchronisation** adresse fournisseur vs `profile_json["collected"]` (à documenter lors du branchement KYC).
5. **Pays résidence** : déjà soumis à **allowlist** juridictionnelle ; toute auto-fill Google doit **réaligner** le `country_picker` sur un ISO2 accepté ou afficher erreur / correction utilisateur.
6. **AML** : [`aml_risk`](services/arquantix/api/services/aml_risk/routes.py) opère au niveau personne ; l’adresse structurée pourrait alimenter des scores futurs — hors scope actuel mais le schéma `profile_json` le permet.

---

## Recommended integration strategy

1. **Backend proxy** (nouveau module ou router dédié, monté dans `main.py`) :
   - `GET .../autocomplete?q=...` et `GET .../details?place_id=...`
   - Clé API **uniquement** côté serveur (env / secret manager).
   - **Rate limiting** (IP et/ou `session_id` obligatoire pour limiter le scraping).
   - Réponse normalisée (rue, CP, ville, pays ISO2, lat/lng, `formatted_address`, flags type `partial_match`).

2. **Moteur registration — nouveau composant** `address_autocomplete` :
   - Ajout à `INPUT_COMPONENT_TYPES` / `FLUTTER_SUPPORTED_TYPES` dans [`governance.py`](services/arquantix/api/services/registration/governance.py).
   - Props : mapping explicite vers slugs existants du catalogue (`address_line_1`, `postal_code`, `city`, `country_of_residence`) + option **métadonnées** (slug JSON type `address_lookup_metadata` à ajouter au master CSV + DB).
   - Admin : étendre [`web/.../registration/flows/.../edit/page.tsx`](services/arquantix/web/src/app/admin/registration/flows/[id]/edit/page.tsx) pour créer/éditer ce type (comme pour les autres widgets).

3. **Flutter** :
   - Brancher un widget dans `RegistrationFlowRenderer` qui : debounce sur la search bar, appelle le proxy, affiche liste, au tap appelle details, **remplit** controllers + `onFieldChanged` pour chaque slug.
   - Bouton **« My address is not listed »** : masque suggestions, laisse saisie manuelle (champs déjà éditables).
   - Réutiliser **AppTextInput** / **AppCountryPicker** pour les champs affichés (cohérence Revolut-like + DS Vancelian).

4. **Données KYC-ready** :
   - Conserver les **slugs plats** pour compatibilité submit/projection.
   - Ajouter un **objet JSON** (slug dédié) pour `place_id`, `raw_input`, `confidence` / `partial_match`, `manual_override`, timestamps si besoin — **sans** marquer `verified: true` côté compliance sans pipeline KYC.

---

## Open questions / assumptions

| Question | Hypothèse de travail |
|----------|----------------------|
| API Google : Places (New) vs legacy ? | À trancher avant implémentation (facturation, champs, quotas). |
| Autocomplete sans session ? | Exposer uniquement avec **`session_id`** valide réduit l’abus ; à valider produit (UX premier écran). |
| Floor / unit | PRD Revolut : champ manuel séparé — soit `text_input` additionnel dans le même écran, soit second slug dans les props du composant. |
| i18n labels | Les libellés « Search address » / fallback passent par `props` / `label_i18n` comme les autres composants si le flux i18n admin est étendu. |
| Riverpod | Non requis pour v1 ; le flux actuel est **StatefulWidget**. |

---

## Implementation plan

Phases suggérées (ordre logique, sans ordre de grandeur temps) :

1. **Audit légal / ops** : conformité Google Maps Platform ToS, conservation logs, DPA.
2. **Backend** : client HTTP Google, parseur `address_components`, endpoints proxy, rate limit, tests mockés (`pytest`).
3. **Données** : migration / seed `field_definitions` pour slug métadonnées adresse si retenu.
4. **Governance + admin API + UI admin** : type `address_autocomplete`, health checks, éditeur de flux.
5. **Flutter** : renderer + polish UX (debounce, erreurs, loading, accessibilité).
6. **E2E** : parcours résidence avec sélection Google + override manuel + submit + `complete_session` → vérifier `profile_json["collected"]` et `registration_session_data.source`.
7. **Documentation** : runbook clés API, feature flag, note « Google n’est pas source légale ».

### Tests existants à étendre ou à utiliser comme modèle

Sous [`services/arquantix/api/tests/`](services/arquantix/api/tests/) : nombreux `test_registration_*.py` (governance, projection layering, jurisdiction policies, flow, interaction SMS, etc.). Prévoir **`test_registration_address_autocomplete.py`** (proxy mock) + tests governance pour le nouveau `component_type`.

---

## Références doc interne (contexte historique)

- [`services/arquantix/docs/HISTORY_SMART_REGISTRATION.md`](services/arquantix/docs/HISTORY_SMART_REGISTRATION.md) — historique moteur registration / vision KYC fournisseurs.
- [`services/arquantix/EU_REGISTRATION_VERTICAL_SLICE.md`](services/arquantix/EU_REGISTRATION_VERTICAL_SLICE.md) — slice EU et mentions Sumsub phase suivante.

---

*Fin du rapport d’audit.*
