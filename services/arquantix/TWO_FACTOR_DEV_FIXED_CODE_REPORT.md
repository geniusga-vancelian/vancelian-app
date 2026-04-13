# TWO_FACTOR_DEV_FIXED_CODE — Rapport

## Executive Summary

Un mode **dev/test** permet d’utiliser un **OTP SMS/email à six chiffres fixe** (`TWO_FACTOR_DEV_FIXED_CODE`) lorsque l’environnement **n’est pas** `production`, `prod` ou `staging` (via `APP_ENV` ou `ARQUANTIX_ENV`). Le code est **hashé comme avant** (bcrypt) ; **aucun** stockage en clair en base ; **`verify_code` est inchangé** (hash, tentatives, expiration, statuts). Optionnellement, **`TWO_FACTOR_DEV_EXPOSE_CODE`** peut faire remonter ce code en JSON sous **`dev_code`** sur `/api/2fa/start` (canal sms/email uniquement) et sur **prepare/resend** d’inscription. **Jamais** actif en environnement production-like.

## Env Vars Added

| Variable | Rôle |
|----------|------|
| `TWO_FACTOR_DEV_FIXED_CODE` | Si défini, **6 chiffres**, et env non production-like → remplace le tirage aléatoire pour SMS/email à la création du challenge. Sinon ignoré. |
| `TWO_FACTOR_DEV_EXPOSE_CODE` | Si truthy (`1` / `true` / `yes`), env non production-like, et code fixe valide → les réponses API concernées incluent `dev_code`. |

Garde centralisée : `is_production_like_env()` dans `api/services/security/two_factor_env.py`.

## Service Changes

- **`two_factor_env.py`** : `two_factor_dev_fixed_code()`, `two_factor_dev_code_for_api_exposure()`.
- **`two_factor_service.py`** : `_otp_plaintext_for_sms_email()` — utilise le code fixe autorisé ou `_generate_numeric_code()` ; SMS/email appellent cette méthode avant `_hash_otp` et le reste du flux (TTL, DB, `send_code`, audit) reste identique.
- **`router.py`** : `TwoFactorStartResponse.dev_code` optionnel ; `response_model_exclude_none=True` sur `/start` pour ne pas exposer de clé vide ; `dev_code` seulement pour `sms` / `email`.
- **`registration/service.py`** : clé `dev_code` ajoutée aux dict retournés par `prepare_interaction` et `resend_interaction` uniquement quand l’exposition est autorisée.

## Security Guards

- Production-like (`APP_ENV` / `ARQUANTIX_ENV` ∈ {`production`, `prod`, `staging`}) : **ignore** `TWO_FACTOR_DEV_FIXED_CODE` et **n’expose jamais** `dev_code` (helpers retournent `None`).
- Format OTP fixe invalide (≠ 6 chiffres) : **ignoré** (comportement aléatoire normal).
- TOTP : **pas** de code fixe ni d’exposition `dev_code` sur `/start`.
- Aucun bypass de `verify_code` : même comparaison bcrypt, mêmes `attempts` / expiration / transitions.

## Tests Added

Fichier : `api/tests/test_two_factor_dev_fixed_code.py`

- Garde production-like / `ARQUANTIX_ENV=staging` / format invalide / exposition conditionnelle.
- `/api/2fa/start` email + `verify` avec le code fixe.
- `verify` avec mauvais code → échec attendu.
- `dev_code` présent sur start SMS quand exposition activée ; absent pour TOTP même si exposition.

## Remaining Gaps

- Pas de **refus explicite** (HTTP 500 / log d’alerte) si `TWO_FACTOR_DEV_FIXED_CODE` est défini en prod-like : la variable est **silencieusement ignorée** (comportement demandé : ignorée ou interdite — ici **ignore**).
- Les clients doivent continuer à traiter `dev_code` comme **strictement dev** et ne jamais s’en servir en prod (contrat d’API documenté ici et dans les descriptions de champs).
