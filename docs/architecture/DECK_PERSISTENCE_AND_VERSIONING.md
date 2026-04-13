# Architecture — persistance et versionnement des présentations (decks)

**Objectif** : modèle de données et API alignés sur les besoins métier (templates référentiels, decks, versions, lifecycle draft / validated / archived), cohérents avec **FastAPI + SQLAlchemy + Alembic** (`services/arquantix/api`).

---

## 1. Choix de modélisation : hybride (recommandé et implémenté)

| Approche | Avantages | Inconvénients |
|----------|-----------|----------------|
| **A — Snapshot JSON seul** | Immutabilité simple, export audit trivial | Édition difficile, requêtes SQL pauvres, conflits merge |
| **B — Relationnel seul** | Requêtes fines, ordre des slides naturel | « Immutabilité validée » sans copie = risque d’altération rétroactive si mal gouverné |
| **C — Hybride** | Édition sur lignes `presentation_version_slides` ; à la **validation**, écriture d’un **`snapshot_json`** figé ; relecture audit sans dépendre des UPDATE ultérieurs | Légère redondance ; discipline service (blocage des mutations si `validated`) |

**Décision** : **C — Hybride**.

- **Brouillon** : vérité opérationnelle = tables `presentation_version_slides` (+ métadonnées sur `presentation_deck_versions`).
- **Validée** : `snapshot_json` rempli une fois ; le service **refuse** les mutations sur les slides et sur le snapshot ; lecture « officielle » peut prioriser le snapshot pour l’audit.
- **Archivée** : pas de suppression ; plus **courante** ; restauration possible vers **draft** (choix impl : sortie d’archive = draft pour permettre re-travail).

---

## 2. Schéma relationnel (PostgreSQL, schéma `public`)

### 2.1 `presentation_slide_templates`

Ressource référentielle pour un type de slide.

| Colonne | Type | Notes |
|---------|------|--------|
| `id` | UUID PK | |
| `key` | TEXT UNIQUE | Stable (ex. `title`, `metrics`) — lien avec le front |
| `name`, `category`, `description` | TEXT | `description` nullable |
| `status` | TEXT | `active` \| `inactive` \| `archived` |
| `preview_image_url` | TEXT nullable | |
| `schema_json` | JSONB | Schéma JSON Schema (sous-ensemble) pour `content_json` |
| `default_content_json` | JSONB | Valeurs par défaut à l’insertion d’une slide |
| `design_tokens_json` | JSONB nullable | Optionnel : surcharges DS |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

**Évolution des templates** : la v1 utilise une seule ligne par `key` avec `schema_json` versionné par convention (champ `version` dans le JSON si besoin). Une évolution future peut introduire `presentation_slide_template_revisions` sans casser les clés.

### 2.2 `presentation_decks`

Entité métier « présentation ».

| Colonne | Type | Notes |
|---------|------|--------|
| `id` | UUID PK | |
| `name`, `slug` | TEXT ; `slug` UNIQUE | |
| `description` | TEXT nullable | |
| `deck_type` | TEXT nullable | ex. `investor`, `product`, `internal` |
| `current_version_id` | UUID FK nullable | → `presentation_deck_versions.id` ON DELETE SET NULL |
| `created_at`, `updated_at` | TIMESTAMPTZ | |
| `archived_at` | TIMESTAMPTZ nullable | Présentation archivée (versions conservées) |

### 2.3 `presentation_deck_versions`

| Colonne | Type | Notes |
|---------|------|--------|
| `id` | UUID PK | |
| `presentation_id` | UUID FK | CASCADE delete deck → versions |
| `version_number` | INT | UNIQUE (`presentation_id`, `version_number`) |
| `version_label` | TEXT | ex. `V1` |
| `status` | TEXT | `draft` \| `validated` \| `archived` |
| `is_current` | BOOL | Une seule version courante par deck (index unique partiel) |
| `changelog` | TEXT nullable | |
| `snapshot_json` | JSONB nullable | Rempli à la validation |
| `validated_at`, `archived_at` | TIMESTAMPTZ nullable | |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

**Règles** :

- Une seule ligne avec `is_current = true` par `presentation_id` (index unique partiel PostgreSQL).
- **Dupliquer** une version : nouvelle ligne, `version_number = max+1`, `status = draft`, copie des slides depuis la source.
- **Valider** : `status = validated`, `snapshot_json` = document complet, `validated_at = now()`, slides non modifiables ensuite.

### 2.4 `presentation_version_slides`

| Colonne | Type | Notes |
|---------|------|--------|
| `id` | UUID PK | |
| `presentation_version_id` | UUID FK | CASCADE |
| `sort_order` | INT | |
| `slide_template_id` | UUID FK | → `presentation_slide_templates` |
| `slide_title`, `subtitle` | TEXT nullable | |
| `content_json` | JSONB | Données métier validées vs `schema_json` du template |
| `style_overrides_json`, `notes_json`, `metadata_json` | JSONB nullable | Notes orateur, visibilité dans `metadata_json` |

---

## 3. Validation `content_json` vs `schema_json`

- Service utilise la bibliothèque **`jsonschema`** (Draft 2020-12 ou compatible) sur le schéma stocké en base.
- Si `schema_json` est vide ou absent, la validation est **no-op** (compat migration progressive).

---

## 4. API REST (préfixes)

Implémentés sous `services/arquantix/api/services/presentations/` :

- **`/api/presentation-templates`** — CRUD + archive / restore des templates.
- **`/api/presentations`** — CRUD deck + archive / restore + liste des versions.
- **`/api/presentation-versions`** — opérations par `version_id` : validate, archive, restore, duplicate, set-current, save-draft, CRUD slides, reorder.

*Les chemins exacts correspondent aux spécifications utilisateur ; détail dans le code (`router.py`).*

**Validation contenu slide (évite le conflit de route avec `/{template_id}`)** :

- `POST /api/presentation-templates/validate-content?template_id={uuid}` — corps `{ "content_json": { ... } }`.

**Sécurité (v1)** : endpoints **sans JWT** par défaut (aligné sur plusieurs routes internes type field-definitions). À durcir derrière réseau privé ou `get_current_user` pour la production ouverte.

---

## 5. Front (`presentation-design-system`)

- Variable **`VITE_ARQUANTIX_API_URL`** (ex. `http://localhost:8011`) pour les appels fetch.
- Pages minimales : liste des présentations, détail + versions, éditeur de version (liste de slides + formulaire JSON + boutons d’action).
- **Registre React** : inchangé pour le rendu ; l’éditeur peut afficher un aperçu limité ou se concentrer sur les données jusqu’à branchement preview complet.

---

## 6. Impacts sur l’existant

- **Aucun breaking change** sur `RegistrationDeck` ou la galerie tant que l’on n’y branche pas l’API.
- **Prochaine étape produit** : faire converger les `key` SQL avec les `SlideType` de la galerie et externaliser le contenu demo vers la BDD (optionnel).

---

## 7. Seed

Des templates d’exemple (`title`, `section-divider`, `metrics`, `two-column`, `team`, `quote`, `closing`) sont insérés par la migration **095** pour démo / tests manuels.
