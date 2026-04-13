# Jurisdiction policy — résidence vs nationalité

## Executive Summary

La table `public.jurisdiction_country_policies` expose désormais un troisième axe **`allow_nationality`**, distinct de `allow_residence` et `allow_phone_country_code`. Le **runtime d’inscription** choisit la liste injectée dans `allowed_countries` selon le **`binding_slug`** (`country_of_residence`, `nationality`, ou autre en compatibilité). La **validation submit** applique les codes d’erreur **`[RESIDENCE_COUNTRY_NOT_ALLOWED]`** et **`[NATIONALITY_COUNTRY_NOT_ALLOWED]`** selon le cas. L’**admin API / UI** permet d’éditer la nationalité par pays ; le **flow editor** affiche uniquement des compteurs (pas d’édition). **Flutter** reste un consommateur de `allowed_countries` / `default_country` sans logique métier juridictionnelle.

## Why Residence And Nationality Were Split

- La **résidence** est contrainte par la juridiction d’onboarding (ex. liste EU, résidence UAE uniquement).
- La **nationalité** est un attribut démographique souvent **plus large** : un résident UAE peut déclarer une nationalité hors pays de résidence.
- Traiter tous les `country_picker` comme « résidence » provoquait des **faux refus** en submit et des **listes UI trop étroites** pour le champ nationalité.

## Data Model Evolution

- Colonne **`allow_nationality`** : `BOOLEAN NOT NULL`, ajoutée par la migration **`102_jurisdiction_country_policy_allow_nationality.py`**.
- **`is_default_residence`** et **`is_default_phone`** inchangés ; pas de **`is_default_nationality`** dans cette phase.
- Modèle SQLAlchemy : `JurisdictionCountryPolicy.allow_nationality` dans `api/database.py`.

## Backfill Strategy

**Règle métier retenue pour la nationalité (seed / migration)** :

1. Pour les juridictions **`EU`** et **`UAE`** :
   - **UPDATE** : `allow_nationality = true` sur **toutes les lignes déjà présentes** (la liste résidence historique reste inchangée pour ces lignes).
   - **INSERT** : pour chaque pays **`country_directory.is_active = true`** sans ligne `(jurisdiction, iso2)`, création d’une ligne **nationalité seule** : `allow_residence = false`, `allow_phone_country_code = false`, `allow_nationality = true`, `position` élevée (plage 20 000+) pour ne pas perturber l’ordre résidence existant.

**Hypothèses** :

- La **vérité métier** pour « quels pays peuvent être nationalités » est, pour EU/UAE au moment de la migration, **l’ensemble des pays actifs du référentiel** `country_directory`. Les pays non présents dans l’annuaire ne sont pas injectés automatiquement.
- Les autres juridictions (ex. jeux de tests `JTEU*`) ne sont **pas** modifiées par la migration : `allow_nationality` reste à `false` jusqu’à configuration explicite.

**Décision documentée** : nationalité **≠** résidence ; l’élargissement se fait via `allow_nationality` (et lignes dédiées), pas via un assouplissement de `allow_residence`.

## Runtime Enrichment By Binding Slug

Fichier : `api/services/registration/jurisdiction_policies.py` — `enrich_registration_component_props(..., binding_slug=...)`.

| `binding_slug`   | Comportement |
|------------------|--------------|
| `nationality`    | Si `jurisdiction_has_nationality_policies` : `list_allowed_nationality_countries` → `allowed_countries`, `default_country` = premier pays de la liste (ordre policy). Sinon : **pas d’injection** (client non filtré par la policy nationalité). |
| `country_of_residence` | Liste résidence + défaut résidence (settings / flags existants). |
| Autre / vide     | **Compatibilité** : même logique que **résidence** (flows historiques avec slug custom). |

`api/services/registration/service.py` passe `c.binding_slug` à l’enrichissement sur l’écran session courant.

## Backend Submit Validation

Fichier : `api/services/registration/jurisdiction_policy_submit.py`.

- `country_of_residence` → `allow_residence` + `[RESIDENCE_COUNTRY_NOT_ALLOWED]`.
- `nationality` → `allow_nationality` (si au moins une ligne `allow_nationality` pour la juridiction) + `[NATIONALITY_COUNTRY_NOT_ALLOWED]`.
- Autre slug → **résidence** (même message résidence), aligné sur l’enrichissement legacy.

## Admin UI Changes

- **`/admin/jurisdiction-policies/[code]`** : colonne **Nationality**, toggle `allow_nationality` ; sauvegarde via PATCH `/countries` ; texte d’aide résidence vs nationalité.
- **Liste policies** : compteur **`nationality_country_count`**.
- **Flow editor** (`Jurisdiction policy in use`) : affichage **Nationality countries** (lecture seule).
- **Page registration flows** : même compteur dans le résumé carte flow.

## Tests Added

Fichier : `api/tests/test_registration_jurisdiction_country_policies.py` (réécrit avec suffixes de juridiction uniques par test pour éviter la pollution DB).

- Listes **nationalité ≠ résidence** (EU avec US en nationalité seule ; UAE avec FR en nationalité seule).
- Enrichissement `nationality` vs `country_of_residence` pour UAE.
- Submit : nationalité FR acceptée UAE ; nationalité US refusée UAE ; résidence US refusée EU, nationalité US acceptée EU.
- Admin : détail expose `allow_nationality` ; PATCH persiste `allow_nationality`.

**Prérequis** : `alembic upgrade head` jusqu’à **102** (colonne `allow_nationality`). Sans cela, les tests sont **skippés**.

## Remaining Gaps / Next Steps

- **`is_default_nationality`** et réglage global type `default_nationality_iso2` si le produit veut un défaut métier explicite.
- **Presets** serveur : `uae_explicit` ne recrée pas automatiquement toutes les lignes « nationalité annuaire » ; après un preset minimal, réappliquer une stratégie d’élargissement ou utiliser l’admin.
- **Prévisualisation admin** du flow (`_serialize_screen` sans enrichissement juridictionnel) peut ne pas refléter les listes runtime ; inchangé dans ce chantier.
- **Pays hors `country_directory`** : pas de ligne policy possible tant que l’annuaire n’est pas étendu.

## Compatibilité avec les flows existants

- Bindings **`country_of_residence`** et **`nationality`** sur `country_picker` : comportement ciblé et aligné submit/runtime.
- Autres slugs : inchangés côté liste (toujours filtrés comme **résidence** si policies résidence présentes).
- Flutter : aucune règle juridiction codée en dur ; consommation inchangée des clés **`allowed_countries`** / **`default_country`** (renommage interne du helper : `_allowedCountryPickerOptions`).
