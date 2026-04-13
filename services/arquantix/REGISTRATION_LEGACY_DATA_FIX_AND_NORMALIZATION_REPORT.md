# Registration Legacy Data Fix & Normalization

## Executive Summary

Une couche dédiée **`legacy_normalization.py`** classe chaque `registration_screen_component` en **OK**, **auto-fixable** ou **ambigu (revue manuelle)**, puis applique uniquement les corrections sûres : liaison `field_definition_id` par `binding_slug` unique (après normalisation), réalignement du `binding_slug` sur le slug canonique du field déjà lié, et nettoyage des champs parasites sur les composants **content**. Aucune suppression de ligne. Mode **dry-run** et **apply** (transaction unique + rollback si erreur). Un script CLI et des endpoints admin exposent le même comportement.

## Legacy Data Categories

| Catégorie | Critères (résumé) |
|-----------|-------------------|
| **OK** | Content sans `binding_slug` ni `field_definition_id` ; ou field-bound avec `field_definition_id` + `binding_slug` équivalent au slug du field (kebab/snake/casse ignorés). |
| **Auto-fixable** | Content avec binding ou field def ; field-bound avec binding seul et **exactement un** field definition après `normalize_slug` ; field-bound avec `field_definition_id` valide mais binding non équivalent → canonique = `field.slug`. |
| **Ambiguous** | `component_type` inconnu ; field-bound sans binding et sans FD ; binding sans match ; **plusieurs** field definitions pour la même clé normalisée ; `field_definition_id` orphelin. |

## Normalization Rules

Fonctions publiques :

- **`normalize_slug(value)`** — minuscule, `-` → `_`, trim.
- **`are_field_slugs_equivalent(a, b)`** — comparaison sur forme normalisée.
- **`classify_component_legacy_state(...)`** — logique pure (tests unitaires).
- **`load_field_definition_indexes(db)`** — index slug normalisé → liste de `FieldDefinition` (détection des doublons sémantiques).

Familles de types : **`INPUT_COMPONENT_TYPES`** et **`CONTENT_COMPONENT_TYPES`** importées depuis **`governance.py`** (pas de duplication).

## Dry Run Results

À produire sur chaque environnement avant apply :

```bash
cd services/arquantix/api
python3 scripts/run_registration_legacy_normalization.py
# ou
python3 scripts/run_registration_legacy_normalization.py --json-out /tmp/reg_legacy_report.json
```

Réponse JSON : `totals`, listes `ok`, `auto_fixable`, `ambiguous`, `health_before`, `applied` vide, `health_after` = `health_before` en dry-run via `apply_auto_fixes(dry_run=True)`.

**GET** `/api/admin/registration/legacy-normalization/report` — diagnostic (même classification, `health_after` null).

**POST** `/api/admin/registration/legacy-normalization/dry-run` — aligné sur le pipeline apply sans écriture.

## Applied Fixes

Apply :

```bash
python3 scripts/run_registration_legacy_normalization.py --apply
```

**POST** `/api/admin/registration/legacy-normalization/apply` avec body `{"confirm": true}` (sinon **400**).

Chaque ligne appliquée est loggée via **`logger.info("legacy_normalization", {...})`** avec : `component_id`, `screen_id`, `flow_id`, action, anciens / nouveaux `binding_slug` et `field_definition_id`, timestamp.

## Remaining Manual Review Cases

Liste **`ambiguous`** du rapport : à traiter au cas par cas (création de field definition, correction de type, suppression manuelle de données incohérentes, etc.). L’outil ne devine pas lorsque plusieurs fields correspondent à un même slug normalisé.

## Health Check Before / After

- **`health_before`** / **`health_after`** : pour chaque flow, `can_publish`, `error_count`, `warning_count`.
- **`diagnose_registration_components`** inclut seulement **`health_before`**.
- Après **`--apply`**, comparer `publishable` / `blocked` sur l’ensemble des flows pour mesurer le gain.

## Tests Added

- **`tests/test_registration_legacy_normalization.py`** : slugs, équivalence, classification (content, link, canonical, ambiguïtés), apply content cleanup, apply + **`check_flow_health`** publishable, diagnose totals.
- **`tests/test_registration_api.py`** : GET report, POST apply sans `confirm`.

## Rollback / Safety Notes

- Un seul **`commit`** après toutes les mises à jour ; en cas d’exception, **`rollback`** et liste **`errors`** dans le résultat.
- Champs modifiés : **`binding_slug`**, **`field_definition_id`** uniquement.
- Pas de DELETE ; pas de correction des cas **ambiguous**.
- Les endpoints admin suivent le même niveau de protection que le reste de `/api/admin/registration` (en production, restreindre l’accès réseau / auth selon votre politique).
- Optionnel : conserver le fichier **`--json-out`** comme snapshot « before » avant `--apply », puis régénérer un rapport « after ».

## Fichiers livrés

| Fichier | Rôle |
|---------|------|
| `api/services/registration/legacy_normalization.py` | Service |
| `api/services/registration/legacy_normalization_analysis.py` | Analyse JSON, validation, delta, résumé MD |
| `api/scripts/run_registration_legacy_normalization.py` | CLI (dry-run, `analyze`, `validate`, `apply`, `delta`) |
| `api/services/registration/admin_router.py` | Routes `legacy-normalization/*` |
| `REGISTRATION_LEGACY_NORMALIZATION_RUNBOOK.md` | Orchestration sécurisée en 4 étapes |

Les compteurs exacts (**nombre total analysé**, **auto-fixés**, **content nettoyés**, **non résolus**, **flows réparés**) dépendent de la base cible : les obtenir en exécutant le script ou l’endpoint sur cet environnement.

Le fichier **`REGISTRATION_LEGACY_NORMALIZATION_EXECUTION_SUMMARY.md`** se génère avec la sous-commande `delta --write-summary` (voir runbook), pas à commiter tel quel s’il contient des données sensibles.
