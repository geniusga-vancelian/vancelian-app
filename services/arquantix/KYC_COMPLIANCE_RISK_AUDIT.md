# KYC / Compliance / Risk Scoring — Audit Complet

## Executive Summary

Le système KYC/Compliance/Risk Scoring de Vancelian repose sur une architecture **configurable par juridiction** avec un moteur d'onboarding par étapes, un moteur de scoring AML à règles, et un journal d'audit centré sur les personnes. L'architecture de base est **fonctionnelle et extensible**, mais présente des lacunes significatives en matière de **sécurité des endpoints** (authentification absente sur la majorité des routes), de **complétude du moteur** (écart entre le schéma de configuration et les fonctionnalités réellement implémentées), et de **traçabilité des changements de politique** (pas d'audit sur les modifications de configs). Le scoring AML est traçable et explicable, mais certains éléments sont **codés en dur** dans le moteur.

---

## Current Architecture

### Vue d'ensemble

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                    │
│                                                          │
│  /api/persons              → CRUD Person + set fields    │
│  /api/persons/.../onboarding → moteur KYC par étapes     │
│  /api/persons/.../risk     → scoring AML                 │
│  /api/jurisdiction-configs → CRUD configs KYC & AML      │
│  /api/field-definitions    → catalogue de champs         │
│  /api/ai/jurisdiction-configs → IA compose/validate      │
└────────────┬────────────────────────────┬────────────────┘
             │                            │
     ┌───────▼────────┐          ┌────────▼───────────┐
     │ Onboarding     │          │ AML Risk Engine     │
     │ Engine         │          │                     │
     │ (step/block    │          │ (rules, weights,    │
     │  visibility,   │          │  tiers, flags)      │
     │  field sets)   │          │                     │
     └───────┬────────┘          └────────┬────────────┘
             │                            │
     ┌───────▼────────────────────────────▼────────────┐
     │               PostgreSQL                         │
     │                                                  │
     │  field_definitions    persons (profile_json)     │
     │  jurisdiction_configs audit_events               │
     │  documents            pe_clients (kyc_status)    │
     └──────────────────────────────────────────────────┘
