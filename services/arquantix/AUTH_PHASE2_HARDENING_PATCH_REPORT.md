# AUTH_PHASE2_HARDENING_PATCH_REPORT.md

## Executive Summary

Patch de durcissement sur la Phase 2 auth : **`/auth/revoke`** exige désormais **`X-Device-ID`** et un alignement strict avec `session.device_id` ; **middleware de rate limiting** sur login (par IP), refresh et revoke (par device) ; **purge périodique** des lignes `auth_spent_refresh_jti` au-delà d’une rétention configurable ; **logs enrichis** (changement d’IP, rafraîchissements rapprochés, IP avec nombre élevé d’échecs refresh).

## 1. `/auth/revoke` sécurisé

- En-tête **`X-Device-ID`** obligatoire (chaîne non vide après trim). Sinon **401** avec `detail: "X-Device-ID required"`.
- Si une session active correspond au `jti` du refresh : **égalité stricte** entre `normalize_device_id(header)` et `session.device_id`. Sinon **401** `Device mismatch` + log `auth.revoke.device_mismatch` (device masqués, jti tronqué).
- Jeton illisible / sans session : comportement idempotent inchangé pour le corps (204 possible) **après** la vérification d’en-tête — une requête sans en-tête échoue toujours avant.

**Tests :** `test_revoke_requires_device_header`, `test_revoke_rejects_wrong_device` ; les tests existants envoient `X-Device-ID: legacy-unknown` lorsque le login est sans device explicite.

## 2. Rate limiting (middleware global)

Fichiers : `services/auth/auth_rate_limit.py`, `services/auth/auth_rate_limit_middleware.py`, enregistré dans `create_app()` juste après le CORS.

| Route | Clé | Défaut quota | Fenêtre (défaut) |
|-------|-----|--------------|------------------|
| `POST /auth/login` | IP client (`client.host` ou premier hop `X-Forwarded-For` si `AUTH_TRUST_X_FORWARDED_FOR=1`) | **5** / fenêtre | **60 s** |
| `POST /auth/refresh` | `X-Device-ID` ou `__missing__` | **20** | **60 s** |
| `POST /auth/revoke` | idem | **10** | **60 s** |

**Variables d’environnement :**

- `AUTH_RL_LOGIN_MAX`, `AUTH_RL_LOGIN_WINDOW_SEC`
- `AUTH_RL_REFRESH_MAX`, `AUTH_RL_REFRESH_WINDOW_SEC`
- `AUTH_RL_REVOKE_MAX`, `AUTH_RL_REVOKE_WINDOW_SEC`
- `AUTH_RL_BACKEND` : `memory` | `redis` | `auto` (défaut : `auto` — Redis si joignable, sinon mémoire process)
- `AUTH_TRUST_X_FORWARDED_FOR` : `1` / `true` / `yes` pour faire confiance au premier IP de `X-Forwarded-For` (derrière reverse proxy)

Réponse **429** : JSON `{"error":{"code":"rate_limited","message":"...","retry_after":...}}`.

**Tests :** `test_login_rate_limited_after_quota`, `test_refresh_rate_limited_per_device`, `test_revoke_rate_limited_per_device`.

**Isolation tests :** fixture `autouse` dans `test_auth_refresh.py` qui appelle `reset_auth_rate_limiter_for_tests()` pour éviter l’accumulation de hits entre cas.

## 3. Cleanup `auth_spent_refresh_jti`

- Fonction : `services/auth/spent_jti_cleanup.py` → `run_spent_jti_cleanup(db)` supprime les lignes avec `spent_at` **strictement antérieur** à `now - retention_days`.
- `AUTH_SPENT_JTI_RETENTION_DAYS` (défaut **30**).
- Thread daemon dans `main.py` (hors `testing`) : intervalle `AUTH_SPENT_JTI_CLEANUP_INTERVAL_SEC` (défaut **86400**, minimum de sommeil **60 s** entre passes).

**Test :** `test_spent_jti_cleanup_removes_old_rows`.

## 4. Logging avancé

Toujours via `arquantix.auth.security` ; pas de jeton en clair.

| Événement | Déclencheur |
|-----------|-------------|
| `auth.session.ip_changed` | Refresh réussi : `session.ip_address` connue et différente de l’IP courante (IPs masquées). |
| `auth.refresh.rapid_burst` | Deux refresh valides espacés de **&lt; 2 s** pour la même session (`last_used_at` vs maintenant). |
| `auth.refresh.suspect_ip` | **≥ 8** échecs refresh (401) depuis la même IP sur une fenêtre glissante **60 s** (mémoire process, best-effort multi-workers). |
| `auth.refresh.rejected` | Inchangé ; chaque 401 refresh déclenche aussi `note_refresh_reject` pour alimenter le compteur ci-dessus. |

Fichiers : `refresh_session.py` (`_note_failed_refresh`, logs IP / burst), `auth_security_signals.py`.

## 5. Tests ajoutés / modifiés

| Fichier | Cas |
|---------|-----|
| `tests/test_auth_refresh.py` | En-tête `X-Device-ID: legacy-unknown` sur revoke ; fixture reset rate limiter |
| `tests/test_auth_hardening_patch.py` | Revoke sans header / mauvais device ; rate limit login / refresh / revoke ; cleanup JTI |

## 6. Fichiers touchés (référence)

- `api/services/auth/auth_rate_limit.py` (nouveau)
- `api/services/auth/auth_rate_limit_middleware.py` (nouveau)
- `api/services/auth/spent_jti_cleanup.py` (nouveau)
- `api/services/auth/auth_security_signals.py` (nouveau)
- `api/services/auth/refresh_session.py` (revoke, logs refresh)
- `api/main.py` (middleware, thread cleanup, route revoke)
- `api/tests/test_auth_refresh.py`
- `api/tests/test_auth_hardening_patch.py` (nouveau)

## 7. Limites connues

- Rate limiting **mémoire** : par processus uniquement ; utiliser **`AUTH_RL_BACKEND=redis`** en multi-workers.
- Signal `auth.refresh.suspect_ip` : mémoire locale, non partagé entre instances.
- Clients legacy sans `X-Device-ID` sur revoke : **cassés par design** — ils doivent envoyer explicitement `legacy-unknown` s’ils étaient logués sans device.

## 8. Suite possible

- Lier le rate limit à Redis par défaut en production.
- Persister les compteurs « suspect » en Redis.
- Corrélation SIEM sur les champs structurés des logs.
