# Phase 2 — Centralisation des flags sécurité (`security_env.py`)

## Inventory

### Avant refactor (cible : services auth / sécurité)

Les occurrences suivantes ont été identifiées comme **flags ou réglages sécurité** lus directement (`os.getenv` / `_truthy` local), hors `security_env.py` :

| Fichier | Variable(s) | Usage | Criticité |
|--------|-------------|--------|-----------|
| `adaptive_auth_orchestrator.py` | `ADAPTIVE_AUTH_*` | Feature flags adaptatif | Haute |
| `session_intelligence_service.py` | `SESSION_INTELLIGENCE_ENABLED`, `SESSION_STEP_UP_ENABLED`, `SESSION_REAUTH_ENABLED` | Intelligence session | Haute |
| `continuous_auth_engine.py` | `CONTINUOUS_AUTH_ENABLED` | Auth continue | Haute |
| `login_auth_strategy_service.py` | `LOGIN_AUTH_STRATEGY_ENABLED`, `LOGIN_STRATEGY_PERSIST_DECISIONS` | Stratégie login | Haute |
| `login_device_trust_service.py` | `LOGIN_DEVICE_TRUST_ENABLED` | Confiance device | Moyenne |
| `security_response_engine.py` | `SECURITY_RESPONSE_ENGINE_ENABLED`, `DEVICE_REPUTATION_RISK_ENGINE_INTEGRATION`, `SECURITY_ACCOUNT_LOCK_HOURS`, `ML_WEIGHT`, `FRAUD_ML_ENFORCE_MIN_HEURISTIC` | Moteur de réponse / blend ML | Haute |
| `security_event_pipeline.py` | `SECURITY_CORRELATION_ON_EMIT`, `SECURITY_RESPONSE_ENGINE_ON_EMIT` | Hooks post-événement | Haute |
| `security_event_sink.py` | `SECURITY_EVENTS_SINK` | Backend SIEM | Moyenne |
| `device_reputation_service.py` | `DEVICE_REPUTATION_ENABLED`, `DEVICE_REPUTATION_CRITICAL_BLOCKS_AUTH` (+ seuils numériques inchangés localement) | Réputation device | Haute |
| `login_fraud_evaluator.py` | `LOGIN_FRAUD_ML_EVALUATION_ENABLED`, `FRAUD_ML_ENFORCE_MIN_HEURISTIC`, `LOGIN_FRAUD_PATTERN_WEIGHT` | Fraude ML login | Haute |
| `fraud_ml_inference_service.py` | `FRAUD_ML_INFERENCE_ENABLED` | Inférence ML | Haute |
| `device_fingerprint.py` | `AUTH_DEVICE_FINGERPRINT_ENABLED` | Empreinte device | Moyenne |
| `passkey_login_eligibility.py` | `PASSKEY_AUTO_*` | Fast lane passkey | Moyenne |
| `auth_bootstrap.py` | `AUTH_RL_BACKEND` | Bootstrap prod / Redis | Haute |
| `security_events_service.py` | `AUTH_SECURITY_EVENTS_ENABLED` | Persistance événements | Haute |

### Restant hors périmètre immédiat (lectures directes encore présentes)

- **WebAuthn / attestation / crypto / providers** : `webauthn_config.py`, `device_attestation_service.py`, `crypto_service.py`, etc.
- **Zero-trust** : `zero_trust/*.py` (`ZERO_TRUST_*`).
- **Infra générale** : `main.py`, `database.py`, `auth.py` (JWT), rate limit adresse, chatbot, etc.
- **Seuils numériques device reputation** : `DEVICE_REPUTATION_*_MIN` encore dans `device_reputation_service.py` (comportement inchangé).

---

## Refactors Applied

