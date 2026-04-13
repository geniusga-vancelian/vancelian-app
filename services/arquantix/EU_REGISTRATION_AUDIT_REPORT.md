# Audit — Parcours registration / onboarding EU (Arquantix)

**Date du rapport :** 2026-04-03  
**Périmètre :** code réel du dépôt `services/arquantix` (mobile Flutter, API FastAPI, admin Next.js, migrations Alembic).  
**Méthode :** lecture du code et des seeds/migrations ; aucune assertion non vérifiable.

---

## 1. Executive summary

### Ce qui existe déjà

- **Moteur de registration déclaratif** côté API : flows versionnés par juridiction (`registration_flows`, `registration_flow_steps`, `registration_step_screens`, `registration_screen_components`), sessions (`registration_sessions`, `registration_session_data`, `registration_session_steps`), événements d’exécution (`registration_execution_events`), projection vers `persons.profile_json` à la complétion.
- **Runtime Flutter** : un écran générique `RegistrationFlowScreen` consomme l’API (start → submit/next/prev → complete), rend les composants via `RegistrationFlowRenderer`, gère téléphone (validation locale + modale), écrans `interaction` SMS OTP, adresses (`address_step` / `address_autocomplete` + proxy Places côté API).
- **Seed EU historique (migration 085)** : juridiction `EU` avec un flow **5 étapes** — `basic_info`, `residence`, `professional`, `risk_screening`, `consent` (champs détaillés en section 3).
- **Politiques juridictionnelles** : validation téléphone (mobile strict, libphonenumber), listes pays résidence/nationalité via `jurisdiction_country_policies` et `policy_scope` à la soumission (`jurisdiction_policy_submit.py`).
- **Admin** : liste des sessions registration, preview de flows ; **Customer 360** avec agrégat `registration_progress` (jalons téléphone, identité, session registration, KYC, lien `pe_client`, statut actif).
- **Moteur d’onboarding par étapes** séparé (`onboarding_engine.py` + routes `/api/persons/{person_id}/onboarding/...`) basé sur `jurisdiction_configs` — **auth non câblée** (TODO explicite dans le code).

### Niveau de maturité actuel

- **Technique (engine + mobile + persistence)** : **élevé** pour un parcours piloté par configuration, observable (events, admin sessions), avec projection structurée vers `Person`.
- **Produit « parcours EU complet jusqu’au compte investisseur »** : **partiel** — la registration crée/ enrichit surtout une **Person** et des données collectées ; le lien **utilisateur d’auth**, **client PE**, **KYC documentaire / fournisseur**, et la **reprise de session** ne sont pas traités comme un tout cohérent dans le flux mobile analysé.
- **Documentation interne** : le fichier `EU_REGISTRATION_VERTICAL_SLICE.md` décrit un flow **EU_VS** à 3 écrans ; la migration **101** supprime les juridictions `EU_VS` et `TEST_AUDIT` — ce document est **historique / à réconcilier** avec l’état DB actuel (juridiction **`EU`** + seed 085).

### Plus gros gaps (synthèse)

1. **Pas de chaînage explicite registration → compte applicatif** dans `complete_session` (projection `Person` uniquement ; pas de création utilisateur auth dans ce service).
2. **Pas de reprise de session** côté Flutter (chaque lancement fait `startSession` ; pas de persistance locale de `session_id`).
3. **Deux modèles de « progression »** : registration runtime (`progress_percent`, `step_states`) vs onboarding engine (`jurisdiction_configs`) vs agrégat admin (`registration_progress`) — risque de divergence produit.
4. **Onboarding API** (`/api/persons/.../onboarding/...`) sans auth réelle — non utilisable en production telle quelle.
5. **KYC** : champ `persons.kyc_status` existe ; pas de preuve dans ce périmètre d’un flux IDV branché sur la registration EU.

---

## 2. Parcours utilisateur actuel

### Ordre réel côté mobile (logique générique)

Fichier pivot : `mobile/lib/features/registration/screens/registration_flow_screen.dart`.

