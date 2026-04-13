# PR F.3 — Baseline avancée (temporel + comportemental)

## Objectif

Détecter des schémas **lents** ou **mimétiques** en comparant la session courante à une baseline apprise (Welford + historique d’actions).

## Prérequis

- `DEVICE_RISK_ENGINE_PR_F_ENABLED=true`
- `DEVICE_RISK_ENABLE_ADVANCED_BASELINE=true`

Optionnel mais recommandé avec F.2 : `DEVICE_RISK_ENABLE_BASELINE=true` pour pays/IP ; le compteur d’observations est partagé.

## Données persistées (migration 137)

Colonnes sur `auth_user_risk_baselines` :

- `avg_hour_of_day`, `std_hour_of_day`
- `avg_weekday`, `std_weekday`
- `avg_session_duration_sec`, `std_session_duration_sec`
- `last_10_actions_types` (JSON, max 10)
- `temporal_welford_json` — état Welford interne (heure, weekday, durée session)
- `actions_per_hour_ema` (existant) — comparé à la vélocité courante

## Signaux dans le contexte (`RiskEvaluationContext`)

- `current_hour_utc`, `weekday_utc` (UTC)
- `session_duration_sec` — `now - session.created_at`
- `action_type` — dérivé du chemin (`infer_risk_action_type`)

## Scoring

`baseline_temporal_anomaly_score` ajoute une pénalité bornée (max 55 pts cumulés) multipliée par `DEVICE_RISK_BASELINE_TIME_WEIGHT`.

Raisons possibles :

- `baseline_time_anomaly`
- `baseline_weekday_anomaly`
- `baseline_session_duration_anomaly`
- `baseline_behavior_anomaly` (vélocité ou type d’action rare)

Seuil d’apprentissage : `DEVICE_RISK_ADVANCED_BASELINE_MIN_SAMPLES` (défaut 8).

## Mise à jour

Uniquement après décision **ALLOW** : `update_advanced_baseline_from_observation` (avec `increment_sample_count` pour éviter double comptage si F.2 actif).

## Rétrocompatibilité

`DEVICE_RISK_ENABLE_ADVANCED_BASELINE=false` → aucun effet (pas de requête métier supplémentaire hors chemin PR F existant).