```

### Fichiers centraux

| Composant | Fichier |
|-----------|---------|
| Modèles SQLAlchemy | `api/database.py` |
| Schémas KYC | `api/schemas_jurisdiction.py` |
| Schémas AML | `api/schemas_aml_risk.py` |
| Moteur onboarding | `api/services/onboarding_engine.py` |
| Moteur AML | `api/services/aml_risk_engine.py` |
| Gestion champs | `api/services/person_fields.py` |
| Routes configs | `api/services/jurisdiction_configs/routes.py` |
| Service configs | `api/services/jurisdiction_configs/service.py` |
| Validateurs configs | `api/services/jurisdiction_configs/validators.py` |
| Routes personnes | `api/services/persons/routes.py` |
| Routes onboarding | `api/services/onboarding/routes.py` |
| Routes AML | `api/services/aml_risk/routes.py` |
| IA admin | `api/services/ai_jurisdiction_configs/` |

---

## Data Model Analysis

### 1. `field_definitions`

**Rôle** : Catalogue des champs KYC collectables (slugs normalisés).

| Colonne | Type | Contraintes |
|---------|------|-------------|
| `id` | UUID | PK |
| `slug` | Text | UNIQUE, NOT NULL |
| `field_name_en` | Text | NOT NULL |
| `field_type` | Text | NOT NULL |
| `category` | Text | nullable |
| `is_active` | Boolean | default `true` |
| `created_at` | DateTime(tz) | server default now() |
| `updated_at` | DateTime(tz) | server default now() |

**Index** : `ix_field_definitions_category` (btree).

**Problèmes** :
- Pas de contrainte `CHECK` sur `field_type` (valeurs autorisées : string, date, datetime, boolean, number, enum, array, json, file — validées uniquement côté applicatif)
- Pour `field_type = 'enum'` : pas de liste de valeurs autorisées en base (aucune table `enum_values` ou `field_options`)
- Pas d'API CRUD — gestion par seed CSV uniquement (`scripts/seed_field_definitions.py` + `data/field_definitions_master.csv`)
- Trigger `updated_at` supprimé en migration `009` — repose sur l'ORM

### 2. `persons`

**Rôle** : Entité personne KYC. Toutes les données collectées sont stockées dans `profile_json`.

| Colonne | Type | Contraintes |
|---------|------|-------------|
| `id` | UUID | PK |
| `status` | Text | default `active` |
| `jurisdiction` | Text | nullable |
| `profile_json` | JSONB | default `{}` |
| `created_at` | DateTime(tz) | server default now() |
| `updated_at` | DateTime(tz) | server default now(), onupdate |

**Index** : GIN `ix_persons_profile_json`, btree `ix_persons_jurisdiction`.

**Problèmes** :
- **Pas d'endpoint de création** — Person créée directement en base ou par scripts de test
- `profile_json` est un **fourre-tout** : données saisies par l'utilisateur ET données dérivées par le moteur AML (risk-score-current, risk-tier-current, aml-flags, aml-required-actions). Pas de séparation entre données collectées et données calculées
- Pas d'index sur `status` (pourrait être utile pour filtrer par statut)
- Pas de lien FK vers `pe_clients` — le statut KYC "trading" est géré séparément

### 3. `audit_events`

**Rôle** : Journal d'audit pour toutes les actions liées aux personnes.

| Colonne | Type | Contraintes |
|---------|------|-------------|
| `id` | UUID | PK |
| `person_id` | UUID | FK persons.id CASCADE |
| `event_type` | Text | — |
| `actor_type` | Text | user/admin/system/provider |
| `actor_id` | Text | nullable |
| `correlation_id` | UUID | nullable |
| `payload` | JSONB | default `{}` |
| `schema_version` | Integer | default `1` |
| `created_at` | DateTime(tz) | server default now() |

**Index** : `(person_id, created_at)`, `event_type`, `correlation_id`, GIN `payload`.

**Types d'événements observés** :
- `FIELD_SET` : modification d'un champ (slug, ancienne/nouvelle valeur, field_definition_id)
- `AML_RISK_COMPUTED` : résultat scoring (jurisdiction, config_id, version, score, tier, flags, actions, reasons)

**Problèmes** :
- `actor_type` et `actor_id` souvent en dur (`system`/`None`) car auth non branchée
- Pas d'audit pour les changements de configuration (création, publication, suppression de `jurisdiction_configs`)
- Pas d'audit quand les champs dérivés AML sont écrits dans `profile_json` (pas de `FIELD_SET` pour ceux-ci)

### 4. `jurisdiction_configs`

**Rôle** : Configurations versionnées par juridiction et par purpose (KYC ou AML_RISK).

| Colonne | Type | Contraintes |
|---------|------|-------------|
| `id` | UUID | PK |
| `jurisdiction` | Text | — |
| `purpose` | Text | ex. KYC, AML_RISK |
| `version` | Integer | — |
| `status` | Text | draft/active/archived |
| `config_json` | JSONB | — |
| `created_at` | DateTime(tz) | server default now() |
| `updated_at` | DateTime(tz) | server default now() |

**Contrainte** : UNIQUE `(jurisdiction, purpose, version)`.
**Index** : `(jurisdiction, purpose, status)`, GIN `config_json`.

**Problèmes** :
- `jurisdiction` est une chaîne libre — pas de table de référence des juridictions supportées
- Pas de champ `published_by` ou `published_at` pour tracer qui a publié et quand
- Pas de protection contre la suppression d'une config archivée qui a servi pour des scorings passés

### 5. `documents`

**Rôle** : Pièces justificatives (identité, preuves).

| Colonne | Type | Contraintes |
|---------|------|-------------|
| `id` | UUID | PK |
| `person_id` | UUID | FK persons.id CASCADE |
| `doc_type` | Text | — |
| `status` | Text | — |
| `storage_provider` | Text | — |
| `storage_bucket` | Text | — |
| `storage_key` | Text | — |
| `content_type` | Text | — |
| `file_size` | BigInteger | — |
| `sha256` | Text | — |
| `metadata_json` | JSONB | default `{}` |
| `created_at` | DateTime(tz) | server default now() |
| `updated_at` | DateTime(tz) | server default now() |

**Problèmes** :
- **Pas d'API REST** pour upload/download/CRUD documents
- Pas de contrainte d'unicité `(person_id, doc_type)` — doublons possibles
- Table définie mais semble **non utilisée** dans les flux actuels

### 6. `pe_clients` (Portfolio Engine)

**Rôle** : Statut KYC côté produit/trading.

| Colonne notable | Type |
|-----------------|------|
| `kyc_status` | String(30), default `not_started` |

**Enum** : `not_started`, `in_progress`, `approved`, `rejected`.

**Problème critique** : **Pas de FK ni synchronisation** avec `persons`. Le statut KYC trading et le statut KYC compliance sont deux mondes séparés.

### 7. Collision de nommage

Trois classes `AuditEvent` distinctes dans le codebase :
- `database.py` → table `audit_events` (personnes/KYC)
- `portfolio_engine/hardening/audit_models.py` → table `pe_audit_events` (portfolio)
- `finance_strategy_chat/schemas.py` → Pydantic model (chat)

---

## Field System Analysis

### Types de champs supportés

Le fichier `person_fields.py` (`_validate_value_type`) supporte :
- `string` : `isinstance(value, str)`
- `date` / `datetime` : string parsée
- `boolean` : `isinstance(value, bool)`
- `number` : `isinstance(value, (int, float))`
- `enum` : `isinstance(value, str)` — **pas de validation de la valeur contre une liste autorisée**
- `array` : `isinstance(value, list)`
- `json` : `isinstance(value, dict)`
- `file` : `isinstance(value, str)` — URL ou path stocké comme texte

### Validation

- **Présente** : vérification de type Python basique
- **Absente** : regex, format (email, téléphone, IBAN), plage numérique, taille d'array, liste de valeurs enum, validation croisée entre champs

### Dépendances et conditions d'affichage

Le système de conditions est défini dans `schemas_jurisdiction.py` :

```python
class ConditionAction(str, Enum):
    show_block = "show_block"
    hide_block = "hide_block"
    require_field = "require_field"
    optional_field = "optional_field"
    skip_step = "skip_step"
    goto_step = "goto_step"
