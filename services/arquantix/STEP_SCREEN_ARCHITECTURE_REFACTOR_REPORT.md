# Steps & screens — audit et proposition d’évolution (registration engine)

## Objectif du document

Documenter **l’état réel** du moteur (DB, backend, Flutter, admin), les **écarts** par rapport à l’intention « step = module logique », puis proposer une **architecture cible**, une **stratégie de migration** prudente et les **impacts** admin / front — **sans** imposer une refonte totale ni casser l’existant.

---

## Partie 1 — Audit actuel

### 1.1 Modèle de données

| Entité | Table | Rôle |
|--------|--------|------|
| Flow | `registration_flows` | Versionné par juridiction + `entrypoint_type` (`uq_reg_flow_jurisdiction_entry_version`). |
| **Step** | `registration_flows_steps` → `registration_flow_steps` | Module logique au sens **schéma** : `step_key`, `position`, `is_optional`, `is_blocking`, `visibility_rule_json`, `completion_rule_json`, i18n titres. |
| **Screen** | `registration_step_screens` | **Plusieurs** écrans par step : FK `step_id`, `screen_key` **unique par step**, `position`, `config_json`, `screen_type`, etc. |
| Composants | `registration_screen_components` | Rattachés au **screen** (`screen_id`). |
| Session runtime | `registration_sessions` | Curseur : `current_step_id` **et** `current_screen_id`, `progress_percent`, `flow_id`. |
| État par step | `registration_session_steps` | `status`, `started_at`, `completed_at`, **`skipped_at`**, `last_screen_id`, `metadata_json`. |

**Conclusion modèle** : la base **supporte déjà** la hiérarchie `flow → steps[] → screens[] → components[]`. La contrainte `(step_id, screen_key)` impose l’unicité de la clé d’écran **dans** un step, pas globalement au flow.

**Ce qui crée la confusion produit** : les **seeds / migrations** (ex. EU v2/v3) modèlent très souvent **un seul `registration_step_screen` par `registration_flow_step`** (position 0). Du coup, en pratique, **step_key ≈ screen_key** dans l’esprit métier, et la liste « des steps » ressemble à une **liste plate d’écrans**.

### 1.2 `config_json`

- **Niveau screen** (`registration_step_screens.config_json`) : métadonnées d’écran (ex. `step_metadata`, `phone_confirm_modal_enabled`, `show_success_modal_on_complete`, etc.).
- **Niveau step** : pas de colonne `module` dédiée ; la **sémantique module** peut être portée par **`step_key`** et/ou enrichie dans `completion_rule_json` / futur champ JSON.

### 1.3 Backend — utilisation des steps et des screens

- **Navigation** : `RegistrationSessionService._flatten_visible_screens(flow, context)` construit une **liste linéaire** de tous les **screens visibles**, dans l’ordre des steps (`position` step puis `position` screen), après `filter_visible_items` sur steps et screens.
- **`next_screen` / `prev_screen`** : index dans cette **liste aplatie** ; le passage à l’écran suivant peut **changer de step** ; à la frontière de step, `_mark_step_completed` et `_enforce_blocking_gate` (steps bloquants jusqu’au step courant).
- **Progression** : `progress_percent` est calculée sur **le nombre total d’écrans aplatis** (`_compute_progress(current_idx, len(flat_screens))`), pas sur le nombre de **modules** steps.
- **Soumission** : validation sur **l’écran courant** (`submit_screen`) ; agrégation des champs requis au niveau **step** pour `_are_step_required_fields_present` et garde blocking.

**Dépendance `registration_progress`** : la logique canonique (`services/customers_admin/registration_progress.py`) s’appuie sur des **`step_key`** et des valeurs dans `profile_json["collected"]`, pas sur les `screen_key`. Tant que les **identifiants `step_key`** restent stables ou mappés, l’impact est **modéré** ; un **regroupement** de steps en moins de lignes DB mais **même** `step_key` sur un module agrégé demande une **migration de données** et une **stratégie de migration** prudente (voir partie 3).

### 1.4 Frontend Flutter

- **Une requête = un écran** : le client consomme `GET /screen` (ou équivalent runtime) et affiche **`screen` + `components`** (via `RegistrationFlowScreen` / renderer).
- **Parcours** : `submit` / `next` / `prev` ; **pas besoin** côté app de « connaître » explicitement la liste des screens d’un step : le **serveur** est la source de vérité du curseur (`current_screen_id`).
- **Flatten** : la **progress bar** utilise `progress_percent` serveur ; **pas** de second flatten client des steps pour la navigation principale.

**Limite UX** : l’UI ne montre **pas** un « sous-pas » dans un module (ex. 2/4 écrans du module financial) tant que l’API ne renvoie pas une structure **module + index dans le module** (optionnel, partie 5).

### 1.5 Admin (Next.js)

