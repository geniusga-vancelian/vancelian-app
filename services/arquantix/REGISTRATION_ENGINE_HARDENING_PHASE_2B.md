# Registration Engine Hardening — Phase 2B

## Executive Summary

Phase 2B renforce le Registration Flow Engine livré en Phase 2A sur **5 axes critiques** :

1. **Data layering** — projection dans `profile_json["collected"]` au lieu de flat
2. **Flow version locking** — sessions figées sur la version de flow au démarrage
3. **Session step state tracking** — suivi explicite de l'état de chaque step
4. **Navigation hardening** — contrôle strict de `next`/`prev`, validation des champs requis
5. **Blocking vs non-blocking** — distinction explicite entre steps obligatoires et informatifs

Aucun breaking change sur les endpoints existants. Le contrat API est enrichi (champs additionnels) mais reste backward-compatible.

---

## Data Layering Changes

### Avant

```
persons.profile_json = {
  "first_name": "Gael",
  "last_name": "Itier"
}
```

### Après

```
persons.profile_json = {
  "collected": {"first_name": "Gael", "last_name": "Itier"},
  "computed": {},
  "compliance": {}
}
```

### Règles

- Toutes les réponses de registration sont projetées dans `profile_json["collected"]`
- Les namespaces `computed` et `compliance` sont créés mais non modifiés par le registration engine
- Les données legacy existantes à plat sont préservées (pas de migration destructive)

### Helper de lecture

```python
from services.registration.service import get_person_collected_value

value = get_person_collected_value(person, "first_name")
```

Ce helper lit d'abord `collected[slug]`, puis fallback sur `profile_json[slug]` pour la compatibilité legacy.

---

## Flow Version Locking

### Colonne ajoutée

`registration_sessions.flow_version INTEGER NOT NULL DEFAULT 1`

### Comportement

- Au `start_session`, `flow_version` est copié depuis `flow.version`
- Toute la session navigue ensuite sur le `flow_id` figé (qui est déjà lié à la session)
- Si une v2 du flow est publiée, les sessions v1 continuent sur v1

### Invariant

**Une session commencée sur v1 DOIT continuer sur v1**, même si v2 est publiée ensuite.

### Backfill

La migration 086 backfill `flow_version` depuis le flow lié pour les sessions existantes.

---

## Session Step State Tracking

### Nouvelle table

```sql
registration_session_steps (
  id UUID PRIMARY KEY,
  session_id UUID FK → registration_sessions,
  step_id UUID FK → registration_flow_steps,
  status TEXT NOT NULL DEFAULT 'not_started',
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  skipped_at TIMESTAMPTZ,
  last_screen_id UUID FK → registration_step_screens,
  metadata_json JSONB,
  UNIQUE(session_id, step_id)
)
```

### Statuts possibles

| Status | Déclencheur |
|---|---|
| `not_started` | Valeur par défaut |
| `in_progress` | Le step est le step courant de la session |
| `completed` | Le step a été validé et la session a avancé au step suivant |
| `skipped` | Step sauté par règle de visibilité |
| `blocked` | Validation bloquante échouée |

### API enrichie

Chaque réponse de screen inclut désormais :
- `current_step_status` — statut du step courant
- `step_states` — liste des états de tous les steps de la session

---

## Navigation Hardening

### Next strictement contrôlé

Lors d'un changement de step via `next_screen()` :

1. Si le step courant est `is_blocking=True` :
   - Vérification que tous les champs `required` visibles ont une valeur dans le contexte
   - Si non → `StepBlockedError` (HTTP 409)
2. Le step courant est marqué `completed` dans `session_steps`
3. Le step suivant est marqué `in_progress`

### Submit avec validation

`submit_screen()` valide les champs requis visibles de l'écran courant :
- Champs avec `props_json.required = true` et `binding_slug` défini
- Valeurs `None`, `""` ou `[]` considérées comme manquantes
- Si manquant → `ValidationError` (HTTP 422)

### Prev permissif mais borné

`prev_screen()` ne permet que la navigation dans les bornes du flow figé. Impossible de passer avant le premier écran.

### Invariant

**Le backend décide toujours du next screen.** Le frontend ne choisit jamais librement un screen cible.

---

## Blocking vs Non-Blocking

### Colonne ajoutée

`registration_flow_steps.is_blocking BOOLEAN NOT NULL DEFAULT true`