1. **`_startFlow`** → `POST /api/registration/sessions/start` avec `{ "jurisdiction": "<code>" }` (optionnellement `flow_id`, `person_id`, `client_id` côté client API — voir `registration_api.dart`).
2. Réponse appliquée → premier écran (`_applySessionData`).
3. **Soumission** :
   - Écran formulaire : `_submitWithPhoneConfirmIfNeeded` → `_submitAndAdvance` → `POST .../submit` avec `{ "answers": <formData> }`.
   - Écran **permission** : `submitScreen` avec le slug de décision booléen.
   - Écran **interaction** SMS : panneau OTP puis `refresh` + `next` (pas de CTA formulaire du bas).
4. **Navigation** : `next` / `prev` via `POST .../next` et `.../prev`.
5. **Dernier écran** (`is_last_screen`) : après submit réussi (si champs), `completeSession` → `POST .../complete`, puis UI « Registration Complete ».

### Point d’entrée utilisateur dans l’app

- `RegistrationTestLauncherScreen` : lit `GET /api/registration/runtime/current-jurisdiction`, affiche les steps du flow actif, lance `RegistrationFlowScreen` avec le **code juridiction courant** (souvent aligné sur `registration_runtime_settings`, ex. `EU` après migrations).
- Références : `welcome_landing_screen.dart`, `profile_screen.dart` (imports vers le launcher test).

### Ce qui fonctionne déjà (techniquement)

- Rendu dynamique des composants listés dans `_inputComponentTypes` + permission + interaction.
- Validations téléphone côté client + erreurs structurées 422 (codes connus : `invalid_phone_number`, etc.).
- Complétion session et état `_completed` local.

### Ce qui est incomplet (produit)

- **Pas de parcours « onboarding EU » bout-en-bout** garanti par un seul flux métier : la registration engine couvre la collecte ; **login / OTP hors registration**, **création wallet**, **KYC** sont ailleurs ou absents du chemin unique.
- **Reprise** : aucune logique de reprise de `session_id` après kill app (d’après le code du screen).

---

## 3. Cartographie frontend (Flutter)

### Fichiers clés

| Fichier | Rôle |
|--------|------|
| `registration_flow_screen.dart` | Orchestration API, état formulaire, CTA, permission, interaction SMS, écran de fin |
| `registration_flow_renderer.dart` | Mapping `component_type` → widgets DS, adresses composites |
| `registration_api.dart` | Client HTTP runtime + autocomplete/details adresse |
| `registration_form_hydration.dart` | Hydratation depuis `RegistrationSessionState` |
| `registration_models.dart` | Modèles écran / composants |
| `registration_phone_sms_otp_panel.dart` | Flux OTP lié aux écrans `interaction` |
| `registration_test_launcher_screen.dart` | Launcher test + `SetupProgressCard` |
| `registration_phone_format_validation.dart` | Validation locale alignée produit |

### Composants / types gérés (extrait)

- Entrées : `text_input`, `phone_input`, `select`, `country_picker`, `date_picker`, `checkbox`, `multi_select`, `address_autocomplete`, `address_step`.
- Écrans spéciaux : `permission_prompt` (DsPermissionPrompt), `interaction` + `phone_verification_sms`.

### Logique de progression / resume

- **Progression affichée** : `progress_percent` et `step_states` viennent du backend ; le launcher peut afficher une carte de steps via `getActiveFlow`.
- **Resume** : **non implémenté** dans `RegistrationFlowScreen` (pas de stockage local de session, pas de paramètre « reprendre » visible).

### Dette / incohérences notables

- Textes de fin de parcours en **anglais** hardcodés (« Registration Complete ») — incohérent avec une app i18n ailleurs.
- Le launcher est nommé **Test** ; l’entrée produit réelle pour l’EU devra clarifier navigation (welcome vs profil) et branding.
- `EU_REGISTRATION_VERTICAL_SLICE.md` vs DB : **EU_VS supprimé** (migration 101).

---

## 4. Cartographie backend

### Routes registration runtime

Documentées dans `api/services/registration/runtime_router.py` :

- `GET /api/registration/runtime/current-jurisdiction`
- `GET /api/registration/flows/active?jurisdiction=...`
- `POST /api/registration/sessions/start`
- `GET /api/registration/sessions/{id}/screen`
- `POST /api/registration/sessions/{id}/submit`
- `POST .../next`, `POST .../prev`
- `POST .../interaction/prepare`, `.../resend`, `.../interaction/complete`
- `POST .../complete`

