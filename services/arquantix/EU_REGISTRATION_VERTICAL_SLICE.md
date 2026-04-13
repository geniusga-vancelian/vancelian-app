# EU Registration Vertical Slice

## Flow Structure

```
Jurisdiction: EU_VS (European Union - Vertical Slice)
Flow: "EU Individual Registration v1"
Version: 1 | Status: active | Entrypoint: individual
```

```
Step 1: personal_info   [blocking]    → 1 screen, 4 components
Step 2: residency        [blocking]    → 1 screen, 3 components
Step 3: consent          [non-blocking] → 1 screen, 3 components
                                        ─────────────────────────
                                        3 steps, 3 screens, 10 components
```

---

## Screens

### Screen 1 — Personal Info Form

| Component | Type | Binding | Required |
|---|---|---|---|
| First Name | text_input | first_name | yes |
| Last Name | text_input | last_name | yes |
| Email | text_input | email | yes |
| Phone Number | phone_input | phone_number | yes |

### Screen 2 — Residency Form

| Component | Type | Binding | Required |
|---|---|---|---|
| Country of Residence | country_picker | country_of_residence | yes |
| Nationality | country_picker | nationality | yes |
| Date of Birth | date_picker | date_of_birth | yes |

### Screen 3 — Consent Form

| Component | Type | Binding | Required |
|---|---|---|---|
| Terms Notice | legal_content | — | — |
| Terms and Conditions | checkbox | terms_and_conditions | yes |
| Privacy Policy | checkbox | privacy_policy | yes |

---

## Components

Component types utilisés dans ce vertical slice :

| Type | Count | Description |
|---|---|---|
| text_input | 3 | Champs texte standard |
| phone_input | 1 | Numéro de téléphone |
| country_picker | 2 | Sélecteur de pays |
| date_picker | 1 | Sélecteur de date |
| checkbox | 2 | Cases à cocher |
| legal_content | 1 | Bloc de texte légal (non-bindé) |

---

## API Calls

### Runtime (Flutter / Admin Preview)

| Endpoint | Method | Description |
|---|---|---|
| `/api/registration/flows/active?jurisdiction=EU_VS` | GET | Récupérer le flow actif |
| `/api/registration/sessions/start` | POST | Démarrer une session |
| `/api/registration/sessions/{id}/screen` | GET | Écran courant |
| `/api/registration/sessions/{id}/submit` | POST | Soumettre réponses + avancer |
| `/api/registration/sessions/{id}/next` | POST | Avancer manuellement |
| `/api/registration/sessions/{id}/prev` | POST | Reculer |
| `/api/registration/sessions/{id}/complete` | POST | Compléter et projeter |

### Debug / Validation

| Endpoint | Method | Description |
|---|---|---|
| `/api/registration/flows/{id}/flutter-contract` | GET | Contrat Flutter (types, slugs, stats) |

### Admin

| Endpoint | Method | Description |
|---|---|---|
| `/api/admin/registration/flows/{id}/preview` | GET | Preview complet (flow + stats) |
| `/api/admin/registration/flows/{id}/preview?simulate_session=true` | GET | Preview + simulation first screen |
| `/api/admin/registration/flows` | GET | Liste des flows |
| `/api/admin/registration/jurisdictions` | GET | Liste des juridictions |

---

## Admin Preview

### Page : `/admin/registration/flows/[id]/preview`

Layout 3 colonnes :

| Zone | Contenu |
|---|---|
| **Left (3/12)** | Steps list avec statuts, badges blocking/optional, progress bar |
| **Center (5/12)** | Screen preview avec composants HTML mappés |
| **Right (4/12)** | Debug panel (session_id, status, step_states, collected_data) |

### Component Mapping (admin preview)

| Backend Type | HTML Render |
|---|---|
| text_input | `<input type="text">` |
| phone_input | `<input type="tel">` |
| country_picker | `<select>` avec pays EU mock |
| date_picker | `<input type="date">` |
| checkbox | `<input type="checkbox">` |
| legal_content | Bloc texte amber |
| select | `<select>` avec options |
| section_title | `<h3>` |

### Page liste : `/admin/registration`

Cards avec tous les flows, badges status/jurisdiction, bouton "Preview".

---

## Flutter Compatibility

### Contrat vérifié

L'endpoint `/api/registration/flows/{id}/flutter-contract` retourne :

```json
{
  "contract_version": "1.0",
  "flow": { ... },
  "flutter_metadata": {
    "component_types_used": ["checkbox", "country_picker", "date_picker", ...],
    "binding_slugs": ["first_name", "last_name", "email", ...],
    "total_screens": 3,
    "total_components": 10
  }
}
```

### Types de composants à mapper côté Flutter

| Backend Type | Flutter Widget attendu |
|---|---|
| text_input | AppTextInput |
| phone_input | AppPhoneInput |
| country_picker | AppCountryPicker |
| date_picker | AppDatePicker |
| checkbox | AppCheckbox |
| legal_content | AppLegalContent (texte seul) |

### Binding

Chaque composant avec `binding_slug` doit être bindé à un state local Flutter.
Au submit, le `Map<String, dynamic> answers` est envoyé au backend.

### Invariants Flutter

1. Le backend décide du next screen → Flutter ne fait que render
2. `is_last_screen` indique quand afficher le bouton "Complete"
3. `step_states` permet d'afficher un stepper visuel
4. `flow_version` est figé → pas de changement de structure en cours de session

---

## Tests

### Fichier : `test_registration_eu_vertical_slice.py`

| Classe | Tests | Couverture |
|---|---|---|
| TestEUVerticalSliceFlowCreation | 4 | Structure du flow, composants, blocking/non-blocking |
| TestEUVerticalSliceNavigation | 5 | Start, submit, advance, blocking gate, consent skip |
| TestEUVerticalSliceProjection | 2 | Projection complète, step states après completion |
| TestEUVerticalSliceAPI | 5 | HTTP: start, submit, complete, admin preview, flutter-contract |

**Total : 16 tests**

---

## Known Gaps

| Gap | Impact | Résolution |
|---|---|---|
| Admin preview utilise mock pays (11 pays) | Cosmétique | Charger la liste complète en Phase 2C |
| Pas de validation email côté backend | Faible | Ajouter regex validation dans le rules engine |
| Pas de file upload (document ID) | Attendu | Phase 2E (Sumsub) |
| Pas d'i18n sur les labels | Attendu | Phase 2C (Flutter renderer) |
| Admin preview ne fait pas de rollback propre | Faible | Le simulate_session crée une vraie session — acceptable en dev |
| Pas de rate limiting sur les endpoints | Moyen | Phase 2D |

---

## Fichiers créés / modifiés

### Backend

| Fichier | Action |
|---|---|
| `api/alembic/versions/087_seed_eu_vertical_slice.py` | Nouveau — Seed EU 3 steps |
| `api/services/registration/admin_router.py` | Modifié — Preview endpoint |
| `api/services/registration/runtime_router.py` | Modifié — Flutter contract endpoint |
| `api/tests/test_registration_eu_vertical_slice.py` | Nouveau — 16 tests E2E |

### Frontend

| Fichier | Action |
|---|---|
| `web/src/app/admin/registration/page.tsx` | Nouveau — Liste des flows |
| `web/src/app/admin/registration/flows/[id]/preview/page.tsx` | Nouveau — Flow preview + debug |