- Remplacement des `_truthy` locaux et des `os.getenv` listés ci-dessus par des appels à `services.security.security_env`.
- **`adaptive_auth_orchestrator`** : import des helpers `is_adaptive_*` depuis `security_env` (plus de duplication locale).
- **`session_intelligence_service`** : import `is_session_intelligence_enabled`, `is_session_step_up_enabled`, `is_session_reauth_enabled`.
- **`continuous_auth_engine`** : import `is_continuous_auth_enabled`.
- **`login_auth_strategy_service`** : `is_login_auth_strategy_enabled`, `is_login_strategy_persist_decisions_enabled`.
- **`login_device_trust_service`** : `is_login_device_trust_enabled` depuis `security_env`.
- **`security_response_engine`** : flags + fonctions numériques centralisées (`security_account_lock_hours`, `global_risk_ml_weight`, `fraud_ml_enforce_min_heuristic`).
- **`security_event_pipeline`** : `is_security_correlation_on_emit_enabled`, `is_security_response_engine_on_emit_enabled` ; ré-export de `security_events_sink_name` pour le module de compat `services.auth.security_event_pipeline`.
- **`security_event_sink`** : `security_events_sink_name` déplacé vers `security_env`, import dans le sink.
- **`device_reputation_service`** : `is_device_reputation_enabled`, `is_device_reputation_critical_blocks_auth_enabled`.
- **`login_fraud_evaluator`** : délégation vers `is_login_fraud_ml_evaluation_enabled` et helpers numériques.
- **`fraud_ml_inference_service`** : `is_fraud_ml_inference_enabled`.
- **`device_fingerprint`** : `is_auth_device_fingerprint_enabled` (alias public inchangé `is_device_fingerprint_enabled`).
- **`passkey_login_eligibility`** : `is_passkey_auto_trigger_enabled`, `passkey_auto_max_login_risk`, `is_passkey_auto_expose_login_email_enabled`.
- **`auth_bootstrap`** : `auth_rate_limit_backend_for_bootstrap()` (défaut vide si absent — **sémantique historique conservée**).
- **`security_events_service`** : `is_security_events_enabled` importé depuis `security_env` (même sémantique `_env_not_falsy` / opt-out).

---

## Helpers Added (`security_env.py`)

| Helper | Variable / logique |
|--------|---------------------|
| `is_adaptive_passkey_auto_enabled` | `ADAPTIVE_AUTH_PASSKEY_AUTO` |
| `is_adaptive_block_high_risk_enabled` | `ADAPTIVE_AUTH_BLOCK_HIGH_RISK` |
| `is_adaptive_email_fallback_enabled` | `ADAPTIVE_AUTH_EMAIL_FALLBACK` |
| `is_session_step_up_enabled` | `SESSION_STEP_UP_ENABLED` |
| `is_session_reauth_enabled` | `SESSION_REAUTH_ENABLED` |
| `is_login_strategy_persist_decisions_enabled` | `LOGIN_STRATEGY_PERSIST_DECISIONS` |
| `is_security_response_engine_enabled` | `SECURITY_RESPONSE_ENGINE_ENABLED` |
| `is_device_reputation_risk_engine_integration_enabled` | `DEVICE_REPUTATION_RISK_ENGINE_INTEGRATION` |
| `is_security_correlation_on_emit_enabled` | `SECURITY_CORRELATION_ON_EMIT` (tuple **sans** `on`, aligné historique) |
| `is_security_response_engine_on_emit_enabled` | `SECURITY_RESPONSE_ENGINE_ON_EMIT` (même tuple) |
| `is_device_reputation_enabled` | `DEVICE_REPUTATION_ENABLED` |
| `is_device_reputation_critical_blocks_auth_enabled` | `DEVICE_REPUTATION_CRITICAL_BLOCKS_AUTH` |
| `is_login_fraud_ml_evaluation_enabled` | `LOGIN_FRAUD_ML_EVALUATION_ENABLED` |
| `is_auth_device_fingerprint_enabled` | `AUTH_DEVICE_FINGERPRINT_ENABLED` |
| `is_passkey_auto_trigger_enabled` | `PASSKEY_AUTO_TRIGGER_ENABLED` |
| `is_passkey_auto_expose_login_email_enabled` | `PASSKEY_AUTO_EXPOSE_LOGIN_EMAIL` |
| `passkey_auto_max_login_risk` | `PASSKEY_AUTO_MAX_LOGIN_RISK` |
| `is_fraud_ml_inference_enabled` | `FRAUD_ML_INFERENCE_ENABLED` |
| `security_events_sink_name` | `SECURITY_EVENTS_SINK` |
| `security_account_lock_hours` | `SECURITY_ACCOUNT_LOCK_HOURS` |
| `global_risk_ml_weight` | `ML_WEIGHT` |
| `fraud_ml_enforce_min_heuristic` | `FRAUD_ML_ENFORCE_MIN_HEURISTIC` |
| `login_fraud_pattern_weight` | `LOGIN_FRAUD_PATTERN_WEIGHT` |
| `auth_rate_limit_backend_for_bootstrap` | `AUTH_RL_BACKEND` (défaut `""`) |

