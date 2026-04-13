# Executive Summary

Extension de l’**Adaptive Auth Orchestrator** au-delà du login : une table **`auth_session_intelligence`**, un service de mise à jour continue, un moteur **`continuous_auth_engine`** pour les actions sensibles, enrichissement des **JWT** (claims `strust`, `lstup`, `relock`, `bio_req`), middleware d’**activité légère**, endpoints **admin**, événements **SIEM** sous le préfixe `auth.session.*`, et intégration **Flutter** (snapshot JWT + relock via `SessionIntelligenceManager`). Rien de parallèle à la stack auth existante : les hooks vivent dans `issue_fresh_auth_session`, `perform_refresh` et les dépendances FastAPI optionnelles.

# Architecture Overview

| Composant | Rôle |
|-----------|------|
| `AuthSessionIntelligence` | 1:1 avec `auth_sessions`, état courant risque / confiance / flags |
| `session_intelligence_service.py` | Init, mise à jour (refresh + contexte), scores, flags step-up / relock |
| `continuous_auth_engine.py` | Décision `allow` / `require_step_up` / `require_reauth` / `require_biometric` |
| `sensitive_action_map.py` | `ACTION_SECURITY_MAP` (high / medium / low) |
| `session_intelligence_dependencies.py` | `require_continuous_auth_for_action("…")` |
| `session_intelligence_middleware.py` | Touche `last_activity_at` via JWT `sid` (hors chemins auth) |
| `zero_trust/continuous_auth.py` | Inchangé fonctionnellement ; refresh continue d’appeler `maybe_require_step_up_after_refresh_signals` |

# Session Intelligence Model

Champs principaux : `auth_strength`, `session_trust_level`, `device_trust_level`, `last_risk_score`, `last_fraud_score`, `last_activity_at`, `last_sensitive_action_at`, `last_ip`, `last_country`, `relock_required`, `step_up_required`, `last_step_up_at`, `reason_codes_json`, timestamps.

Migration : `alembic/versions/119_auth_session_intelligence.py`.

# Continuous Auth Engine

`evaluate_request_security_context(session, request, session_intelligence, sensitive_action=…)` :

- Si feature off ou pas d’intelligence → `allow=True` (fallback UX).
- `tier_for_action` + scores / raisons → `require_reauth` (ex. pays changé + action sensible), `require_step_up` (flag intel ou risque vs tier).

# Sensitive Action Protection

`ACTION_SECURITY_MAP` : `withdrawal`, `wallet_transfer`, `api_key_create` (high), `change_password`, `view_sensitive_data` (medium).

Branchement : `Depends(require_continuous_auth_for_action("view_sensitive_data"))` — exemple **`GET /admin/security/session-intelligence/probe-continuous-auth`**. Les routes métier peuvent ajouter la même dépendance sans changer les handlers existants.

# JWT Integration

`auth.create_access_token` accepte désormais : `session_trust_level`, `last_step_up_at_ts`, `relock_required`, `biometric_hint` → claims **`strust`**, **`lstup`**, **`relock`**, **`bio_req`**. Émis à l’**issue session** et à chaque **refresh** si une ligne intelligence existe.

# Flutter Integration

- `SessionSecuritySnapshot` : parse / persiste les nouveaux claims.
- `SessionService.storeTokens` : enregistre `securityClaimsJson` après chaque stockage de token.
- `SessionIntelligenceManager` : `effectiveRelockThreshold`, `shouldRelockNow`, `shouldRequireBiometric`, `shouldForceReauth` (heuristique).
- `BiometricPolicyService.shouldRelockNow` : applique le seuil issu de `SessionIntelligenceManager` via `LocalRelockEngine.shouldRelockNow(..., effectiveThresholdOverride: …)`.

# Events / SIEM

Types émis (via `persist_auth_security_event`) :

- `auth.session.intelligence.updated`
- `auth.session.risk_changed` (variation de score ≥ 5)
- `auth.session.step_up.triggered` (transition vers step-up)
- `auth.session.reauth.triggered` (blocage dépendance)
- `auth.session.step_up.triggered` (403 step-up)

Payloads incluent `session_id`, `user_id`, `risk_score`, `device_trust`, `reason_codes` lorsque disponibles.

# Tests

- Backend : `api/tests/test_session_intelligence.py`
- Flutter : `mobile/test/features/security/session_intelligence_snapshot_test.dart`

# Rollout Strategy

1. Migrer la base (`alembic upgrade head`).
2. Activer `SESSION_INTELLIGENCE_ENABLED=true` seul → init des lignes + JWT enrichis + middleware léger.
3. Puis `CONTINUOUS_AUTH_ENABLED=true` sur environnements pilotes.
4. Ajouter `Depends(require_continuous_auth_for_action(...))` route par route sur les opérations sensibles.

Variables (voir aussi `.env.arquantix.example`) :

- `SESSION_INTELLIGENCE_ENABLED` (défaut **false**)
- `CONTINUOUS_AUTH_ENABLED` (défaut **false**)
- `SESSION_STEP_UP_ENABLED` (défaut **true** si env set)
- `SESSION_REAUTH_ENABLED` (défaut **true** si env set)

# Remaining Gaps

- Brancher explicitement `mark_sensitive_action` sur les endpoints métier (virements, clés API, etc.).
- Affiner `shouldForceReauth` côté client avec un claim dédié si besoin (aujourd’hui heuristique locale).
- Réduire la verbosité SIEM si `auth.session.intelligence.updated` est trop fréquent (échantillonnage / agrégation).
- Tests d’intégration DB + refresh avec intelligence activée.
- Harmoniser avec une future API « step-up completed » pour poser `last_step_up_at` côté serveur.
