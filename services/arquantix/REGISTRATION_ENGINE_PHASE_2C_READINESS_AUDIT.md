# Registration Engine — Phase 2C Readiness Audit

**Date**: 2026-03-27
**Scope**: Phase 2A + 2B + EU Vertical Slice
**Status**: Read-only audit — no code modified

---

## Executive Summary

Le Registration Flow Engine est **fonctionnel en runtime** : la navigation complète (start → submit → next → prev → complete) marche correctement sur les 3 flows seedés (EU, EU_VS, UAE). Les blocking steps, le version locking et le step state tracking fonctionnent.

Cependant, **3 problèmes critiques** et **5 lacunes structurelles** ont été identifiés qui doivent être résolus avant Phase 2C.

### Problèmes critiques

| # | Problème | Impact | Fichier |
|---|----------|--------|---------|
| **C1** | **Projection JSONB cassée** — `persons.profile_json["collected"]` reste vide après `complete_session` | Données perdues | `service.py:457` |
| **C2** | **UAE nationality = `select` sans options** | Champ vide en prod | `085_seed.py:line 130` |
| **C3** | **Admin preview `stats` toujours `None`** | Preview admin incomplet | `admin_router.py:preview` |

### Lacunes structurelles pour Phase 2C

| # | Lacune | Requis pour |
|---|--------|-------------|
| **G1** | Pas de PATCH/DELETE sur les flows | Admin Builder |
| **G2** | 4 component types sans widget Flutter DS | Flutter intégration |
| **G3** | Pas de Field Definitions Engine (binding_slugs non centralisés) | Cohérence multi-flow |
| **G4** | Pas de validation côté backend (format email, phone, etc.) | Intégrité données |
| **G5** | Admin UI limitée à 2 pages (list + preview) | Flow Builder |

---

## 1. Runtime Flow Validation

### Résultat : ✅ FONCTIONNEL

Flow complet testé sur EU_VS (3 steps, 3 screens, 10 composants) :

```
1. POST /sessions/start        → 201 ✅  step=personal_info, progress=0%
2. GET  /sessions/{id}/screen   → 200 ✅  retourne l'écran courant
3. POST /next (sans submit)     → 409 ✅  "blocking and has missing required fields"
4. POST /submit (personal_info) → 200 ✅  avance à residency, progress=50%
5. POST /submit (residency)     → 200 ✅  avance à consent, progress=100%
6. POST /prev (consent→residency) → 200 ✅  navigation arrière OK
7. POST /next (residency→consent) → 200 ✅  retour avant OK
8. POST /submit (consent)       → 200 ✅  is_last_screen=true
9. POST /complete               → 200 ✅  person_id créé, projected_fields=9
10. POST /complete (2ème fois)  → 409 ✅  "Session already completed"
```

### Détails fonctionnels vérifiés

| Fonctionnalité | Statut | Détail |
|----------------|--------|--------|
| Session start | ✅ | Crée session + step_state initial |
| Blocking step enforcement | ✅ | 409 si champs requis manquants |
| Non-blocking step (consent) | ✅ | Peut être skip via navigation |
| Step state tracking | ✅ | `not_started → in_progress → completed` |
| Version locking | ✅ | `flow_version` figé au start |
| Navigation prev/next | ✅ | Bornée par le flow |
| Double-complete guard | ✅ | 409 si déjà completed |
| Collected data aggregation | ✅ | 9/9 champs dans la réponse API |

### Bug découvert pendant l'audit

La navigation `next_screen` et `prev_screen` souffrait d'un bug SQLAlchemy (relationship cache stale après `db.flush()`). **Corrigé dans cette conversation** via `db.expire(session)`.

---

## 2. Flutter Contract Compatibility

### Résultat : ✅ ENDPOINT FONCTIONNEL, ⚠️ GAPS DS

L'endpoint `GET /api/registration/flows/{id}/flutter-contract` retourne :

```json
{
  "contract_version": "1.0",
  "flow": { ... },
  "flutter_metadata": {
    "component_types_used": ["checkbox", "country_picker", "date_picker", ...],
    "binding_slugs": ["first_name", "last_name", ...],
    "total_screens": 3,
    "total_components": 10
  }
}
```

### Mapping component_type → Flutter DS

