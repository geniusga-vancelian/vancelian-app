# Rapport — Durcissement environnement & flags sécurité (Arquantix API)

## Executive Summary

Un module central **`services/security/security_env.py`** unifie la lecture de **`APP_ENV` / `ARQUANTIX_ENV` / `ENVIRONMENT` / `ENV`**, la **normalisation** des alias (`dev` → `development`, etc.), et expose des **helpers** pour passkeys, OTP, WebAuthn strict, adaptive auth, session intelligence, continuous auth, et validations **bootstrap**.

Le module historique **`two_factor_env.py`** s’appuie sur **`security_env`** (plus de duplication de la logique « prod-like »). **`webauthn_config.py`** importe les flags **passkeys / OTP mobile / OTP admin / WebAuthn strict / libellé env** depuis **`security_env`**.

**Sémantique préservée** : l’exigence **Redis** pour le rate-limit auth reste basée sur **`ENVIRONMENT` / `ENV`** uniquement (`production|prod|live`), comme avant ce chantier — **`APP_ENV` seul ne déclenche pas** cette exigence (évite les régressions sur les tests et déploiements existants).

---

## Inventory of Current Security Flags (extrait)

| Variable | Rôle | Défaut typique | Criticité |
|----------|------|-----------------|-----------|
| APP_ENV, ARQUANTIX_ENV, ENVIRONMENT, ENV | Identité déploiement | vide → traité **development** pour normalisation | Haute |
| TWO_FACTOR_DEV_FIXED_CODE | OTP fixe hors prod-like | absent | Haute |
| TWO_FACTOR_DEV_EXPOSE_CODE | `dev_code` JSON | false | Haute |
| TWO_FACTOR_RELAXED | Assouplissement 2FA | auto (non prod-like) | Moyenne |
| AUTH_PASSKEYS_ENABLED | Passkeys | true | Moyenne |
| AUTH_MOBILE_OTP_LOGIN_ENABLED | OTP SMS login | false | Haute |
| AUTH_ADMIN_EMAIL_OTP_ENABLED | OTP e-mail admin | false | Haute |
| AUTH_RL_BACKEND, AUTH_REDIS_URL | Rate limit distribué | auto / optionnel | Haute |
| AUTH_SECURITY_EVENTS_ENABLED | Persistance événements | true | Moyenne |
| LOGIN_DEVICE_TRUST_ENABLED | Confiance device | true | Moyenne |
| LOGIN_AUTH_STRATEGY_ENABLED | Stratégie login | true | Moyenne |
| ADAPTIVE_AUTH_ENABLED | Adaptive auth | false | Moyenne |
| SESSION_INTELLIGENCE_ENABLED | Session intelligence | false | Moyenne |
| CONTINUOUS_AUTH_ENABLED | Continuous auth | false | Moyenne |
| WEBAUTHN_STRICT_CONFIG | Forcer config stricte | auto si prod-like | Haute |
| FAKE_SMS_PROVIDER | SMS factice | interdit prod-like | Haute |
| SECURITY_EVENTS_SINK | Sink SIEM | none | Moyenne |

Inventaire détaillé des fichiers : grep `os.getenv` / lecture env dans `api/services/**` (hors périmètre exhaustif dans ce rapport — voir code et `ENV_HARDENING_AND_SECURITY_FLAGS.md`).

---

## Problems Found

1. **Duplication** : `is_production_like` / `effective_app_env` / flags WebAuthn dispersés entre `two_factor_env`, `webauthn_config`, `phone_validation`.
2. **Incohérence potentielle** : `ENVIRONMENT` vs `APP_ENV` pour Redis vs 2FA — **documentée et conservée** sciemment (Redis = legacy `ENVIRONMENT`).
3. **Tests flaky** : dépendance au `.env` local pour `AUTH_ADMIN_EMAIL_OTP_ENABLED` — corrigé dans `test_webauthn_phase34` avec `monkeypatch` explicite.

---

## Centralized Environment Model

- **`get_normalized_app_env()`** — priorité **APP_ENV → ARQUANTIX_ENV → ENVIRONMENT → ENV** ; alias normalisés.
- **`is_production_like_env()`** — `production` ou `staging` (canoniques) pour OTP / noop / 2FA.
- **`is_auth_redis_required_env()`** — **uniquement** `ENVIRONMENT`/`ENV` ∈ {production, prod, live}.

---

## Refactors Applied

| Fichier | Changement |
|---------|------------|
| `services/security/security_env.py` | **Nouveau** — source de vérité |
| `services/security/two_factor_env.py` | Délégation + `effective_app_env` = normalisé |
| `services/auth/webauthn_config.py` | Import flags depuis `security_env` |
| `services/auth/auth_bootstrap.py` | `validate_security_environment_startup` + docstrings |
| `services/registration/phone_validation.py` | `is_phone_validation_production_strict()` |
| `tests/test_security_env.py` | **Nouveau** |
| `tests/test_phase3_1_auth_infra.py` | `delenv` / garde-fous env pour bootstrap |
| `tests/test_webauthn_phase34.py` | OTP admin désactivé explicitement |

---

## Behavior Matrix by Environment

Voir tableau dans `ENV_HARDENING_AND_SECURITY_FLAGS.md`.

---

## Startup Safety Checks

- `validate_security_environment_startup` : interdit combinaisons **ENVIRONMENT=production (legacy)** + OTP dev / expose / fake SMS ; interdit **fake SMS** en **prod-like** (`APP_ENV` normalisé staging/production).

---

## Tests Added

- `tests/test_security_env.py` — normalisation, expose OTP, Redis legacy, validation startup.

---

## Documentation Updated

- `docs/arquantix/ENV_HARDENING_AND_SECURITY_FLAGS.md`
- `api/.env.security.example`
- Ce rapport

---

## Final Verdict

| Question | Réponse |
|----------|---------|
| Logique centralisée ? | **Oui** pour la majorité des flags auth exposés ; modules métier peuvent encore lire `os.getenv` directement (refactor progressif). |
| Comportements dev/prod déterministes ? | **Oui** pour `get_normalized_app_env` et garde-fous documentés ; **deux** définitions de « production » (Redis vs prod-like) sont **explicites**. |
| Flags sensibles cohérents ? | **Renforcés** au bootstrap ; défauts **secure-by-default** pour OTP admin/mobile (opt-in). |
| Alias APP_ENV supportés ? | **Oui** (`dev`, `prod`, `stage`, `live`, …). |
| Recommander `APP_ENV=development` ? | **Oui** pour le développement local et la documentation ; utiliser **`ENVIRONMENT=production`** en complément pour **Redis** obligatoire jusqu’à harmonisation des déploiements. |

---

## Remaining Risks / Follow-up

1. Migrer progressivement les `_truthy(os.getenv(...))` restants (`adaptive_auth_orchestrator`, `session_intelligence_service`, etc.) vers **`security_env`** ou un sous-module `security_flags.py` si le fichier devient trop volumineux.
2. Harmoniser à terme **Redis** sur `get_normalized_app_env() == "production"` **uniquement** après audit des déploiements réels.
3. Étendre les tests bootstrap pour **APP_ENV=production** + `ENVIRONMENT` vide (politique cible future).