- Le fichier `web/src/app/admin/registration/flows/[id]/edit/page.tsx` gère déjà **`steps[]`**, **`selectedStepId`**, **`screens[]`** (chargés par step), **`loadScreens(selectedStepId)`**, et création d’écran sous un step (`POST .../steps/{id}/screens`).
- **Donc** : le modèle **step → screens** est **éditable** ; la perception « liste plate » vient surtout du **contenu** des flux (1 screen/step) et possiblement de **vues** / preview qui **aplatissent** mentalement la liste des `step_key` sans montrer la profondeur **screens**.

---

## Partie 2 — Proposition d’architecture cible

### 2.1 Principes

1. **Step = module logique** (ex. `identity_foundation`, `financial_profile`, `investor_profile`, `kyc_documents`).
2. **Screen = écran UI** (plusieurs par step, ordonnés par `position`).
3. **Comportement runtime inchangé au niveau API** : curseur `(current_step_id, current_screen_id)` + liste aplatisée pour next/prev ; **compatibilité** avec les sessions en cours.

### 2.2 Champs cibles (évolution incrémentale)

| Besoin | Approche recommandée | Rationale |
|--------|----------------------|-----------|
| `step.module` | **Option A** : convention `step_key` préfixe ou nom stable (`financial_profile`, …). **Option B** : nouvelle colonne `module_key` (text) ou `metadata_json` sur `registration_flow_steps`. | Évite de casser les `step_key` déjà utilisés en audit / progress. |
| `step.is_blocking` | **Déjà** : `is_blocking` sur `registration_flow_steps`. | Conserver. |
| `step.is_skippable` | **Proche** de `is_optional` existant ; renommer ou documenter (`is_optional` = step entier skippable). | Éviter doublon ; aligner sémantique produit ↔ colonne. |
| `step.trigger_condition` | **Déjà** : `visibility_rule_json` (même DSL que `rules.py`). | Éventuellement alias / doc métier « trigger = visibility ». |
| `step.order` | **Déjà** : `position`. | Conserver. |

### 2.3 Structure cible (schéma logique)

```
registration_flow
  └── registration_flow_steps[]     # modules, ordre = position
        ├── step_key, module (key), visibility, blocking, optional/skippable
        └── registration_step_screens[]   # vrais écrans UI
              ├── screen_key, position, config_json, screen_type
              └── registration_screen_components[]
```

### 2.4 Cohérence CMS / scoring / KYC

- **Scoring** : les **binding_slug** et valeurs normalisées restent sur **session_data** / **collected** ; **pas** besoin de lier le scoring au nombre de steps tant que les slugs sont stables.
- **KYC / investor questionnaire** : nouveaux **steps** (modules) avec **N screens** + `visibility_rule_json` sur step ou screen selon le besoin.

---

## Partie 3 — Stratégie de migration

### 3.1 Principe « safe »

1. **Ne pas** déplacer d’IDs de **screen** pour les sessions **in_progress** sans script de **réécriture** de `current_screen_id` — **risque élevé**.
2. **Stratégie A (recommandée, faible risque)** : pour les **nouveaux** flux (nouvelle version de flow), **concevoir** dès la création **plusieurs screens par module** ; les flux **archivés** restent inchangés.
3. **Stratégie B (regroupement)** : fusionner plusieurs **steps** en un seul **step** avec **plusieurs screens** — implique :
   - migration SQL : créer un nouveau step, **réattacher** les `registration_step_screens` (changer `step_id`), **supprimer** les anciens steps vides ;
   - **mise à jour** `registration_sessions.current_step_id` / `current_screen_id` ;
   - **mise à jour** `registration_session_steps` (step_id) ;
   - **tests** de non-régression sur `registration_progress` (clés `step_key`).

### 3.2 Mapping concret (exemple EU v3)

| Regroupement logique | Step cible (exemple) | Contenu actuel (v3) |
|----------------------|----------------------|---------------------|
| Identity foundation | `identity_foundation` (nouveau step agrégé) | identity, date_of_birth, residence_country, home_address, contact_email, email_verification_optional, terms — **chacun** pourrait devenir un **screen** au lieu d’un **step** | **Attention** : opération lourde ; plutôt **nouveau flow v4** qu’édition destructive de v3. |
| Financial profile | `financial_profile` | `employment_status` … `financial_acknowledgements` : déjà **6 steps** ; alternative = **1 step** + **6 screens** | Migration B. |

**Recommandation** : pour **identity / financial**, introduire la structure « module = 1 step, N screens » sur **un nouveau `registration_flows.version`** (ex. v4), **sans** modifier les lignes de v3 utilisées en prod par des sessions ouvertes.

### 3.3 Compatibilité backward

