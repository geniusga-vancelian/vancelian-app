# Registration field catalog completion & binding alignment

## Executive Summary

Les **10** composants classés `ambiguous` par le dry-run legacy normalization (référence initiale : **7** `no_field_definition_for_binding`, **3** `field_bound_missing_binding_and_fd`) ont été traités **sans** exécuter d’`apply` de normalisation legacy.

- **Migration `092`** : ajout des `field_definitions` manquantes pour les bindings réels des seeds **085** / **087**, alignement sur la convention catalogue **kebab-case** (`replace(binding_slug, '_', '-') = fd.slug`, comme en **088**), backfill `field_definition_id`, et réparation des orphelins dont la clé métier est déductible (`component_key` stable type seed).
- **Migration `093`** : réparation des **3** entrées restantes avec `component_key` auto-généré (`phone_input_*`, `checkbox_*`, `date_picker_*`) en leur assignant un binding canonique **uniquement si** le même `binding_slug` n’existe pas déjà sur l’écran (évite les doublons destructeurs).

Le fichier maître `api/data/field_definitions_master.csv` a été enrichi pour refléter les nouveaux slugs (référence hors-DB).

**Convention documentée** : en base, le slug du catalogue reste en **kebab-case** (`annual-income-range`). Les **bindings runtime** dans `registration_screen_components.binding_slug` restent en **snake_case** (`annual_income_range`). La fonction `normalize_slug()` de `legacy_normalization.py` les considère comme **équivalents** ; pas de renommage des clés `profile_json` existantes pour les champs concernés.

---

## Ambiguous Cases Inventory

Inventaire logique (référence dry-run **avant** correctif, 49 composants, flows seeds EU / UAE + EU vertical slice + données de test locales).

| # | component_id (ex.) | flow_name | screen (logique) | component_type | component_key (observé) | binding_slug | reason_code | Proposition de correction |
|---|-------------------|-----------|------------------|----------------|-------------------------|--------------|-------------|---------------------------|
| 1–2 | (EU + UAE) | EU / UAE Individual Onboarding v1 | professional_form | select | income_range | annual_income_range | no_field_definition_for_binding | FD `annual-income-range` + lien FK |
| 3–4 | (EU + UAE) | idem | risk_form | multi_select | asset_classes | known_asset_classes | no_field_definition_for_binding | FD `known-asset-classes` + lien FK |
| 5–6 | (EU + UAE) | idem | consent_form | checkbox | terms_accepted | terms_accepted | no_field_definition_for_binding | FD `terms-accepted` (≠ `terms-and-conditions-accepted`, autre clé normalisée) |
| 7–8 | (EU + UAE) | idem | residence_form | country_picker | country | country_of_residence | no_field_definition_for_binding | FD `country-of-residence` (aligné `slug_aliases.json`) |
| 9 | EU Individual Registration v1 (087) | consent | checkbox | terms_and_conditions | terms_and_conditions | no_field_definition_for_binding | FD `terms-and-conditions` |
| 10 | idem | consent | checkbox | privacy_policy | privacy_policy | no_field_definition_for_binding | FD `privacy-policy` |
| 11–12 | EU Onboarding (données locales) | divers | phone_input / checkbox / date_picker | `phone_input_*` / `checkbox_*` / `date_picker_*` | null | field_bound_missing_binding_and_fd | Heuristique **093** (binding + FD si pas de conflit sur l’écran) |

*Les `component_id` exacts dépendent de la base ; le JSON de sortie `/tmp/reg_dry_after_catalog_fix.json` reflète l’état **après** migrations.*

---

## New Field Definitions Added

Insérées par **092** si absentes (`WHERE NOT EXISTS` sur `slug`) :

| Slug (catalogue) | ui_label (schéma) | field_type | component_type_default | required_default | category | options_json |
|------------------|-------------------|------------|-------------------------|------------------|----------|--------------|
| country-of-residence | Country of residence | string | country_picker | true | address | — |
| annual-income-range | Annual income range | enum | select | true | financial | options alignées seed 085 |
| known-asset-classes | Asset classes you have invested in | array | multi_select | false | knowledge | options alignées seed 085 |
| terms-accepted | I accept the Terms of Service and Privacy Policy | boolean | checkbox | true | consents | — |
| terms-and-conditions | I accept the Terms and Conditions | boolean | checkbox | true | consents | — |
| privacy-policy | I accept the Privacy Policy | boolean | checkbox | true | consents | — |

**Décision `terms_accepted` vs `terms-and-conditions-accepted`** : le catalogue contenait déjà `terms-and-conditions-accepted` (normalisé `terms_and_conditions_accepted`), distinct de `terms_accepted` → **nouveau** slug `terms-accepted` pour préserver la sémantique et la clé métier du seed 085 sans casser les profils existants.

**Décision `privacy_policy` vs `privacy-policy-accepted`** : même logique de clé normalisée différente → slug **`privacy-policy`** pour le binding `privacy_policy`.

---

## Existing Bindings Realigned

