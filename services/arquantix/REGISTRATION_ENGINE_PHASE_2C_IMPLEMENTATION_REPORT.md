# Registration Engine — Phase 2C Implementation Report

**Date**: 2026-03-27
**Base**: Phase 2A + 2B + EU Vertical Slice
**Input**: `REGISTRATION_ENGINE_PHASE_2C_READINESS_AUDIT.md`

---

## Executive Summary

Phase 2C livre **4 axes** sur le Registration Engine sans casser le moteur runtime existant :

1. **3 bugs critiques corrigés** (projection JSONB, UAE nationality, admin stats)
2. **Field Definitions Engine** minimal avec binding formel et catalog API
3. **Flutter real hookup** — 4 widgets DS + renderer dynamique + écran complet
4. **Admin Builder usable** — PATCH/DELETE flows + page Flow Editor 3 panneaux
5. **Validations backend** — email, phone, date, select, multi_select, checkbox

### Chiffres

| Métrique | Valeur |
|----------|--------|
| Fichiers créés | 10 |
| Fichiers modifiés | 5 |
| Nouveaux widgets Flutter | 4 |
| Endpoints ajoutés | 4 |
| Tests ajoutés | 27 |
| Migration Alembic | 1 (088) |

---

## 1. Critical Fixes Applied

### P0.1 — Projection JSONB (flag_modified)

**Problème** : `persons.profile_json["collected"]` restait vide après `complete_session` car SQLAlchemy ne détectait pas la mutation du JSONB.

**Fix** : Ajout de `flag_modified(person, "profile_json")` dans `_project_to_person()`.

```python
# service.py:458
from sqlalchemy.orm.attributes import flag_modified

person.profile_json = profile
flag_modified(person, "profile_json")  # ← 1 ligne ajoutée
db.flush()
```

**Vérifié** : projection testée avec commit + requête dans une nouvelle session DB. Les 9 champs du flow EU_VS sont correctement persistés dans `profile_json["collected"]`.

### P0.2 — UAE nationality

**Problème** : `nationality` dans le flow UAE était seedé comme `select` avec `options: []`.

**Fix** : 
- Donnée en DB corrigée via `UPDATE` direct
- Seed `085` corrigé pour les futurs replays (déjà fait en conversation précédente)
- Harmonisation avec EU : `nationality` utilise `country_picker` dans tous les flows

### P0.3 — Admin Preview Stats

**Résultat** : Faux positif. L'audit cherchait la clé `stats` alors que l'endpoint utilise `statistics`. Les stats (total_steps, total_screens, total_components, blocking_steps) sont correctement calculées dans `admin_router.py:292-313`.

---

## 2. Field Definitions Engine (Minimal)

### Migration 088 — `088_field_definitions_engine.py`

Colonnes ajoutées à `field_definitions` :
- `ui_label` TEXT — label UI exploitable par le builder
- `component_type_default` TEXT — type de composant par défaut
- `required_default` BOOLEAN — required par défaut
- `options_json` JSONB — options par défaut (pour select/multi_select)

Colonne ajoutée à `registration_screen_components` :
- `field_definition_id` UUID FK nullable → `field_definitions(id)`

**Backfill intelligent** :
- `ui_label` ← `field_name_en`
- `component_type_default` ← type de composant le plus fréquent pour chaque slug
- `field_definition_id` ← liaison automatique via normalisation kebab↔snake

### Field slug normalization helpers

Fichier : `services/registration/field_helpers.py`

```python
normalize_to_snake("first-name")     # → "first_name"
normalize_to_kebab("first_name")     # → "first-name"
are_field_slugs_equivalent("first-name", "first_name")  # → True
```

### Field catalog endpoint

`GET /api/admin/registration/field-definitions/catalog`

Retourne les 89 field definitions actives avec : slug, slug_snake, label, field_type, category, component_type_default, required_default, options.

---

## 3. Flutter Real Hookup

### 4 nouveaux widgets DS

| Widget | Fichier | Description |
|--------|---------|-------------|
| `AppSelect` | `app_select.dart` | Dropdown avec bottom sheet modale |
| `AppCountryPicker` | `app_country_picker.dart` | Picker pays ISO 3166-1 (~195 pays) avec recherche |
| `AppDatePicker` | `app_date_picker.dart` | Champ date avec picker natif Material (dd/MM/yyyy) |
| `AppMultiSelect` | `app_multi_select.dart` | Multi-select avec chips et bottom sheet |

Tous suivent les patterns DS existants : card blanche, border-radius 16px, typographie Inter, couleurs `AppColors`.

### RegistrationFlowRenderer

Fichier : `lib/features/registration/widgets/registration_flow_renderer.dart`

Widget stateless qui mappe `component_type` → widget DS :

| component_type | Widget DS |
|----------------|-----------|
| `text_input` | `AppTextInput` |
| `phone_input` | `AppTextInput` (keyboardType: phone) |
| `select` | `AppSelect` |
| `country_picker` | `AppCountryPicker` |
| `date_picker` | `AppDatePicker` |
| `checkbox` | `AppCheckbox` |
| `multi_select` | `AppMultiSelect` |
| `section_title` | `AppSectionTitle` |
| `legal_content` | Rich text block |

### RegistrationFlowScreen

Fichier : `lib/features/registration/screens/registration_flow_screen.dart`

Écran complet consommant l'API runtime :

1. `POST /sessions/start` → démarre une session
2. Affiche les composants via `RegistrationFlowRenderer`
3. Boutons Previous / Next / Submit
4. Gestion erreurs 422 (validation) et 409 (blocking)
5. Barre de progression basée sur `progress_percent`
6. Complete sur dernier écran