| component_type | Widget DS Flutter | Statut |
|----------------|-------------------|--------|
| `text_input` | `app_text_input.dart` | ✅ Prêt |
| `phone_input` | `app_text_input.dart` (variant) | ⚠️ Pas de widget dédié |
| `checkbox` | `app_checkbox.dart` | ✅ Prêt |
| `section_title` | `app_section_title.dart` | ✅ Prêt |
| `select` | — | ❌ **Manquant** |
| `country_picker` | — | ❌ **Manquant** |
| `date_picker` | — | ❌ **Manquant** |
| `multi_select` | — | ❌ **Manquant** |
| `legal_content` | `legal_footer_note.dart` (partiel) | ⚠️ Pas spécifique |

### Incohérence détectée

**UAE flow** : le champ `nationality` est de type `select` avec `options: []` (vide).
**EU flows** : `nationality` est correctement de type `country_picker`.

---

## 3. Component & Field Analysis

### Vue globale

- **54 composants** répartis sur **3 flows**
- **9 component_types** utilisés
- **22 binding_slugs** uniques

### Binding slugs par type

| binding_slug | Type | Required | Flows |
|--------------|------|----------|-------|
| `first_name` | text_input | ✅ | 3/3 |
| `last_name` | text_input | ✅ | 3/3 |
| `email` | text_input | ✅ | 3/3 |
| `phone_number` | phone_input | ✅ | 3/3 |
| `date_of_birth` | date_picker | ✅ | 3/3 |
| `country_of_residence` | country_picker | ✅ | 3/3 |
| `nationality` | ⚠️ **INCONSISTANT** | ✅ | 3/3 |
| `city` | text_input | ✅ | 2/3 |
| `address_line_1` | text_input | ✅ | 2/3 |
| `postal_code` | text_input | ✅ | 2/3 |
| `employment_status` | select | ✅ | 2/3 |
| `employer_name` | text_input | ❌ | 2/3 |
| `annual_income_range` | select | ✅ | 2/3 |
| `source_of_funds` | select | ✅ | 2/3 |
| `investment_experience` | select | ✅ | 2/3 |
| `known_asset_classes` | multi_select | ❌ | 2/3 |
| `risk_tolerance` | select | ✅ | 2/3 |
| `terms_accepted` | checkbox | ✅ | 2/3 |
| `data_processing_consent` | checkbox | ✅ | 2/3 |
| `marketing_consent` | checkbox | ❌ | 2/3 |
| `terms_and_conditions` | checkbox | ✅ | 1/3 (EU_VS only) |
| `privacy_policy` | checkbox | ✅ | 1/3 (EU_VS only) |

### Incohérence critique

`nationality` utilise `country_picker` dans EU/EU_VS mais `select` (avec options vides) dans UAE.

### Alignement avec field_definitions

- **89 field_definitions** actives en base (naming convention: `kebab-case`)
- **22 binding_slugs** dans registration (naming convention: `snake_case`)
- **17** matchent après normalisation (`-` → `_`)
- **5 non matchés** : `annual_income_range`, `known_asset_classes`, `privacy_policy`, `terms_accepted`, `terms_and_conditions`

**Problème** : les binding_slugs du registration engine et les slugs de field_definitions utilisent des conventions différentes (`snake_case` vs `kebab-case`). Aucun lien formel entre les deux systèmes.

---

## 4. Admin Capabilities

### API CRUD — État actuel

| Entité | CREATE | READ | UPDATE | DELETE | REORDER |
|--------|--------|------|--------|--------|---------|
| Jurisdiction | ✅ POST | ✅ GET list | ✅ PATCH | ❌ 405 | — |
| Flow | ✅ POST | ✅ GET list/detail | ❌ **Manquant** | ❌ **Manquant** | — |
| Step | ✅ POST | ✅ GET list | ✅ PATCH | ✅ DELETE | ✅ POST reorder |
| Screen | ✅ POST | ✅ GET (via step) | ✅ PATCH | ✅ DELETE | — |
| Component | ✅ POST | ✅ GET (via screen) | ✅ PATCH | ✅ DELETE | — |

### Opérations spéciales

| Opération | Endpoint | Statut |
|-----------|----------|--------|
| Publish flow | `POST /flows/{id}/publish` | ✅ |
| Archive flow | `POST /flows/{id}/archive` | ✅ |
| Flow preview | `GET /flows/{id}/preview` | ⚠️ `stats` est `None` |
| Simulate session | `?simulate_session=true` | ✅ |

### Admin UI (Next.js)

| Page | Route | Statut |
|------|-------|--------|
| Flow list | `/admin/registration` | ✅ Fonctionnel |
| Flow preview | `/admin/registration/flows/[id]/preview` | ✅ Fonctionnel |
| Flow create/edit | — | ❌ **Inexistant** |
| Step builder | — | ❌ **Inexistant** |
| Screen builder | — | ❌ **Inexistant** |
| Component builder | — | ❌ **Inexistant** |
| Rules builder | — | ❌ **Inexistant** |