### Sémantique

| `is_blocking` | Comportement |
|---|---|
| `true` | Impossible d'avancer au step suivant tant que les champs requis ne sont pas remplis |
| `false` | Le flow peut continuer même si ce step est incomplet |

### Seeds mis à jour

Le step `consent` est marqué `is_blocking=false` dans les flows seedés. Tous les autres steps sont `is_blocking=true` par défaut.

### Exposition API

- `is_blocking` est retourné dans `current_step` et dans `serialize_flow`
- Admin API : `StepCreate` et `StepUpdate` acceptent `is_blocking`

---

## Migrations

### 086_registration_engine_hardening.py

| Opération | Table | Détail |
|---|---|---|
| ADD COLUMN | `registration_flow_steps` | `is_blocking BOOLEAN NOT NULL DEFAULT true` |
| ADD COLUMN | `registration_sessions` | `flow_version INTEGER NOT NULL DEFAULT 1` |
| CREATE TABLE | `registration_session_steps` | Step state tracking per session |
| BACKFILL | `registration_sessions.flow_version` | Depuis le flow lié |
| UPDATE | `registration_flow_steps` | `is_blocking=false` pour step_key='consent' |

### Downgrade

Suppression table + colonnes dans l'ordre inverse.

---

## Tests Added

| Fichier | Tests | Couverture |
|---|---|---|
| `test_registration_projection_layering.py` | 7 | Projection layered, helper lecture, backward compat, namespace isolation |
| `test_registration_flow_version_locking.py` | 4 | Pin version, survie après republish, audit payload |
| `test_registration_session_step_states.py` | 5 | in_progress au start, completed après advance, DB persistence |
| `test_registration_navigation_guards.py` | 8 | Blocking gate, validation required, prev bounds, backend decides next |
| `test_registration_blocking_steps.py` | 7 | Blocking bloque, non-blocking passe, mixed flow E2E |

Tests existants mis à jour :
- `test_registration_flow.py` — projection assertions adaptées pour `collected` namespace, enrichissement `flow_version` et `step_states` vérifié

---

## Backward Compatibility Notes

### Ce qui ne change PAS

- URLs des endpoints identiques
- Contrat principal des réponses préservé
- Flows EU/UAE seedés toujours navigables

### Ce qui est enrichi (non-breaking)

| Champ | Description |
|---|---|
| `flow_version` | Ajouté aux réponses screen |
| `current_step_status` | Statut du step courant |
| `step_states` | Liste des états de tous les steps |
| `current_step.is_blocking` | Indicateur blocking dans le step courant |
| `current_step.status` | Statut du step courant dans les données step |

### Validation ajoutée

- `submit_screen` peut maintenant retourner HTTP 422 si des champs requis sont manquants
- `next_screen` peut retourner HTTP 409 si un step blocking n'est pas complété
- Le client Flutter doit gérer ces cas (afficher un message d'erreur)

---

## Remaining Risks

| Risque | Mitigation |
|---|---|
| Données legacy à plat dans profile_json | Helper `get_person_collected_value` gère le fallback |
| Sessions existantes sans step_states | Les step_states sont créés à la demande au runtime |
| Clients Flutter non mis à jour | Les nouveaux champs sont additionnels, pas bloquants côté API |
| Validation trop stricte sur submit | Seuls les composants avec `props_json.required=true` sont validés |

---

## Fichiers modifiés/créés

### Modèles & Migration
- `api/database.py` — 3 changements : `is_blocking`, `flow_version`, `RegistrationSessionStep`
- `api/alembic/versions/086_registration_engine_hardening.py` — Migration DDL + backfill

### Service Layer
- `api/services/registration/service.py` — Réécriture complète avec les 5 axes de hardening

### API Layer
- `api/services/registration/runtime_router.py` — Import `StepBlockedError`, `ValidationError` + error handlers
- `api/services/registration/admin_router.py` — `is_blocking` dans schemas et serialisation

### Tests (5 nouveaux fichiers)
- `api/tests/test_registration_projection_layering.py`
- `api/tests/test_registration_flow_version_locking.py`
- `api/tests/test_registration_session_step_states.py`
- `api/tests/test_registration_navigation_guards.py`
- `api/tests/test_registration_blocking_steps.py`

### Tests mis à jour
- `api/tests/test_registration_flow.py` — Assertions adaptées pour layered projection