Montage : `api/main.py` inclut `registration_runtime_router` et `registration_admin_router`.

### Service principal

`api/services/registration/service.py` — `RegistrationSessionService` :

- `start_session`, `submit_screen` (validation, politiques, avancement),
- navigation `next` / `prev`,
- interactions SMS (liaison challenges 2FA, flags stockés en `registration_session_data`),
- `complete_session` : statut `completed`, `progress_percent = 100`, **`_project_to_person`** vers `persons.profile_json`.

### Schémas / validation

- Soumission : règles par composant + **jurisdiction policies** (`jurisdiction_policy_submit.py`) pour téléphone, résidence, nationalité (y compris composites adresse).
- Téléphone : `phone_validation.py` — mobile only, cohérence pays, allowlists ; signaux « low risk » région documentés en code pour UE/EEA/CH/GB/AE.

### Admin registration

`api/services/registration/admin_router.py` — flows, preview, **liste sessions**, détail session, replay, events (voir `replay.py`).

### Onboarding (distinct)

- `api/services/onboarding/routes.py` : `GET .../onboarding/next-step`, `POST .../submit-step` avec `jurisdiction` + `purpose` en query ; **`actor_id` / auth TODO**.

---

## 5. Data model mapping

### Source of truth actuelle (registration)

| Entité | Rôle |
|--------|------|
| `registration_sessions` | Session en cours ; `person_id`, `flow_id`, `flow_version`, `current_step_id`, `current_screen_id`, `status`, `progress_percent` |
| `registration_session_data` | Réponses par `field_slug` / `value_json` |
| `registration_session_steps` | États par étape du flow |
| `registration_execution_events` | Observabilité / audit d’exécution |

### Projection post-registration

- `complete_session` → `_project_to_person` : écrit dans `persons.profile_json` sous **`collected`** (et slugs « compliance » via `session_slug_to_compliance` → namespace `compliance`).
- Création de `Person` si absente : `kyc_status = not_started`, `profile_json` avec `collected` / `computed` / `compliance`.

### Person / Client

- `Person` : `jurisdiction`, `profile_json`, `client_id` (nullable), `kyc_status`.
- `Client` (portfolio engine / `pe_clients`) : utilisé par **Customer 360** pour savoir si un compte portefeuille existe et est actif — **pas créé dans `complete_session`** (d’après lecture du service).

### Relation auth user

- Aucun lien explicite **User ↔ Person** traité dans les extraits de `complete_session` analysés ; à traiter comme **hors scope ou gap** selon le module d’auth du reste de la plateforme.

### Champs disponibles (exemple EU seed 085)

Le seed **085** pour la juridiction **`EU`** définit notamment (binding slugs) :

- **basic_info** : `first_name`, `last_name`, `email`, `phone_number`, `date_of_birth`
- **residence** : `country_of_residence`, `city`, `address_line_1`, `postal_code`, `nationality`
- **professional** : `employment_status`, `employer_name` (visibilité conditionnelle), `annual_income_range`, `source_of_funds`
- **risk_screening** : `investment_experience`, `known_asset_classes`, `risk_tolerance`
- **consent** : `terms_accepted`, `data_processing_consent`, `marketing_consent`

**Note doc** : `EU_REGISTRATION_VERTICAL_SLICE.md` (3 étapes, juridiction `EU_VS`) ne reflète plus le schéma DB après migration **101**.

### Champs manquants pour une registration EU « sérieuse » (constat relatif, non légal)

- **Preuves d’identité / documents** : table `documents` existe en ORM ; pas branchée au flux registration dans ce périmètre d’audit code.
- **Lien fort auth** : non montré dans la completion registration.
- **Email** : le doc vertical slice signalait l’absence de validation backend dédiée — à vérifier dans `submit_screen` / rules (non exhaustive ici).

---

## 6. Jurisdiction readiness (EU)

### Prêt

- Juridiction **`EU`** seedée (085) avec flow **individual** multi-étapes.
- Politiques pays (migrations 099, 102, etc.) et **`policy_scope`** sur téléphone / résidence / nationalité.
- Validation téléphone **alignée produit** (mobile, pays).

### Partiellement prêt