```

**Écart majeur** : seules `show_block` et `hide_block` sont implémentées dans `onboarding_engine.py`. Les actions `require_field`, `optional_field`, `skip_step`, `goto_step` existent dans le schéma mais **ne sont pas exécutées par le moteur**.

### Opérateurs de condition

Implémentés dans `evaluate_condition` :
- `equals`, `not_equals`
- `in`, `not_in`
- `exists`, `not_exists`

**Absents** : `greater_than`, `less_than`, `contains`, `matches` (regex).

### Multi-juridiction

Les champs sont **globaux** (même catalogue `field_definitions` pour toutes les juridictions). La différenciation se fait par la config KYC qui référence des slugs spécifiques selon la juridiction. C'est une approche correcte mais qui repose entièrement sur la discipline de configuration.

---

## Jurisdiction Config Analysis

### Gestion EU vs UAE

Il n'existe **aucune logique codée en dur** pour différencier EU et UAE. La juridiction est une **chaîne libre** (`Text`) passée en paramètre aux APIs. Les différences régionales résident uniquement dans le contenu de `config_json` pour chaque instance.

**Conséquence** : pas de table de référence des juridictions, pas d'enum, pas de contrainte — n'importe quelle chaîne est acceptée.

### Cycle de vie des configs

```
  draft  ──publish──▶  active  ──(nouvelle publication)──▶  archived
    │                                                          │
    └──────── update (PUT, si draft) ◀─────────────────────────┘
                                            (pas de rollback)
