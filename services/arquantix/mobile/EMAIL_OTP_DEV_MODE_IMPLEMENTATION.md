# Avant

- Génération OTP e-mail : `_generate_code()` aléatoire, indépendante de `TWO_FACTOR_DEV_FIXED_CODE`.
- `NoopEmailProvider` (sans SES) → **503** sur `POST /auth/login/email-otp/start` dans tous les environnements.
- Pas de `dev_code` dans la réponse JSON.

# Problème dev

- Impossible de tester le flux e-mail comme le SMS sans SES.
- Pas d’alignement avec `TWO_FACTOR_DEV_FIXED_CODE` / `two_factor_env`.

# Solution

- **Génération** : `otp_plaintext_for_login_challenges()` dans `sms_otp_core.py` — délègue à `new_plaintext_sms_otp()` (même règle dev que le SMS).
- **Noop** : 503 **uniquement** si `is_production_like_env()` **et** provider noop ; sinon le flux continue (challenge + `send_otp` noop).
- **JSON** : champ optionnel `dev_code` sur `AdminEmailOtpStartResponse`, rempli via `admin_email_otp_dev_code_for_response(plaintext)` dans `two_factor_env.py` (non prod + `TWO_FACTOR_DEV_EXPOSE_CODE`).

# Sécurité

- `is_production_like_env()` : **pas** de code fixe exposé, **pas** de contournement SES obligatoire (noop → 503).
- `admin_email_otp_dev_code_for_response` : retourne `None` en prod-like même si `TWO_FACTOR_DEV_EXPOSE_CODE` est mal positionné.

# Tests

- `api/tests/test_admin_email_otp_dev_mode.py` : fixed code, noop 200, expose JSON, prod noop 503, prod sans `dev_code`.
- `test_webauthn_phase34.py` : fixture **reset** du rate limiter auth entre tests (évite 429 en suite).

# Impact prod

- Comportement inchangé : env prod-like + SES requis ; code aléatoire si pas de `TWO_FACTOR_DEV_FIXED_CODE` ; `dev_code` toujours absent (ou null).

# Fichiers

| Fichier | Rôle |
|---------|------|
| `api/services/security/two_factor_env.py` | `admin_email_otp_dev_code_for_response` |
| `api/services/security/sms_otp_core.py` | `otp_plaintext_for_login_challenges` |
| `api/services/auth/admin_email_otp_routes.py` | logique dev / réponse |
| `api/tests/test_admin_email_otp_dev_mode.py` | tests dédiés |
| `api/tests/test_webauthn_phase34.py` | reset rate limit |
| `mobile/.../passkey_api.dart` | `adminEmailOtpStart` → `Map` |
| `mobile/.../login_email_otp_screen.dart` | hint « Mode test » si `dev_code` |
| `mobile/.../admin_email_otp_login_screen.dart` | idem (message concaténé) |