- **Progression unifiée** : calcul admin `registration_progress` mélange présence de session, complétion, KYC, PE — utile mais **heuristique** (ex. « registration » compte dès qu’une session existe).
- **i18n** : résolution `title_i18n` côté API pour les flows ; rendu Flutter dépend des données envoyées.

### Absent ou à clarifier

- **Un seul référentiel d’étapes** couvrant registration + KYC + compte : aujourd’hui **plusieurs systèmes** (registration engine, `jurisdiction_configs` onboarding, champs Person).
- **EU_VS** : supprimé — les tests/docs qui le mentionnent doivent être **mis à jour**.

---

## 7. Compliance readiness

### Déjà couvert (collecte dans le seed EU 085)

- Identité de base, contact, résidence texte, nationalité, naissance.
- Situation pro, revenus, source of funds (questionnaire simplifié).
- Profil investisseur simplifié (expérience, classes d’actifs, tolérance au risque).
- Consentements terms / données / marketing optionnel.

### Partiel / fragile

- **Vérification d’identité** : pas de flux IDV dans le moteur registration analysé.
- **Adresse** : le seed 085 utilise des `text_input` ; le moteur Flutter supporte des composants adresse plus riches — **cohérence à décider** (flow DB vs UX).
- **Conservation preuve** : cases cochées sans horodatage / version documentaire traçable dans ce rapport (à confirmer dans rules/audit events si besoin).

### Nécessaire pour une registration EU crédible (orientation produit, non conseil juridique)

- Clarifier **quels consentements** et **quels documents** sont requis pour votre modèle (MiCA / CGU / privacy — arbitrage compliance).
- Définir **quand** le KYC IDV intervient par rapport à la registration (séquentiel vs parallèle).

---

## 8. Gaps & blockers (priorisés)

### Backend

1. **Auth sur onboarding** ` /api/persons/.../onboarding/...` — TODO explicite.
2. **Cohérence registration vs onboarding** : deux moteurs, un seul `profile_json`.
3. **Complétion registration** : pas de création **compte** / **pe_client** dans le service analysé.

### Frontend

1. **Pas de resume session**.
2. **Point d’entrée** encore « test launcher » pour le flux complet.
3. **Copy** fin de parcours non localisée.

### Data model

1. **`Person` sans user** : modèle relationnel auth à documenter.
2. **`registration_progress` admin** : bon indicateur mais **pas** une spec fonctionnelle unique (scores et étapes macro).

### UX

1. Charge cognitive : flow 085 = **5 écrans lourds** ; peut être fragmenté différemment (produit).
2. Gestion erreurs réseau / retry au-delà du « Retry » start.

### Admin / support

1. **Customer 360** : affiche progression agrégée + session récente — manque peut‑être le **détail champs collectés** dans l’UI (à confirmer hors liste customers).
2. **Sessions registration** dédiées : page admin existe ; utile pour support.

---

## 9. Recommended target registration flow for EU (proposition pragmatique)

**Principes :** réglementairement sérieux sans « monstre », progressif, aligné sur l’engine existant, préparant l’admin.

### Étapes recommandées (ordre)

1. **Accès & juridiction** — Confirmer EU (déjà le cas via runtime ou paramètre) ; message clair sur entité légale.
2. **Identité & contact** — Nom, email, mobile ; **OTP SMS** sur le mobile (écran `interaction` déjà supporté) avant ou après selon risque produit (recommandation : tôt pour sécuriser le contact).
3. **Résidence & nationalité** — `country_picker` + adresse (privilégier `address_step` / autocomplete pour qualité d’adresse si exigence compliance).
4. **Situation financière light** — Emploi, fourchette de revenus, source of funds (déjà dans le seed ; wording court).
5. **Investisseur** — Expérience + risque (déjà présent ; éviter sur-ingénierie au début).
6. **Consentements** — Terms, traitement des données, marketing optionnel ; tracer version document (backend).
7. **Complete** — Projection `Person` ; **pivot** vers KYC / création compte selon votre stack (hors registration engine pur).

### Données par étape (alignées champs existants 085 + extensions possibles)

- Étape 2 : slugs déjà prévus (`first_name`, `last_name`, `email`, `phone_number`, `date_of_birth`).
- Étape 3 : `country_of_residence`, adresse, `nationality`.
- Étape 4–5 : slugs profession / risk du seed.
- Étape 6 : consentements du seed.