```

### Incohérences identifiées

1. **Validation POST vs PUT** : le POST applique `validate_kyc_config_structure` + normalisation (`field` → `field_slug`, `op` → `operator`). Le PUT valide uniquement via `JurisdictionConfigSchema(**config_json)` sans la même passe de normalisation — une config mise à jour pourrait contenir des clés non normalisées
2. **Pas de rollback** : aucun endpoint pour réactiver une config archivée. Un retour arrière nécessite de créer un nouveau draft (copie manuelle) et de le publier
3. **Suppression sans garde-fou** : DELETE autorisé même sur des configs archivées qui ont pu servir pour des scorings passés (rupture potentielle de l'audit trail)
4. **`entry_rules`** dans le schéma : défini mais non utilisé par le moteur d'onboarding

---

## Risk Scoring Analysis

### Localisation du calcul

Le scoring AML est calculé dans `aml_risk_engine.py` via la fonction `compute_aml_risk`.

### Algorithme

```
1. Charger config active (jurisdiction, purpose="AML_RISK")
2. Lire profile_json de la personne
3. Pour chaque règle (dans l'ordre de la config) :
   a. Évaluer rule.when (conditions sur profile_json)
   b. Si match : score += int(effect.add_score * rule.weight)
   c. Collecter flags et required_actions
   d. Si effect.stop : arrêter
4. Clamp score entre outputs.min_score et outputs.max_score
5. Déterminer tier : premier intervalle [min,max] contenant le score
6. Écrire AuditEvent "AML_RISK_COMPUTED" avec reasons détaillées
7. Projeter dans profile_json : risk-score-current, risk-tier-current, etc.
```

### Configurabilité

| Élément | Configurable | Codé en dur |
|---------|-------------|-------------|
| Liste des règles | ✅ | — |
| Poids des règles | ✅ | — |
| Flags et actions | ✅ | — |
| Bornes min/max | ✅ | — |
| Tiers (paliers) | ✅ | Labels limités à `low/medium/high` |
| Algorithme (ordre, stop, clamp) | — | ✅ |
| Slugs de sortie dérivés | — | ✅ (`risk-score-current`, etc.) |
| Opérateurs de condition | — | ✅ (equals, in, exists, etc.) |

### Traçabilité et explicabilité

**Points forts** :
- Chaque calcul produit un `AuditEvent` avec `reasons` détaillant pour chaque règle matchée : le slug évalué, la valeur snapshot, le delta de score
- `correlation_id` pour lier les événements d'une même session
- `config_id` et `version` sauvegardés dans le payload

**Points faibles** :
- Les slugs dérivés écrits dans `profile_json` ne génèrent **pas** d'événement `FIELD_SET`
- Pas de versioning de l'algorithme lui-même (si le code du moteur change, l'audit ne le capture pas)
- `actor_type` toujours `system` — on ne sait pas qui a déclenché le calcul

### Compatibilité régulateur

Le système est **globalement compatible** avec les exigences d'explicabilité AML :
- Score traçable avec justification par règle
- Configs versionnées avec historique
- Journal immutable (`audit_events`)

**Lacunes** :
- Pas de signature ou checksum sur les events
- Pas de protection contre la modification directe en base
- Auth absente = non-répudiation impossible

---

## API Analysis

### Endpoints KYC / Compliance

| Route | Méthode | Auth | Rôle |
|-------|---------|------|------|
| `/api/persons/{id}` | GET | ❌ | Lire une personne |
| `/api/persons/{id}/fields` | POST | ❌ (stub) | Écrire un champ |
| `/api/persons/{id}/onboarding/next-step` | GET | ❌ | Prochaine étape KYC |
| `/api/persons/{id}/onboarding/submit-step` | POST | ❌ | Soumettre une étape |
| `/api/persons/{id}/risk/compute` | POST | ❌ | Calculer le score AML |
| `/api/persons/{id}/risk/latest` | GET | ❌ | Dernier score AML |
| `/api/jurisdiction-configs` | POST | ❌ | Créer une config |
| `/api/jurisdiction-configs/{id}/publish` | POST | ❌ | Publier une config |
| `/api/jurisdiction-configs/active` | GET | ❌ | Config active |
| `/api/jurisdiction-configs` | GET | ❌ | Lister les configs |
| `/api/jurisdiction-configs/{id}` | GET/PUT/DELETE | ❌ | CRUD config |
| `/api/field-definitions` | GET | ❌ | Catalogue de champs |
| `/api/ai/jurisdiction-configs/compose` | POST | ✅ JWT | Générer config par IA |
| `/api/ai/jurisdiction-configs/validate` | POST | ✅ JWT | Valider config par IA |

### Problèmes structurels

1. **Authentification** : seuls les endpoints IA sont protégés par JWT. Tous les autres endpoints KYC/compliance/scoring sont **ouverts**
2. **Pas d'endpoint création Person** : la personne doit être créée en base manuellement
3. **Pas d'API documents** : la table `documents` existe mais n'a pas d'endpoints REST
4. **Pas de CRUD field_definitions** : uniquement GET en lecture ; la gestion se fait par seed CSV
5. **Cohérence requête** : `jurisdiction` et `purpose` passés en query string (pas en header ni déduit du contexte utilisateur)

---

## Problems Identified

### Critiques

| # | Problème | Impact |
|---|----------|--------|
| C1 | **Authentification absente** sur la quasi-totalité des endpoints KYC/compliance | Exposition totale des données personnelles et des opérations sensibles (scoring, modification de champs, publication de configs) |
| C2 | **Pas de synchronisation** entre `persons` (compliance) et `pe_clients` (trading) | Un utilisateur peut avoir `kyc_status = approved` côté trading sans validation compliance réelle, ou inversement |
| C3 | **Écart schéma/moteur** : actions `require_field`, `optional_field`, `skip_step`, `goto_step` définies mais non implémentées | Fausse impression de fonctionnalité ; configs utilisant ces actions ne produisent aucun effet |
| C4 | **Pas d'endpoint création Person** | Impossible d'onboarder un utilisateur via l'API seule |

### Moyens

| # | Problème | Impact |
|---|----------|--------|
| M1 | **Pas d'audit** sur les changements de config jurisdiction (création, publication, suppression) | Conformité réglementaire incomplète — impossible de savoir qui a changé les règles et quand |
| M2 | **Slugs dérivés AML codés en dur** (`risk-score-current`, etc.) | Couplage fort entre le moteur et le catalogue de champs ; erreur silencieuse si le slug n'existe pas |
| M3 | **Validation PUT incomplète** par rapport au POST pour les configs KYC | Config potentiellement mal normalisée après mise à jour |
| M4 | **Pas de validation métier** pour les champs `enum` (pas de liste de valeurs autorisées) | Accepte n'importe quelle chaîne pour un champ censé être contraint |
| M5 | **`profile_json` mélange** données saisies et données calculées | Risque de collision, difficulté de distinguer l'origine d'une valeur |
| M6 | **Collision de nommage** : 3 classes `AuditEvent` dans le codebase | Confusion potentielle d'imports |
| M7 | **Tiers AML limités** aux labels `low/medium/high` dans le schéma Pydantic | Impossible d'ajouter des paliers intermédiaires sans modifier le code |
| M8 | **Documents table sans API** | Fonctionnalité KYC incomplète côté documents justificatifs |

### Améliorations possibles

| # | Amélioration | Bénéfice |
|---|-------------|----------|
| A1 | Ajouter une table `jurisdictions` de référence avec enum ou contrainte | Prévenir les erreurs de saisie, documenter les juridictions supportées |
| A2 | Ajouter index btree sur `persons.status` | Performance si filtrage fréquent par statut |
| A3 | Implémenter les actions conditionnelles manquantes ou les retirer du schéma | Cohérence entre ce qui est promis et ce qui fonctionne |
| A4 | Séparer `profile_json` en `collected_data` et `computed_data` | Clarté et intégrité |
| A5 | Ajouter un endpoint de rollback (réactivation d'une config archivée) | Opérabilité en cas de problème de config |
| A6 | Créer des `FIELD_SET` pour les champs dérivés AML | Traçabilité complète |
| A7 | Ajouter des opérateurs de condition manquants (`greater_than`, `less_than`, `contains`) | Expressivité des règles |
| A8 | Ajouter `published_by` et `published_at` sur `jurisdiction_configs` | Auditabilité admin |
| A9 | Contrainte d'unicité `(person_id, doc_type)` sur `documents` | Prévenir les doublons |
| A10 | Implémenter un `ValidationError` import dans `ai_jurisdiction_configs/routes.py` | Corriger un bug potentiel (`NameError` si Pydantic lève une exception) |

---

## Recommendations (High Level Only)

1. **Phase 1 — Sécurité** : Brancher l'authentification JWT sur tous les endpoints KYC/compliance/scoring avec distinction des rôles (user, admin, system)

2. **Phase 2 — Cohérence modèle** : Synchroniser `persons` et `pe_clients` via un mécanisme de FK ou d'événements, séparer les données collectées des données calculées dans `profile_json`

3. **Phase 3 — Moteur complet** : Implémenter les actions conditionnelles (`require_field`, `skip_step`, `goto_step`) ou les retirer du schéma si non nécessaires ; ajouter les opérateurs manquants

4. **Phase 4 — Audit admin** : Logger les changements de configs (qui a créé, publié, supprimé, quand) dans `audit_events` ou une table dédiée ; ajouter `published_by`/`published_at`

5. **Phase 5 — Documents** : Exposer une API CRUD pour les documents justificatifs avec upload S3 et liaison au flux d'onboarding

6. **Phase 6 — Validation** : Enrichir la validation des champs (listes enum, regex, plages) et ajouter un système de validation croisée entre champs

7. **Phase 7 — Gestion des configs** : Ajouter rollback, protection contre la suppression de configs archivées, et améliorer la parité PUT/POST en validation