- **Anciens flows** : inchangés ; sessions **restent** sur `flow_id` + `flow_version`.
- **API** : mêmes endpoints ; réponses JSON **enrichissables** (optionnel) avec `screens_in_step_total`, `screen_index_in_step` sans casser l’app actuelle.
- **Flutter** : aucun changement obligatoire si la progression reste **screen**-driven.

---

## Partie 4 — Impact admin

### 4.1 État actuel

- **Steps** listés ; **sélection d’un step** → **screens** + **components** dans les panneaux.
- Création d’écrans **déjà** possible par step.

### 4.2 Améliorations souhaitées

| Fonctionnalité | Complexité | Notes |
|----------------|------------|--------|
| **Vue « modules »** en premier (cartes par step avec `module` / `step_key`) | Moyenne | Filtrage / libellés depuis `module_key` ou `step_key`. |
| **Clic step → liste des screens** (déjà partiellement là) | Faible | Renforcer l’UX (breadcrumb, compteur « N écrans »). |
| **Drag & drop** des **screens** **dans** un step | Moyenne | API `PATCH` ordre `position` sur `registration_step_screens` ; état local optimiste ; contraintes uniques. |
| **Ajouter un step** | Déjà possible | Vérifier position par défaut et `step_key` unique. |
| **Preview** : affichage **hiérarchique** step → screens | Moyenne | Éviter liste plate dans la preview si c’est la source de confusion. |

---

## Partie 5 — Impact frontend (Flutter & autres)

### 5.1 Navigation

- **Court terme** : **aucun** changement requis si le backend continue à piloter `next`/`prev` sur la liste aplatisée.
- **Moyen terme** (optionnel) :
  - **Sous-progression** dans le module : afficher « Écran 2/5 du module Financial » si l’API expose `screen_index` / `screens_count` dans le payload **écran**.
  - **Skip module** : le moteur a déjà `skipped_at` sur `registration_session_steps` ; il faut **exposer** une action API « skip step » (si `is_optional`) et un **bouton** dans l’UI — **à spécifier** (pas encore un flux standard partout).

### 5.2 Progression par module

- **Calcul** : peut être **dérivé** côté serveur (nombre de steps complétés / nombre de steps visibles) **en** **complément** de `progress_percent` écran-based, pour éviter deux vérités contradictoires — **décision produit** à trancher (ratio **écrans** vs **modules**).

---

## Partie 6 — Synthèse : limites actuelles vs cible

| Sujet | Limite actuelle | Cible |
|-------|-----------------|--------|
| Sémantique step | Souvent 1 screen → step perçu comme « écran » | Step = module ; plusieurs screens |
| **DB** | Déjà **1-N** step→screens | **Aucun** changement schéma obligatoire pour la hiérarchie |
| **Navigation** | Flatten sur **screens** | **Identique** ; optionnel enrichissement |
| **Progress** | % sur **nombre d’écrans** | Optionnel : % **modules** ou double indicateur |
| **registration_progress** | Basé sur **step_key** | **Stable** si `step_key` conservés ; attention si fusion de steps |
| **Admin** | Hiérarchie éditable mais UX perfectible | Modules + DnD + preview hiérarchique |

---

## Recommandations priorisées

1. **Court terme (sans migration lourde)** : documenter et utiliser **`step_key` + `config_json.step_metadata.module`** (déjà utilisé pour financial) ; **ajouter** `module_key` en DB **seulement** si besoin de requêtes SQL filtrantes.
2. **Contenu** : nouer **nouveaux flows versionnés** avec **plusieurs screens par module** (ex. investor questionnaire) **sans** toucher aux flux archivés.
3. **API (optionnel)** : enrichir `GET screen` avec `step_context: { step_key, module, screen_index, screens_in_step }` pour **Flutter** et **admin preview**.
4. **Skip module** : aligner produit sur `is_optional` + `registration_session_steps.skipped_at` + endpoint dédié.
5. **Migration B** (fusion steps) : **uniquement** avec plan de test sessions + **nouvelle version** de flow plutôt que **patch** en place sur flux actif.

---

## Fichiers de référence (code)

- Modèle : `api/database.py` — `RegistrationFlow`, `RegistrationFlowStep`, `RegistrationStepScreen`, `RegistrationSession`, `RegistrationSessionStep`.
- Navigation / flatten : `api/services/registration/service.py` — `_flatten_visible_screens`, `next_screen`, `_build_screen_response`.
- Règles : `api/services/registration/rules.py`.
- Progression client : `api/services/customers_admin/registration_progress.py`.
- Admin : `web/src/app/admin/registration/flows/[id]/edit/page.tsx`.
- Flutter : `mobile/lib/features/registration/screens/registration_flow_screen.dart`, `data/registration_models.dart`.

---

*Document généré pour préparer l’évolution « step = module, screen = écran » sans refonte totale — aligné sur le code présent dans le dépôt arquantix.*
