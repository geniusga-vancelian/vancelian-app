# AUTH_INFRA_HARDENING_PHASE3_1_REPORT

## Executive Summary

La phase 3.1 renforce l’infrastructure d’authentification pour un niveau « fintech » : rate limiting distribué obligatoire en production (Redis, fenêtre fixe INCR+EXPIRE), confiance appareil via en-tête `X-Device-Fingerprint` (Flutter + parsing backend), persistance des signaux dans `auth_security_events`, corrélation en lecture seule (`SecuritySignalService`), et API admin `/admin/security/events` (+ résumé). Aucun blocage automatique n’a été ajouté (flags + logs uniquement). Les flux existants restent compatibles (feature flags, device legacy, sessions Phase 2).

## Redis Rate Limiting Enforcement

- **`enforce_auth_infrastructure_bootstrap(testing=...)`** (déjà présent, désormais appelé au début de `create_app`) : si `ENVIRONMENT` ∈ `production|prod|live` et `testing=False`, alors `AUTH_RL_BACKEND` doit être exactement `redis`, et `ping_auth_redis()` doit réussir (`AUTH_REDIS_URL` ou repli `REDIS_URL`). Sinon `RuntimeError` avec message explicite.
- **`RedisIncrAuthRateLimiter`** : clés `arq:auth:rl:ic:{login|refresh|revoke}:{client_key}` ; `INCR`, `EXPIRE` sur première requête, correction TTL si `-1` ; dépassement → HTTP 429 (structure d’erreur inchangée).
- **Clés métier** : login → IP (`client_ip_for_rl`) ; refresh / revoke → `X-Device-ID` (via middleware, inchangé).
- **Production** : `build_auth_rate_limiter()` n’utilise jamais la mémoire ; échec Redis → `RuntimeError` au premier build.
- **Hors production** : `memory`, `redis` ou `auto` comme avant, avec repli mémoire si Redis indisponible (hors prod uniquement).

## Device Trust Design

- **Flutter** : `DeviceIdService` — `install_id` stable (secure storage), `buildFingerprintHeaderJson()` produit un JSON avec `device_id`, `install_id`, `platform` (ios/android), `os_version`, `app_version` (const alignée sur `pubspec.yaml`), sans `device_model` pour limiter les dépendances. En-tête `X-Device-Fingerprint` ajouté sur `/auth/refresh` et `/auth/revoke` dans `SessionApi` ; web (`kIsWeb`) : pas d’en-tête.
- **Backend** : `device_fingerprint.py` parse et normalise le JSON ; calcule `fingerprint_hash` (SHA-256 du JSON canonique). Flag `AUTH_DEVICE_FINGERPRINT_ENABLED` (défaut true).
- **DB** (`auth_sessions`) : `fingerprint_hash`, `fingerprint_metadata` (JSONB), `attestation_type`, `attestation_verified_at` (migration `109`).
- **Changement d’empreinte** : si le hash change pour une session existante → log `auth.device.fingerprint_changed` + événement `auth.device.fingerprint_changed` (pas de blocage).
- **Attestation** : `verify_device_attestation(fingerprint, payload)` dans `device_attestation.py` — stub retournant `False` ; prêt pour branchement Apple/Google en phase 3.2.

## Security Events Storage

- **Table** `auth_security_events` : `id` (UUID), `user_id` (nullable), `device_id`, `event_type`, `ip_address`, `user_agent`, `metadata` (JSONB), `created_at` ; index sur `user_id`, `device_id`, `ip_address`, `created_at`, `event_type`.
- **Service** : `persist_auth_security_event` ; flag `AUTH_SECURITY_EVENTS_ENABLED` (défaut true). Même session que la requête quand `db` est fourni (flush) ; sinon session courte + `commit` pour les chemins avec rollback (échecs login, rejets refresh, etc.).
- **Types enregistrés** (liste demandée couverte) : `auth.login.succeeded` / `auth.login.failed`, `auth.refresh.succeeded`, `auth.refresh.rejected`, `auth.revoke`, `auth.revoke_all`, `auth.device.mismatch`, `auth.session.ip_changed`, `auth.refresh.suspect_ip`, `auth.refresh.rapid_burst`, `auth.device.fingerprint_changed`.

## Correlation Logic

- **`SecuritySignalService`** : `count_events_by_ip` / `by_device` / `by_user` ; `detect_anomalies()` retourne `suspicious_ip`, `suspicious_device`, `suspicious_user` + `details` :
  - plus de 10 `auth.refresh.rejected` sur 60 s ;
  - plus de 5 `auth.refresh.rapid_burst` sur 300 s ;
  - même `user_id` avec `auth.session.ip_changed` et `auth.device.fingerprint_changed` dans une fenêtre de 120 s.
- Aucune action automatique (log `security_signal.anomaly_flags` seulement).

## Tests

- **`tests/test_phase3_1_auth_infra.py`** : limiteur INCR concurrent (mock Redis thread-safe) ; bootstrap prod (`AUTH_RL_BACKEND` et Redis) ; parsing fingerprint ; login avec en-tête fingerprint (après migration) ; événement `auth.login.succeeded` avec flag activé ; corrélation sur rafales de rejets.
- **`tests/conftest.py`** : `AUTH_SECURITY_EVENTS_ENABLED=false` par défaut pour éviter les commits isolés hors transaction pytest ; les tests phase 3.1 réactivent le flag explicitement.
- **Prérequis** : `alembic upgrade head` (révision **109**) pour colonnes `auth_sessions` et table `auth_security_events`.
- Les suites `test_auth_refresh` et `test_auth_hardening_patch` passent avec la migration appliquée.

## Remaining Gaps (Attestation, Risk Engine)

- **Attestation** : implémentation réelle App Attest / Play Integrity, validation des chaînes, liaison `attestation_type` / `attestation_verified_at`, et politique de refus graduel.
- **Risk engine** : scoring multi-signaux, décisions automatisées (step-up, blocage, MFA), intégration avec SIEM / export streaming, rétention et anonymisation RGPD sur `ip_address` / `user_agent`.
- **Rate limiting** : fenêtre glissante ou token bucket si besoin de lissage plus fin ; quotas différenciés par tenant ou par route.
- **Admin** : pagination curseur, export CSV contrôlé, rôles « security_readonly » distincts de l’admin CMS.