Base URL configurable (`http://10.0.2.2:8000` pour Android emulator).

---

## 4. Admin Builder Usable

### Endpoints ajoutés

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `PATCH` | `/api/admin/registration/flows/{id}` | Update flow (name, entrypoint_type) |
| `DELETE` | `/api/admin/registration/flows/{id}` | Delete flow (interdit si active, 409) |
| `GET` | `/api/admin/registration/field-definitions/catalog` | Catalog des field definitions |

### Flow Editor page

Route : `/admin/registration/flows/[id]/edit`

Layout 3 panneaux :

| Panneau | Contenu |
|---------|---------|
| **Steps** (col-span-3) | Liste, ajout, édition inline, delete, reorder ▲/▼ |
| **Screens** (col-span-5) | Pour le step sélectionné : liste, CRUD, layout_type |
| **Components** (col-span-4) | Pour le screen sélectionné : type, key, slug, label, required, placeholder, options JSON |

Accessible depuis la page de liste des flows via le bouton "Edit".

---

## 5. Validation Rules Added

Fichier : `services/registration/validators.py`

| Type | Validation | Erreur |
|------|------------|--------|
| `text_input` (email) | Regex email | 422 "Invalid email format" |
| `phone_input` | Regex phone (6-20 chars) | 422 "Invalid phone format" |
| `date_picker` | ISO `YYYY-MM-DD` ou `dd/MM/yyyy` | 422 "Invalid date format" |
| `select` | Valeur dans options si définies | 422 "Invalid option" |
| `multi_select` | Subset d'options si définies | 422 "Invalid options" |
| `checkbox` | Doit être boolean | 422 "must be boolean" |

Intégré dans `submit_screen()` après sauvegarde, avant navigation.

---

## 6. Tests Added

Fichier : `tests/test_registration_phase2c.py` — **27 tests**

| Classe | Tests | Couverture |
|--------|-------|------------|
| `TestProjectionFix` | 3 | JSONB persist, données préservées, couche service |
| `TestUAENationalityFix` | 2 | country_picker pour UAE |
| `TestFieldSlugHelpers` | 4 | Normalisation snake/kebab/equivalence |
| `TestFieldDefinitionsCatalog` | 2 | Endpoint catalog + structure |
| `TestBackendValidation` | 6 | Email, phone, date, checkbox invalides → 422 |
| `TestAdminFlowCRUD` | 5 | PATCH, DELETE actif→409, DELETE draft→204 |
| `TestFlutterContractReadiness` | 5 | Types supportés, binding slugs |

---

## 7. Backward Compatibility Notes

| Composant | Impact | Détail |
|-----------|--------|--------|
| Runtime API | ✅ Aucun | Endpoints inchangés, réponses enrichies |
| Admin API | ✅ Aucun | Seuls ajouts (PATCH, DELETE, catalog) |
| Flows seedés | ✅ Aucun | EU, UAE, EU_VS restent navigables |
| `binding_slug` | ✅ Aucun | `field_definition_id` est nullable, slug reste primary |
| `field_definitions` | ✅ Aucun | Colonnes ajoutées nullable, pas de breaking |
| Validation | ⚠️ Léger | Les données aberrantes (email invalide, etc.) sont maintenant rejetées en 422. Les données correctes passent comme avant. |

---

## 8. Files Created / Modified

### Fichiers créés

| Fichier | Rôle |
|---------|------|
| `api/alembic/versions/088_field_definitions_engine.py` | Migration |
| `api/services/registration/field_helpers.py` | Normalisation slugs |
| `api/services/registration/validators.py` | Validations format |
| `api/tests/test_registration_phase2c.py` | 27 tests |
| `mobile/lib/design_system/components/app_select.dart` | Widget DS |
| `mobile/lib/design_system/components/app_country_picker.dart` | Widget DS |
| `mobile/lib/design_system/components/app_date_picker.dart` | Widget DS |
| `mobile/lib/design_system/components/app_multi_select.dart` | Widget DS |
| `mobile/lib/features/registration/widgets/registration_flow_renderer.dart` | Renderer |
| `mobile/lib/features/registration/screens/registration_flow_screen.dart` | Écran |
| `web/src/app/admin/registration/flows/[id]/edit/page.tsx` | Admin Editor |

### Fichiers modifiés

| Fichier | Changement |
|---------|------------|
| `api/services/registration/service.py` | `flag_modified` + validation integration |
| `api/services/registration/admin_router.py` | PATCH/DELETE flows + catalog endpoint |
| `api/database.py` | `FieldDefinition` enrichi + `field_definition_id` FK |
| `mobile/lib/design_system/components/components.dart` | Exports |
| `web/src/app/admin/registration/page.tsx` | Bouton "Edit" |

---

## 9. Remaining Gaps / Next Steps

### Phase 2D — Risk Scoring

- Brancher `risk_screening` step sur un scoring engine
- Calculer un score basé sur les réponses collectées
- Stocker dans `profile_json["computed"]["risk_score"]`

### Sumsub Integration

- Ajouter un step KYC provider dans le flow
- Intégrer l'API Sumsub pour la vérification d'identité
- Mettre à jour `kyc_status` via callback webhook

### Admin Builder améliorations

- Drag & drop pour reorder steps/screens/components
- Visual rules builder (au lieu de raw JSON)
- Flow clone / versioning UI
- Preview conditionnel (tester les visibility rules)

### Validation avancée

- Validation custom par field_definition (regex, min/max, etc.)
- Validation inter-champs (ex: date_of_birth > 18 ans)
- Validation asynchrone (ex: vérification email unique)
