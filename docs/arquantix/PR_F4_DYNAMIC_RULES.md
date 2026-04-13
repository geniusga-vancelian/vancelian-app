# PR F.4 — Rule engine dynamique

## Objectif

Règles **configurables en base** (`auth_risk_rules`) avec conditions JSON, priorité et action — évaluées **avant** les règles statiques PR F.2.

## Activation

- `DEVICE_RISK_ENABLE_DYNAMIC_RULES=true`
- Migration **138** (table + seed aligné sur les 4 règles historiques PR F.2)

Si le flag est **false** : comportement inchangé ; les règles **statiques** PR F.2 s’appliquent lorsque `DEVICE_RISK_ENABLE_COMBINATION_RULES=true`.

Si le flag est **true** et **aucune** ligne active : retour au pipeline **statique** (même logique que « pas de match dynamique »).

## Schéma `auth_risk_rules`

| Colonne | Rôle |
|---------|------|
| `id` | UUID |
| `name` | Libellé (logs / audit) |
| `priority` | Entier croissant : **la plus petite valeur est évaluée en premier** |
| `conditions` | JSON (voir DSL) |
| `action` | `BLOCK`, `STEP_UP`, `ALLOW` |
| `enabled` | Activer / désactiver sans supprimer |

## DSL conditions

- Liste de signaux : chaîne = nom de signal booléen (voir `combination_rule_signals` dans `device_risk_engine_pr_f2.py`).
- `{"all": ["new_device", "country_changed"]}` — ET logique.
- `{"any": ["a", "b"]}` — OU.
- `{"not": "signal"}` ou `{"not": {"all": [...]}}` — négation.

Signaux disponibles : `new_device`, `country_changed`, `ip_changed`, `attestation_low`, `high_velocity`, `device_churn_and_velocity`.

## Ordre d’exécution (`evaluate_pr_f_for_request`)

1. **PR F.4** — `evaluate_dynamic_rules` (premier match)
2. **PR F.2** — `evaluate_combination_rules` (si pas de court-circuit dynamique)
3. Baseline F.2 / F.3, score, seuils

## Action `ALLOW`

Une règle qui matche avec `ALLOW` **ne court-circuite pas** (pas de blocage / step-up) : le pipeline continue (scores + règles statiques si activées).

## Seed (migration 138)

Quatre règles équivalentes aux combinaisons codées historiques ; tu peux les désactiver, les dupliquer ou les affiner en SQL sans redéployer le code.

## Tests

`tests/test_device_risk_dynamic_rules.py`
