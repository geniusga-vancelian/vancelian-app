# Runbook — durcissement 2FA production

## Variables obligatoires (APP_ENV = production | prod | staging)

| Variable | Rôle |
|----------|------|
| `APP_ENV` ou `ARQUANTIX_ENV` | `production`, `prod` ou `staging` pour activer le garde-fou boot |
| `TWO_FACTOR_REQUIRE_AUTH` | `true` (interdit `person_id` arbitraire dans le body) |
| `TWO_FACTOR_TOTP_MASTER_KEY` | Au moins 32 caractères, **dédiée** (ne pas réutiliser un secret court) |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` | SMS opérationnel (noop interdit en prod) |
| `SES_FROM_EMAIL` ou `AWS_SES_FROM` + credentials AWS | Email opérationnel (noop interdit en prod) |
| `AWS_REGION` / `AWS_DEFAULT_REGION` | Région SES |

Optionnel urgence : `SKIP_TWO_FACTOR_CONFIG_GUARD=true` pour débloquer un déploiement (à retirer immédiatement après).

## Avant déploiement

1. `alembic upgrade head` (inclut `097` : colonne `two_factor_challenges.source_ip`).
2. Vérifier qu’aucun `TWO_FACTOR_RELAXED` / `PYTEST_*` n’est présent sur l’environnement cible.
3. Smoke test Twilio (numéro de test) et SES (sandbox ou prod) depuis un script ou staging.
4. Vérifier les logs applicatifs : au boot, message `2FA configuration guard passed`.

## Après déploiement

1. `GET /health` puis `POST /api/2fa/start` + `verify` sur un compte test (JWT valide).
2. Contrôler qu’une erreur provider (ex. SES refus) renvoie **503** `provider_unavailable` et **aucun** succès 200 si l’envoi a échoué.
3. Vérifier les entrées `two_factor.challenge.*` dans `audit_events`.

## Tests manuels

### SMS

- Start `channel=sms` avec numéro E.164 valide → réception du SMS (texte court « security code »).
- Second start immédiat → **429** `resend_rate_limited`.

### Email

- Start `channel=email` → mail reçu, sujet « Security code ».

### TOTP

- Start `totp` + `purpose=totp_setup` → `otpauth_url` présent.
- Verify avec code authenticator → `totp_secret_cipher` renseigné, `totp_pending_cipher` supprimé.

### REQUIRE_AUTH

- Sans `Authorization` → **401**.
- Avec JWT sans `person_id` / sans résolution client → selon config.

### Noop interdit en prod

- Avec `APP_ENV=production` et sans Twilio/SES, le **process ne doit pas démarrer** (`TwoFactorConfigGuardError`).

### Rate limits

- Plus de 5 starts SMS/email en 15 min pour une même personne → **429** `start_quota_exceeded` (hors mode relaxed).
- Après nombreuses vérifs en échec (fenêtre 10 min) → **429** `verify_rate_limited`.

## Logs / audit

- Rechercher `2fa rejected internal_code=` (niveau WARNING) côté API.
- Table `audit_events`, `event_type` préfixe `two_factor.challenge.` : created, sent, send_failed (session autonome), verify_failed, verify_succeeded, expired, rate_limited, resend_blocked, totp_activated.

## Flutter

- Les erreurs utilisent `detail.code` ; l’app mappe vers des libellés FR via `twoFactorUserMessage`.