Aucun **UPDATE** de `binding_slug` sur les seeds **085** / **087** pour les champs listés ci-dessus : les bindings **snake_case** ont été **conservés** ; seul le **catalogue** et le **FK** ont été complétés.

Les orphelins avec `component_key` seed-like reçoivent un `binding_slug` snake_case cohérent avec la migration **092** (table `fixes`).

---

## Orphan Inputs Fixed

1. **092** — `component_key` connus (`first_name`, `employer`, `employment`, …) : `binding_slug` + `field_definition_id` renseignés.
2. **093** — clés auto-générées `phone_input_[a-z0-9]+`, `checkbox_[a-z0-9]+`, `date_picker_[a-z0-9]+` : respectivement `phone_number` / `terms_accepted` / `date_of_birth` + FK, **sauf** si le binding est déjà pris sur le même `screen_id`.

---

## Naming Canonicalization Decisions

| Alias / variante | Slug catalogue (vérité DB) | Binding runtime (composant) | Normalisé commun |
|------------------|----------------------------|-----------------------------|------------------|
| — | `annual-income-range` | `annual_income_range` | `annual_income_range` |
| — | `known-asset-classes` | `known_asset_classes` | `known_asset_classes` |
| `terms-and-conditions-accepted` (existant) | reste pour autres parcours | — | `terms_and_conditions_accepted` |
| Seed EU/UAE combiné | **`terms-accepted`** | `terms_accepted` | `terms_accepted` |
| EU_VS | **`terms-and-conditions`** | `terms_and_conditions` | `terms_and_conditions` |
| EU_VS | **`privacy-policy`** | `privacy_policy` | `privacy_policy` |
| `residency-country` (existant) | inchangé | — | `residency_country` |
| Seed résidence | **`country-of-residence`** | `country_of_residence` | `country_of_residence` |

---

## Dry-Run / Analyze / Validate Results After Fix

Commandes exécutées (environnement local après `alembic upgrade head`) :

```bash
python3 scripts/run_registration_legacy_normalization.py --json-out /tmp/reg_dry_after_catalog_fix.json
python3 scripts/run_registration_legacy_normalization.py analyze /tmp/reg_dry_after_catalog_fix.json
python3 scripts/run_registration_legacy_normalization.py validate /tmp/reg_dry_after_catalog_fix.json
```

### Before / after (métriques legacy normalization)

| Métrique | Avant (réf. demande) | Après (local post-092+093) |
|----------|----------------------|----------------------------|
| total | 49 | 49 |
| ok | 39 | 49 |
| auto_fixable | 0 | 0 |
| ambiguous | 10 | 0 |
| Top `no_field_definition_for_binding` | 7 | 0 |
| Top `field_bound_missing_binding_and_fd` | 3 | 0 |

### Santé flux (`health_before` dans le rapport)

| | Avant (typique) | Après |
|--|-----------------|-------|
| publishable | 3 / 4 | 3 / 4 |
| blocked | 1 | 1 |

`validate` : **OK** (seuil d’ambiguïté respecté ; 0 % de composants ambigus).

**Note** : `auto_fixable` reste à **0** car les corrections ont été **appliquées par migrations SQL** (FK + bindings), pas par le job `apply_auto_fixes` qui ne voit plus de lignes à corriger.

---

## Remaining Gaps

- Le flux **EU Individual Onboarding v1** peut rester **non publishable** pour d’autres raisons (ex. erreurs gouvernance i18n / règles), **indépendantes** de la classification legacy normalization.
- Les composants **093** réparés par heuristique (`terms_accepted` pour `checkbox_*`) supposent un **doublon accidentel** de case à cocher ; un audit produit sur ces écrans est recommandé.
- **`privacy-policy`** vs **`privacy-policy-accepted`** coexistent dans le catalogue CSV : sens proches mais **clés normalisées différentes** ; ne pas fusionner sans migration de données profil.

---

## Recommendation: Is Apply Safe Now?

- **Gate `validate`** sur le dry-run : **oui**, le rapport local est vert (0 ambigu).
- **Apply legacy normalization** : **non nécessaire** pour lever les ambiguïtés traitées ici (déjà résolu en base). Ne lancer un **`apply`** que si vous voulez traiter d’**autres** catégories (`content_has_binding_or_field_def`, `binding_mismatch_with_linked_field`, etc.) après un nouveau dry-run.
- **Apply « safe » au sens métier** : les migrations **092** / **093** sont **additives** (INSERT conditionnel + UPDATE ciblé) ; pas de suppression de lignes. Vérifier en **staging** les écrans concernés et les parcours Flutter.

---

## Fichiers touchés

- `api/alembic/versions/092_field_definitions_registration_catalog_completion.py`
- `api/alembic/versions/093_fix_registration_autokey_orphan_components.py`
- `api/data/field_definitions_master.csv`
- `api/tests/test_registration_field_catalog_alignment.py`

---

## Références

- `REGISTRATION_LEGACY_NORMALIZATION_RUNBOOK.md`
- `api/services/registration/legacy_normalization.py`
- `api/services/ai_jurisdiction_configs/slug_aliases.json` (`country_of_residence` → `country-of-residence`)
