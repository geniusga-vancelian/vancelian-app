# Phase 5F — Calibration & apprentissage (boucle de feedback déterministe + A/B)

## Objectif

Introduire une **boucle de feedback** et une **couche de configuration** pour le moteur de risque (5C/5D/5E), **sans ML**, **sans second moteur**, **sans application automatique** des changements de poids.

## Modules

| Fichier | Rôle |
|---------|------|
| `api/services/security/risk_feedback.py` | Modèle `RiskFeedback`, `record_risk_feedback` → logs structurés |
| `api/services/security/risk_calibration.py` | `CalibrationSuggestion`, `compute_calibration_suggestions` (suggestions uniquement) |
| `api/services/security/risk_config.py` | `DEFAULT_RISK_WEIGHTS`, `get_risk_weight`, surcharges env, A/B via `runtime_weight_overrides` |
| `api/services/security/risk_experiments.py` | `assign_variant` (hash déterministe), `load_variant_weight_overrides` |

## Types de feedback (`RiskFeedback`)

- `fraud_confirmed`, `fraud_suspected`, `false_positive`, `successful_action`, `manual_override`
- Champs : `action_key`, `user_id`, `risk_score`, `risk_level`, `decision`, `outcome`, `feedback_type`, `metadata`, **`factor_codes`** (codes de facteurs présents lors de l’évaluation)

`record_risk_feedback` journalise un événement `risk_feedback.recorded` avec `user_id` haché (16 caractères), pas d’écriture DB implicite.

## Calibration (suggestions uniquement)

`compute_calibration_suggestions(feedbacks)` :

- Compte, par code de facteur, les feedbacks **fraude** vs **faux positifs** (sur les entrées qui listent ce facteur dans `factor_codes`).
- Règles déterministes (seuils min d’échantillon, pas de modèle statistique noir) :
  - forte proportion de **fraude** associée au facteur → suggestion d’**augmenter** le poids ;
  - forte proportion de **faux positifs** → suggestion de **réduire** le poids.

Les sorties sont des **`CalibrationSuggestion`** (poids actuel vs suggéré, `confidence`, `reason`). **Aucune** mise à jour automatique des poids en production : revue humaine + mise à jour de config / env.

## Configuration des poids

- Dictionnaire de référence : `DEFAULT_RISK_WEIGHTS` dans `risk_config.py` (clés logiques : `device_new`, `geo_velocity_30min`, `segment_adjustment_trusted_user`, etc.).
- Surcharges :
  - `RISK_WEIGHTS_JSON` = objet JSON `{ "device_new": 22, ... }`
  - `RISK_WEIGHT_<KEY>` (ex. `RISK_WEIGHT_DEVICE_NEW=18` → clé `device_new`)
- `RISK_CALIBRATION_VERSION` : chaîne libre pour traçabilité (exposée dans `RiskEvaluation.calibration_version` et les logs).

Le moteur (`risk_engine.py`) lit les poids comportementaux via **`get_risk_weight`** pour les branches concernées (géo, appareil, rafales, sessions, âge de compte, login, bonus stabilité géo, ajustements de segment 5E).

## A/B testing (déterministe)

- Flag : `RISK_EXPERIMENTS_ENABLED=true`
- `RISK_EXPERIMENT_ID` : identifiant d’expérience (non secret)
- Assignation : `assign_variant(user_id, experiment_id)` via `sha256(experiment_id:user_id)` — stable pour un couple (utilisateur, expérience).
- Poids de la variante : `RISK_EXPERIMENT_VARIANT_A_WEIGHTS_JSON` (JSON) ou `RISK_EXPERIMENT_<SANITIZED_ID>_VARIANT_A_WEIGHTS_JSON` (voir `risk_experiments.py`).
- Application : `runtime_weight_overrides` autour du corps d’`evaluate_request_risk` (ContextVar — sûr en async).

**Contrôle** : pas d’`experiment_id` utilisateur ou expérience désactivée → branche `control`, pas d’override.

## Observabilité

`RiskEvaluation` et logs `continuous_auth.risk_evaluated` enrichis :

- `experiment_id`, `variant`, `calibration_version`
- `risk_weights_effective_sample` : extrait trié des poids effectifs (aperçu, pas la liste complète si très grande)

`ContinuousAuthDecision` reprend `experiment_id`, `variant`, `calibration_version` via `_merge_risk_into_decision`.

## Sécurité / gouvernance

- Pas d’auto-application des suggestions de calibration.
- Changements de comportement = **config / env** explicites, versionnés (`RISK_CALIBRATION_VERSION`).
- A/B : répartition modifiable via `RISK_EXPERIMENT_CONTROL_RATIO_PCT` (1–99).

## Tests

`api/tests/test_phase5f_calibration.py` : ingestion feedback, suggestions, A/B, surcharge env, context manager d’overrides.

## Limites

- Pas de stockage persistant des feedbacks dans ce lot (logs uniquement) ; une table dédiée peut s’ajouter sans changer l’API des modèles.
- Les suggestions se basent sur les **`factor_codes` fournis** dans le feedback ; qualité métier = qualité du lien facteur ↔ cas.