**Note** : `auth_rate_limit_backend_raw()` existait déjà avec défaut `auto` (runtime `auth_rate_limit`) ; le bootstrap conserve une lecture **sans** défaut implicite `auto`.

---

## Modules Cleaned

Modules modifiés dans cette phase (ordre de priorité utilisateur respecté en grande partie) :

1. `api/services/auth/adaptive_auth_orchestrator.py`
2. `api/services/security/session_intelligence_service.py`
3. `api/services/security/continuous_auth_engine.py`
4. `api/services/security/login_auth_strategy_service.py`, `login_device_trust_service.py`, `auth/security_events_service.py`, `auth/device_fingerprint.py`, `auth/passkey_login_eligibility.py`, `auth/auth_bootstrap.py`
5. `api/services/security/security_event_pipeline.py`, `security_event_sink.py`
6. `api/services/security/security_response_engine.py`, `device_reputation/device_reputation_service.py`, `ml/login_fraud_evaluator.py`, `fraud_ml_inference_service.py`

**Middleware** : `session_intelligence_middleware.py` n’utilisait pas de `getenv` direct ; il dépend déjà de `session_intelligence_service` (désormais branché sur `security_env`).

---

## Tests

- Tests existants réexécutés : `test_security_env.py`, `test_adaptive_auth_orchestrator.py`, `test_session_intelligence.py`, `test_phase3_1_auth_infra.py`, `test_security_siem.py` — **OK**.
- Ajouts dans `test_security_env.py` :
  - `test_security_correlation_on_emit_tuple_excludes_on` (non-régression sémantique `on` ≠ vrai pour corrélation)
  - `test_passkey_auto_max_login_risk_bounds`
  - `test_auth_rate_limit_backend_for_bootstrap_empty_when_unset`

---

## Remaining Direct Reads

- **`security_env.py`** : source de vérité (lectures centralisées).
- **WebAuthn, attestation, crypto, zero-trust, dépendances externes** : toujours des `os.getenv` dispersés (voir Inventory).
- **`device_reputation_service.py`** : seuils `DEVICE_REPUTATION_*_FINDING_MIN` non migrés (numériques, faible risque de divergence avec les flags).
- **`security_response_engine.py`** : aucun `os.getenv` résiduel après refactor.

---

## Verdict

La **Phase 2** atteint l’objectif pour les **chemins auth adaptatif, intelligence session, auth continue, stratégie login, moteur de réponse, pipeline SIEM, réputation device, fraude ML, passkey auto, empreinte device, bootstrap rate-limit** : une seule source (`security_env`) pour les flags et paramètres listés, **sans changement de comportement intentionnel** (y compris le cas particulier `SECURITY_CORRELATION_ON_EMIT=on` et le bootstrap `AUTH_RL_BACKEND` vide).

Prochaine étape possible (**Phase 3**) : factoriser **zero-trust**, **device attestation**, **crypto flags** et **webauthn_config** restants vers `security_env` ou modules dédiés minces, en veillant aux cycles d’import.