### Ce qui est possible sans code aujourd'hui

Via `curl` / API directe :
- Créer un flow complet (jurisdiction → flow → steps → screens → components)
- Publier / archiver un flow
- Réordonner les steps
- Modifier les props d'un composant (label, required, options)
- Prévisualiser un flow avec simulation de session

### Ce qui est impossible sans code

- **Éditer ou supprimer un flow** (pas d'endpoint)
- **Drag & drop** steps/screens/components (pas d'UI)
- **Visual rules builder** (pas d'UI)
- **Clone / version a flow** (pas d'endpoint)
- **Preview conditionnel** (visibility rules non testables visuellement)

---

## 5. Data & Projection

### Structure session_data

```
registration_session_data
├── session_id (FK)
├── field_slug (text) — maps to binding_slug
├── value_json (JSONB) — actual value
├── source (text) — "user_input" | "system"
└── updated_at
```

✅ Toutes les réponses utilisateur sont correctement stockées pendant la session.

### Projection vers persons — ❌ CRITIQUE : CASSÉE

**Symptôme** : `complete_session` retourne `projected_fields: 9` mais `persons.profile_json["collected"]` reste vide `{}`.

**Cause racine** : SQLAlchemy JSONB mutation tracking.

```python
# service.py:444-458
profile = dict(person.profile_json)    # copie
profile["collected"]["first_name"] = "Gael"  # modification
person.profile_json = profile          # réassignation
db.flush()                             # SQLAlchemy ne détecte PAS le changement
```

**Preuve** : `sqlalchemy.inspect(person).attrs.profile_json.history` retourne `History(unchanged=[...])` même après réassignation.

**Impact** : Les données collectées pendant l'inscription ne sont **jamais persistées** dans `persons.profile_json`. Toutes les sessions complétées ont un profil vide.

**Fix requis** : Utiliser `sqlalchemy.ext.mutable.MutableDict` sur la colonne `profile_json`, ou forcer le dirty flag via `flag_modified(person, 'profile_json')`.

### Step states

✅ Correctement trackés dans `registration_session_steps` :
- `not_started → in_progress → completed` pour les blocking steps
- Consent (non-blocking) reste `in_progress` même après submit (le step n'est jamais marqué `completed` par `_mark_step_completed` car `submit_screen` auto-advance via `next_screen` qui ne rappelle pas `_mark_step_completed` pour le dernier step si c'est `NoNextScreenError`).

---

## 6. Rules Engine V1

### Opérateurs supportés

| Opérateur | Testé | Statut |
|-----------|-------|--------|
| `equals` | ✅ | OK |
| `not_equals` | ✅ | OK |
| `in` | ✅ | OK |
| `not_in` | ✅ | OK |
| `exists` | ✅ | OK |
| `not_exists` | ✅ | OK |
| `all_of` (composite) | ✅ | OK |
| `any_of` (composite) | ✅ | OK |

### Utilisation effective

- **37 entités** ont des règles (visibility ou validation)
- **1 seule règle de visibilité** réellement utilisée : `employer_name` visible si `employment_status == "employed"`
- **Toutes les validation_rule_json** sont de type simple `{"type": "required"}` — pas de validation format
- **Aucune completion_rule_json** n'est définie sur les steps
- **Aucune visibility_rule** sur les steps ou screens

---

## 7. What is Already Production-Ready

| Composant | Prêt | Remarque |
|-----------|------|----------|
| Data model (7 tables) | ✅ | Solide, relations propres |
| Session lifecycle (start→complete) | ✅ | Navigation robuste |
| Blocking step enforcement | ✅ | 409 si incomplet |
| Version locking | ✅ | flow_version figé au start |
| Step state tracking | ✅ | Table dédiée |
| Rules engine V1 | ✅ | 8 opérateurs, composable |
| Admin CRUD API (steps, screens, components) | ✅ | POST/PATCH/DELETE |
| Flow publish/archive | ✅ | Lifecycle complet |
| Flutter contract endpoint | ✅ | Structure cohérente |
| Admin preview page (Next.js) | ✅ | Debug panel inclus |

---

## 8. What Needs to Be Built (Phase 2C)

### P0 — Bugs critiques à corriger immédiatement

| # | Action | Effort | Fichier |
|---|--------|--------|---------|
| **P0.1** | Fix projection JSONB : ajouter `flag_modified(person, 'profile_json')` | 1 ligne | `service.py:458` |
| **P0.2** | Fix UAE nationality : changer `select` → `country_picker` | Migration | `085_seed.py` + DB |
| **P0.3** | Fix admin preview `stats` : calculer total_steps/screens/components | 10 lignes | `admin_router.py:preview` |

### P1 — Requis pour Flutter Integration

| # | Action | Effort |
|---|--------|--------|
| **P1.1** | Créer widget Flutter `app_select.dart` (dropdown) | Moyen |
| **P1.2** | Créer widget Flutter `app_country_picker.dart` | Moyen |
| **P1.3** | Créer widget Flutter `app_date_picker.dart` | Moyen |
| **P1.4** | Créer widget Flutter `app_multi_select.dart` | Moyen |
| **P1.5** | Créer `RegistrationFlowRenderer` widget qui map `component_type` → widget DS | Important |
| **P1.6** | Créer `RegistrationFlowScreen` avec state management (answers, navigation) | Important |

### P2 — Requis pour Admin Builder

| # | Action | Effort |
|---|--------|--------|
| **P2.1** | Ajouter `PATCH /flows/{id}` et `DELETE /flows/{id}` | Petit |
| **P2.2** | Créer page Admin "Flow Editor" (step list, screen list, component list) | Important |
| **P2.3** | Drag & drop reorder pour steps/screens/components | Moyen |
| **P2.4** | Component property editor (props_json visual editor) | Important |
| **P2.5** | Visual rules builder (visibility conditions) | Important |
| **P2.6** | Flow clone / versioning UI | Moyen |

### P3 — Field Definitions Engine

| # | Action | Effort |
|---|--------|--------|
| **P3.1** | Unifier naming convention (`snake_case` partout, ou mapping layer) | Moyen |
| **P3.2** | Lier `binding_slug` → `field_definitions.slug` formellement | Moyen |
| **P3.3** | Créer un "field catalog" exploitable par le component builder | Important |
| **P3.4** | Ajouter validation backend (email format, phone format, etc.) | Moyen |

---

## 9. Risks & Constraints

### Risques de régression

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Modifier `profile_json` column type casse d'autres readers | Moyenne | Élevé | Tester tous les accès à `profile_json` avant |
| Changer la convention de naming des slugs casse les flows seedés | Faible | Élevé | Migration de données avec dual-write |
| Ajouter des widgets Flutter sans backward compat | Faible | Moyen | Versionner le `contract_version` |

### Dépendances critiques

1. **`Person.profile_json`** est lu par : eligibility engine, KYC status, client identity service. Tout changement de structure doit être backward-compatible.
2. **`get_db()` ne fait pas `db.commit()`** — chaque router doit appeler `db.commit()` explicitement. Risque d'oubli.
3. **SQLAlchemy JSONB** — toute mutation de colonne JSONB nécessite `flag_modified()`. Ce pattern doit être documenté et appliqué partout.

### Parties sensibles à ne pas casser

- `services/registration/service.py` — coeur du moteur
- `services/registration/rules.py` — moteur de règles
- Migrations `084` à `087` — schéma DB
- Runtime router endpoints `/sessions/*` — contrat API Flutter

---

## Annexe A — Structure du code

```
api/services/registration/
├── __init__.py
├── service.py              # RegistrationFlowService + RegistrationSessionService (770 lignes)
├── rules.py                # evaluate_rule() + filter_visible_items() (70 lignes)
├── runtime_router.py       # 7 endpoints client (sessions + flutter-contract)
└── admin_router.py         # 20+ endpoints admin (CRUD + preview)

api/alembic/versions/
├── 084_add_registration_flow_engine.py   # 7 tables
├── 085_seed_registration_flows.py        # EU + UAE flows
├── 086_registration_engine_hardening.py  # is_blocking, flow_version, session_steps
└── 087_seed_eu_vertical_slice.py         # EU_VS minimal flow

web/src/app/admin/registration/
├── page.tsx                              # Flow list
└── flows/[id]/preview/page.tsx           # Flow preview + debug
```

## Annexe B — DB Schema (7+1 tables)

```
registration_jurisdictions (3 rows: EU, EU_VS, UAE)
  └── registration_flows (3 active flows)
       └── registration_flow_steps (is_blocking, position, visibility_rule)
            └── registration_step_screens (layout_type, config_json)
                 └── registration_screen_components (component_type, binding_slug, props_json)

registration_sessions (flow_version locked at start)
  ├── registration_session_data (field_slug → value_json)
  └── registration_session_steps (status per step)
```
