# Rapport — moteur de scoring fraude ML (Tier 1)

## Objectif

Couche **Machine Learning** au-dessus du SIEM et du moteur de risque existants pour repérer des schémas non couverts par les heuristiques, enrichir le score utilisateur et permettre un **cycle de retraining** (batch + versioning).

## Architecture

| Composant | Fichier | Rôle |
|-----------|---------|------|
| Feature store | `api/services/security/ml/fraud_feature_store.py` | `build_feature_vector(db, user_id)` → `Dict[str, float]` |
| Modèle | `api/services/security/ml/fraud_ml_model.py` | `train_model`, `predict` — RandomForest (baseline) ou IsolationForest (anomalie) |
| Stockage | `api/services/security/ml/model_storage.py` | Répertoire local versionné + manifest ; upload S3 optionnel (`FRAUD_ML_S3_BUCKET`, `FRAUD_ML_S3_PREFIX`) |
| Inférence | `api/services/security/fraud_ml_inference_service.py` | Orchestration + fallback |
| Entraînement | `api/services/security/fraud_ml_training_pipeline.py` | Dataset depuis `auth_security_events`, labels HIGH/CRITICAL via `assess_user_risk` |
| Scoring hybride | `api/services/security/security_response_engine.py` | `compute_global_risk_score_with_detail` |
| Admin | `api/services/security/ml/fraud_ml_admin_routes.py` | `GET /admin/security/ml/model`, `GET /admin/security/ml/predict/{user_id}` |

## Features (ordre fixe `FEATURE_KEYS`)

- `login_count_24h`, `login_count_7d`
- `unique_ip_count_24h`, `unique_device_count_7d`
- `avg_session_duration`, `refresh_rate_per_hour`
- `failed_login_ratio`, `geo_distance_variance`, `time_of_day_entropy`
- `device_trust_distribution`, `historical_risk_score_avg`, `historical_risk_score_max`

## Scoring hybride

- Formule : `hybrid = (1 - ML_WEIGHT) * heuristic + ML_WEIGHT * ml_score` (défaut **ML_WEIGHT=0.4** → 60 % / 40 %).
- **Sécurité** : si `heuristic < FRAUD_ML_ENFORCE_MIN_HEURISTIC` (défaut **45**), le score **appliqué** aux actions automatiques (OTP, révocation, lock) reste **l’heuristique seule** — le ML ne peut pas à lui seul faire monter le risque opérationnel.
- Si le modèle est absent ou l’inférence désactivée : **fallback** → pas de contribution ML (`hybrid = heuristic`).

## Variables d’environnement (principales)

| Variable | Description |
|----------|-------------|
| `ML_WEIGHT` | Poids du ML dans le blend (0–1), défaut `0.4` |
| `FRAUD_ML_ENFORCE_MIN_HEURISTIC` | Seuil heuristique pour autoriser le blend en enforcement |
| `FRAUD_ML_INFERENCE_ENABLED` | `true` / `false` |
| `FRAUD_ML_MODEL_DIR` | Répertoire des versions (défaut `data/fraud_ml_models` sous `api/`) |
| `FRAUD_ML_MODEL_KIND` | `random_forest` ou `isolation_forest` |
| `FRAUD_ML_MIN_SAMPLES` | Minimum d’échantillons pour `run_batch_retraining` (défaut 20) |
| `FRAUD_ML_S3_BUCKET` / `FRAUD_ML_S3_PREFIX` | Optionnel : synchronisation du dernier artefact |

## Retraining

- Appeler `run_batch_retraining(db, since_days=30)` depuis un job planifié ou un script interne (seuil `FRAUD_ML_MIN_SAMPLES`).
- Chaque run produit une **nouvelle version** (UUID ou `FRAUD_ML_TRAIN_VERSION`), écrit `manifest.json` + `model.joblib`, met à jour `LATEST`, vide le cache mémoire du modèle.

## Dépendances

- `scikit-learn`, `joblib` (voir `api/requirements.txt`).

## Tests

- `api/tests/test_fraud_ml_engine.py` : cohérence des clés features, formule hybride, fallback, garde-fou enforcement, stabilité RF sur même entrée.

## Limites Tier 1

- Pas de serving temps réel séparé (inférence in-process).
- Stockage Binaire DB non implémenté (local + S3 optionnel).
- Labels d’entraînement proxy (heuristique) — à affiner avec des cas frauduleux étiquetés métier.
