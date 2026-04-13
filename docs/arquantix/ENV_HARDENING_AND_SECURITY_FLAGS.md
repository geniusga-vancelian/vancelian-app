# Durcissement des variables d’environnement et flags sécurité

## Executive Summary

La logique **déploiement** et **feature flags** sensibles est centralisée dans :

`services/arquantix/api/services/security/security_env.py`

Les modules historiques (`two_factor_env`, `webauthn_config`) **délèguent** désormais les décisions communes (passkeys, OTP admin/mobile, libellé d’environnement, WebAuthn strict).

## Normalisation des environnements

| Alias (entrée) | Valeur canonique |
|----------------|------------------|
| dev, local | development |
| testing | test |
| stage | staging |
| prod, live | production |

**Lecture unifiée** : `APP_ENV` → `ARQUANTIX_ENV` → `ENVIRONMENT` → `ENV`  
Fonction : `get_normalized_app_env()`

### Deux sémantiques « production » (important)

1. **`is_production_like_env()`** — `development`/`test` exclus ; **staging** et **production** sont « prod-like » pour OTP, noop providers, 2FA, etc.
2. **`is_auth_redis_required_env()`** / `is_production_environment()` — **uniquement** `ENVIRONMENT` / `ENV` ∈ {production, prod, live} (comportement **historique** pour Redis rate-limit et bootstrap). **`APP_ENV` n’est pas lu** ici, afin de ne pas casser les déploiements qui ne fixent que `ENVIRONMENT`.

### Téléphone (registration)

`is_phone_validation_production_strict()` conserve l’ordre **legacy** : `ENVIRONMENT` → `ENV` → `APP_ENV` → `ARQUANTIX_ENV`, et n’active le strict **MOBILE** que si la valeur normalisée est **production** (pas staging).

## Helpers principaux (security_env)

- `normalize_app_env`, `get_normalized_app_env`, `get_raw_deployment_env`
- `is_development_env`, `is_test_env`, `is_staging_env`, `is_production_env`
- `is_production_like_env`, `is_non_production_env`
- `is_two_factor_relaxed`
- `is_passkeys_enabled`, `is_mobile_otp_login_enabled`, `is_admin_email_otp_enabled`
- `is_security_events_enabled`, `is_login_device_trust_enabled`, `is_login_auth_strategy_enabled`
- `is_adaptive_auth_enabled`, `is_session_intelligence_enabled`, `is_continuous_auth_enabled`
- `is_webauthn_strict_environment`, `current_environment_label`
- `should_expose_dev_otp_code`, `should_use_dev_fixed_otp`
- `should_require_real_email_provider_for_admin_otp`, `should_require_redis_auth_rate_limit`
- `validate_security_environment_startup`

`two_factor_env` expose toujours : `two_factor_dev_fixed_code`, `two_factor_dev_code_for_api_exposure`, `admin_email_otp_dev_code_for_response`, `effective_app_env` (alias de `get_normalized_app_env`).

## Comportements par environnement (matrice cible)

| Feature | development | test | staging | production |
|--------|-------------|------|---------|------------|
| OTP fixe dev (`TWO_FACTOR_DEV_FIXED_CODE`) | oui si défini | idem | **non** | **non** |
| `dev_code` JSON | si `EXPOSE` | idem | **non** | **non** |
| Noop e-mail en prod-like OTP admin | interdit si strict | — | interdit | interdit |
| Fake SMS (`FAKE_SMS_PROVIDER`) | si activé | idem | **non** | **non** |
| WebAuthn strict (HTTPS, origines) | si flag ou prod-like | idem | oui | oui |
| Redis auth obligatoire | non | non | non* | oui (`ENVIRONMENT` prod) |

\*Staging : Redis **non** forcé par `is_auth_redis_required_env` (legacy) ; en pratique utiliser Redis en préprod.

## Safe defaults

- `AUTH_ADMIN_EMAIL_OTP_ENABLED` : défaut **false** (opt-in).
- `AUTH_MOBILE_OTP_LOGIN_ENABLED` : défaut **false** (opt-in).
- `TWO_FACTOR_DEV_EXPOSE_CODE` : défaut **false**.
- `AUTH_PASSKEYS_ENABLED` : défaut **true** (désactiver explicitement si besoin).

## Validation au démarrage

`validate_security_environment_startup` (appelée depuis `enforce_auth_infrastructure_bootstrap`) :

- Si `ENVIRONMENT` indique la production (legacy) : refuse `TWO_FACTOR_DEV_FIXED_CODE`, `TWO_FACTOR_DEV_EXPOSE_CODE`, `FAKE_SMS_PROVIDER`.
- Si **prod-like** (`APP_ENV` normalisé staging/production) : refuse `FAKE_SMS_PROVIDER`.

WebAuthn strict et e-mail admin noop restent dans `webauthn_config.validate_*_at_startup`.

## Tests

`tests/test_security_env.py` — normalisation, expose dev OTP, validation startup.

## Migration

- Préférer **`APP_ENV=development`** (ou `staging` / `production`) comme source principale pour la **logique métier** (OTP, 2FA, prod-like).
- Conserver **`ENVIRONMENT=production`** pour l’**exigence Redis** auth jusqu’à convergence documentée des déploiements.
- `effective_app_env()` retourne désormais une valeur **normalisée** (ex. `dev` → `development`).