### Validations principales

- Téléphone : **déjà** côté API (policies EU).
- Pays : **déjà** (allowlists).
- Email : **à renforcer** si confirmé comme gap (micro-règle backend).

### Dépendances backend

- Flow actif juridiction `EU` (versionnée).
- `complete_session` + éventuellement **webhook / job** post-projection pour KYC ou création user (nouvelle couche).

### Progress / completion

- **Source de vérité runtime** : `registration_sessions.status` + `progress_percent` + `step_states`.
- **Source de vérité « lifecycle client »** : étendre progressivement `registration_progress` ou un **state machine** métier unique documenté — éviter trois définitions parallèles sans hiérarchie.

---

## 10. Proposed implementation plan

### Phase 1 — Cadrage & cohérence (priorité haute)

- Réconcilier documentation (`EU_REGISTRATION_VERTICAL_SLICE.md`, tests) avec juridiction **`EU`** et migration 101.
- Décider **point d’entrée produit** (remplacer / renommer le launcher test).
- Décider **auth** : quand lier `Person` à un utilisateur (avant / après registration).
- Définir **une** grille de progression affichable admin + mobile (même vocabulaire d’étapes).

### Phase 2 — Parcours EU MVP robuste

- Finaliser flow DB (5 étapes ou découpage différent) avec i18n et legal versionnés.
- Renforcer validations email si requis.
- **Resume** : stratégie `session_id` persisté + endpoint recover (ou nouveau start idempotent avec `person_id`).

### Phase 3 — Compliance & compte

- Brancher **KYC** (fournisseur / documents) après registration.
- Création **pe_client** / activation : orchestration post-`complete`.
- Durcir **onboarding engine** ou le fusionner conceptuellement avec registration (éviter duplication).

---

## 11. Open questions / ambiguïties

1. **Quand** créer l’utilisateur auth — avant la première étape, après OTP, ou à la fin ?
2. **KYC** : obligation avant tout investissement uniquement, ou aussi avant accès lecture ?
3. **Adresse** : niveau de preuve attendu (texte vs autocomplete vs document) pour l’EU ?
4. Faut-il **déprécier** `onboarding_engine` au profit du registration engine, ou les **spécialiser** (registration = collecte, onboarding = post-login produits) ?
5. **Données sensibles** : durée de rétention et base légale — hors code ; à valider compliance.

---

## Annexes

### Fichiers inspectés (les plus importants)

- `mobile/lib/features/registration/screens/registration_flow_screen.dart`
- `mobile/lib/features/registration/data/registration_api.dart`
- `mobile/lib/features/registration/widgets/registration_flow_renderer.dart`
- `mobile/lib/features/registration/screens/registration_test_launcher_screen.dart`
- `api/services/registration/runtime_router.py`
- `api/services/registration/service.py` (complete, projection, progress)
- `api/services/registration/jurisdiction_policy_submit.py`
- `api/services/registration/phone_validation.py`
- `api/services/onboarding/routes.py`
- `api/services/onboarding_engine.py`
- `api/services/customers_admin/registration_progress.py`
- `api/services/customers_admin/service.py`
- `api/database.py` (`Person`, `RegistrationSession`, …)
- `api/alembic/versions/085_seed_registration_flows.py`
- `api/alembic/versions/101_remove_eu_vs_and_test_audit_jurisdictions.py`
- `EU_REGISTRATION_VERTICAL_SLICE.md`
- `web/src/app/admin/registration/sessions/page.tsx`
- `web/src/app/admin/customers/[personId]/page.tsx` (aperçu registration_progress)

### Principaux constats (rappel)

- Moteur registration **riche et configurable** ; seed EU **085** = 5 étapes avec données pro/risk/consent.
- Mobile **générique** et **sans resume**.
- **Onboarding** parallèle **non sécurisé** (auth TODO).
- Doc **EU_VS** **obsolète** vs migrations récentes.

### Micro-fixes évidents (sans implémentation ici)

- Mettre à jour ou archiver `EU_REGISTRATION_VERTICAL_SLICE.md` pour refléter **EU** et la suppression de **EU_VS**.
- Harmoniser les textes de fin de parcours Flutter avec la stratégie i18n du projet.

---

*Fin du rapport.*
