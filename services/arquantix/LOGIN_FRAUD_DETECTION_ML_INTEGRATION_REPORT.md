# LOGIN_FRAUD_DETECTION_ML_INTEGRATION_REPORT

## Executive Summary

Un pipeline **login / refresh** complète le scoring fraude existant : extraction de **features dédiées** (`login_fraud_features.py`), évaluation **hybride** (ML baseline utilisateur via `predict_user_risk_ml` + **règles vélocité explicites**) dans `login_fraud_evaluator.py`, intégration dans **`issue_fresh_auth_session`** (OTP mobile vérifié, passkeys, mot de passe, etc.) et **`perform_refresh`** (succès session DB). Les événements `auth_security_events` et le **SIEM** portent `login_ml_score`, `login_ml_confidence`, `login_hybrid_score`, `login_fraud_signals`. Le **ML ne remplace pas** les heuristiques : le gate `FRAUD_ML_ENFORCE_MIN_HEURISTIC` et l’absence de patterns critiques **empêchent un blocage dérivé du seul score ML**.

## Feature Extraction

Fichier : `api/services/security/ml/login_fraud_features.py`.

Fonction : `build_login_feature_vector(user_id, session_id=None, device_hash=None, ip=None)` (avec `db` en premier argument).

Features (floats) :

| Clé | Source |
|-----|--------|
| `login_count_1h` / `login_count_24h` | Succès login (OTP mobile, passkey, password) |
| `failed_login_count_1h` | Échecs login / OTP / passkey |
| `new_device_recently` | Profil `auth_user_device_profiles` (nouveau ou < 24 h) |
| `fingerprint_change_recently` | Événements `auth.device.fingerprint_changed` |
| `unique_country_count_24h` | Metadata `geo_country` / `country` + `last_country` profils |
| `unique_ip_count_24h` | IPs distinctes sur événements |
| `unique_device_count_24h` | `device_id` distincts |
| `refresh_velocity` | `auth.refresh.succeeded` sur 1 h |
| `session_velocity` | Créations `auth_sessions` sur 1 h |
| `device_reputation_score` | `auth_device_reputation.global_risk_score` |
| `global_risk_score` | `auth_global_risk_score.score` |
| `attestation_fail_recently` | `auth.device.attestation_failed` |
| `step_up_events_recently` | `auth.security.action.step_up` (plafonné) |
| `otp_fail_then_success_new_device` | OTP échec puis succès sur device différent (1 h) |

## Login Fraud Evaluation

Fichier : `api/services/security/ml/login_fraud_evaluator.py`.

- `evaluate_login_fraud_risk(db, user_id, device_hash=..., ip=..., session_id=...)`
- `evaluate_refresh_fraud_risk(...)` — même moteur avec `flow="refresh"` (session_id réservé pour corrélation future).

Retour structuré : `ml_score`, `confidence`, `top_features`, `hybrid_score`, `recommendation` (`allow` | `step_up` | `review` | `block`), `pattern_signals`, `heuristic_score`, `ml_enforce_gate`, `deterministic_block_eligible`, etc.

- **ML** : `predict_user_risk_ml` (feature store global existant — pas de rupture de modèle).
- **Hybride** : `LOGIN_FRAUD_PATTERN_WEIGHT` (défaut 0,45) mélange ML et risque pattern ; si l’heuristique globale est **sous le gate**, l’hybride est **atténué** pour éviter une surestimation pilotée par le ML seul.
- **Step-up** : `merge_step_up_from_login_fraud` renforce `step_up_otp_required` seulement si reco + seuils cohérents avec le gate.

Flag : `LOGIN_FRAUD_ML_EVALUATION_ENABLED` (défaut `true`).

## Flow Integration

- **`issue_fresh_auth_session`** (`refresh_session.py`) : après stratégie login / réputation, résolution `device_hash` (y compris si seule l’évaluation fraude nécessite le hash), évaluation, fusion step-up, métadonnées dans l’événement de succès (OTP, passkey, password).
- **`perform_refresh`** : avant `auth.refresh.succeeded`, évaluation refresh, fusion step-up sur la session, enrichissement metadata.

Aucun remplacement des garde-fous existants (réputation device, stratégie login, attestation, etc.).

## Velocity / Pattern Rules

Implémentées dans `evaluate_pattern_rules` — chaque signal inclut `code`, `severity`, `detail`, `source: heuristic_pattern` :

- Volume login 1 h (seuils 5 / 8).
- Nouveau device + plusieurs pays / 24 h.
- Nombre élevé de devices distincts / 24 h.
- Rafales refresh (seuils 15 / 25 / 1 h).
- Chaîne OTP échec → succès sur autre device.
- Pic d’échecs login / 1 h.

## SIEM Enrichment

Fichier : `security_event_pipeline.py`.

- `normalize_security_metadata` : coercition `login_ml_score`, `login_ml_confidence`, `login_hybrid_score`, `login_fraud_signals`.
- `build_sink_payload` : champs top-level pour export normalisé.

Logs applicatifs : `logger.info` dans l’évaluateur (`arquantix.security.ml.login_fraud_eval`) avec `user_id`, `flow`, `recommendation`, `hybrid`, `signals` (sans données sensibles).

## Feedback Loop (préparation)

Chemin cible documenté :

1. **Event** : `auth_security_events` (+ payload SIEM avec `login_*`).
2. **Signal** : `pattern_signals` + scores ML / hybrides.
3. **Label** : table ou outil analyste (`fraud` / `safe`, `source=analyst`) — *non implémenté dans ce lot* ; réutiliser / étendre `fraud_ml_training_pipeline` pour ingérer des labels.
4. **Training** : `fraud_ml_training_pipeline` + `train_model` (`fraud_ml_model.py`) sur jeux alignés `FEATURE_KEYS` ; les features login-spécifiques peuvent alimenter un **second modèle** ou des colonnes dérivées après export batch.

## Tests

Fichier : `api/tests/test_login_fraud_ml_integration.py`.

- Pattern login « normal » (comptages).
- Nouveau device + pays multiples → patterns détectés.
- ML désactivé → fallback sans exception.
- Garde-fou : heuristique basse + ML élevé → pas de `block` déterministe.
- SIEM : payload contient les champs `login_*`.

## Remaining Gaps

- **Blocage HTTP** : la reco `block` n’est pas mappée vers un 403 automatique (éviter conflit avec produit) ; `deterministic_block_eligible` est exposé pour une politique future.
- **Labels analyste** : pas de table dédiée ni d’API d’ingestion dans ce lot.
- **Corrélation refresh par `session_id`** : le champ est réservé ; les métadonnées refresh ne portent pas encore `session_id` systématiquement.
- **Modèle ML login-dédié** : l’inférence réutilise le vecteur global ; un modèle entraîné sur le sous-vecteur login pourrait améliorer la précision.
- **Mise à jour explicite `auth_global_risk_score` au login** : non forcée ici ; le **response engine** continue de recalculer sur événements suivants (`recompute_user_risk_and_enforce`).
