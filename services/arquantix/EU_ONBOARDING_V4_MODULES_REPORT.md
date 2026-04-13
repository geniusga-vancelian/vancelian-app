# EU Individual Onboarding v4 — steps = modules, screens = UI

## Objectif

Passer d’un modèle **1 step = 1 écran** (v3) à **1 step = module logique** avec **plusieurs écrans** par step (v4), **sans** modifier les données v3 ni casser les sessions v3 en cours.

## Identifiants et statut

| Champ | Valeur |
|--------|--------|
| Nom | `EU Individual Onboarding v4` |
| `version` | `4` |
| `status` | `active` (après migration) |
| UUID flux v4 | `a4b5c6d7-e8f9-40a1-b2c3-d4e5f6a7b8c9` |

Le flux **v3** (`f1e2d3c4-b5a6-4789-9abc-def012345678`) est passé en **`archived`** lors de l’upgrade Alembic **124** ; les sessions existantes sur v3 restent rattachées à ce flux.

## Migration Alembic

- **Révision** : `124` — `api/alembic/versions/124_eu_registration_flow_v4_modules.py`
- **Prérequis** : `123` (flux EU v3 présent en base).
- **Schéma** : ajout de la colonne **`registration_step_screens.visibility_rule_json`** (JSONB nullable) pour porter les règles de visibilité au niveau **écran** (nécessaire quand plusieurs écrans partagent un même step).

### Downgrade

Suppression du flux v4, réactivation du flux v3, suppression de la colonne `visibility_rule_json` sur les écrans.

## Mapping v3 → v4

En v3, chaque ligne ci-dessous correspondait à **un** `registration_flow_steps` avec **un** écran. En v4, les **mêmes** enregistrements d’écrans (clonés puis réassignés) sont regroupés sous **trois** steps modules.

### Step `identity_foundation` (position 0)

| Ordre | Ancien step_key v3 | `screen_key` |
|------:|-------------------|--------------|
| 0 | `identity` | `identity_form` |
| 1 | `date_of_birth` | `dob_form` |
| 2 | `residence_country` | `residence_country_form` |
| 3 | `home_address` | `home_address_form` |
| 4 | `contact_email` | `email_form` |
| 5 | `email_verification_optional` | `email_otp_optional_form` |
| 6 | `terms` | `terms_form` |

- **is_blocking** : `true`  
- **is_optional** : `false`

### Step `financial_profile` (position 1)

| Ordre | Ancien step_key v3 | `screen_key` |
|------:|-------------------|--------------|
| 0 | `employment_status` | `employment_status_form` |
| 1 | `work_details` | `work_details_form` |
| 2 | `annual_income` | `annual_income_form` |
| 3 | `net_worth` | `net_worth_form` |
| 4 | `source_of_wealth` | `source_of_wealth_form` |
| 5 | `financial_acknowledgements` | `financial_acknowledgements_form` |

- **is_blocking** : `false`  
- **is_optional** : `true`

La règle de visibilité qui était sur le **step** `work_details` en v3 est **copiée** sur l’**écran** `work_details_form` en v4 (`visibility_rule_json`), pour que `_flatten_visible_screens` et le filtrage par écran restent cohérents.

### Step `investor_profile` (position 2)

- Placeholder : **aucun** écran pour l’instant.  
- **is_blocking** : `false`, **is_optional** : `true`.

### Ce qui est conservé à l’identique (réassignation uniquement)

- `config_json`, composants, `binding_slug`, clés d’écran : **pas** de nouveaux écrans métier ; clonage puis **UPDATE** `step_id` + `position`.

### Nettoyage v4 uniquement

Les anciens steps v4 au format « un step_key par ancien écran » (liste `OLD_STEP_KEYS` dans la migration) sont **supprimés** du flux v4 une fois les écrans rattachés aux modules ; **aucune** suppression sur le flux v3.

## Structure finale (v4)

```
registration_flows (v4)
├── identity_foundation      [7 screens]
├── financial_profile      [6 screens]
└── investor_profile       [0 screens]
```

## Impact runtime (API registration)

- **Moteur inchangé** : navigation toujours **écran par écran** ; `_flatten_visible_screens` et enchaînement `next` / `prev` inchangés côté logique métier.
- **Bonus** : la réponse `_build_screen_response` inclut **`step_context`** lorsque session + écran courants sont définis :
  - `step_key`
  - `step_position`
  - `screen_index_in_step` (index parmi les écrans **visibles** du step, triés par `position`)
  - `screens_in_step` (nombre d’écrans visibles dans le step)

Les clients existants qui ignorent ce champ ne sont pas impactés.

## Impact admin / progression

- **Registration progress** (back-office clients) : agrégation des jalons **`identity_foundation`** et **`financial_profile`** sans double comptage avec les clés granulaires (voir `registration_progress.py`).
- **Admin registration** : sérialisation / mise à jour des écrans avec **`visibility_rule_json`** où pertinent (`admin_router`).

## Compatibilité

| Zone | Comportement |
|------|----------------|
| Sessions **v3** | Flux archivé ; pas de modification des lignes historiques du flux v3. |
| Nouvelles sessions | Pointent vers le flux **actif** (v4 après migration). |
| Frontend / Flutter | Aucun changement obligatoire ; consommation écran par écran. |
| Prisma (`RegistrationStepScreens`) | Champ optionnel `visibilityRuleJson` mappé sur `visibility_rule_json` pour alignement schéma. |

## Tests

- `tests/test_registration_flow.py` — dont visibilité conditionnelle composant : après `submit_screen`, la réponse reflète le contexte mis à jour **sans** `prev` sur un flux à écran unique de test.
- `tests/test_customers_admin_registration_progress.py` — régression progression.

Commande indicative :

```bash
cd services/arquantix/api && python3 -m pytest tests/test_registration_flow.py tests/test_customers_admin_registration_progress.py -q
```

## Références fichiers clés

- Migration : `api/alembic/versions/124_eu_registration_flow_v4_modules.py`
- Réponses + `step_context` : `api/services/registration/service.py`
- Modèle ORM écran : `api/database.py` (`RegistrationStepScreen.visibility_rule_json`)
- Progression admin : `api/services/customers_admin/registration_progress.py`, `schemas.py`
