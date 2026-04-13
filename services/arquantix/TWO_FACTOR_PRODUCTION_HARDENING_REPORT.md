# Rapport — durcissement 2FA production-grade

## Executive Summary

Le module 2FA transverse a été renforcé **sans refonte** : garde-fou au boot en environnement `production` / `staging`, interdiction des providers noop en prod, rate limiting multi-critères (personne, cible, IP, fenêtres courte/longue), erreurs normalisées anti-énumération, audit sur `audit_events`, échecs d’envoi SMS/email gérés proprement (503, pas de faux succès), TOTP avec fenêtre limitée et trace d’activation, UX Flutter enrichie (codes d’erreur + titre TOTP). Les tests existants `test_two_factor_api.py` restent verts ; une suite `test_two_factor_hardening.py` couvre les nouveaux garde-fous.

## Environment Guards

- Fichier : `api/services/security/two_factor_config_guard.py`, appel depuis `create_app(..., testing=False)` dans `main.py`.
- Condition : `APP_ENV` ou `ARQUANTIX_ENV` ∈ {`production`, `prod`, `staging`} (lu **à chaque appel**, pas à l’import).
- Exigences : `TWO_FACTOR_REQUIRE_AUTH=true`, `TWO_FACTOR_TOTP_MASTER_KEY` (≥ 32 caractères), SMS Twilio complet, expéditeur SES défini, providers non noop.
- Échappement : `SKIP_TWO_FACTOR_CONFIG_GUARD` (documenté comme exception d’urgence).

## Provider Safety

- `SmsProvider` / `EmailProvider` exposent `is_noop`.
- En prod (non relaxed), start SMS/email refuse `noop` avec `channel_not_available` (503-ready côté sémantique « indisponible »).
- Twilio : erreurs HTTP capturées, message générique côté API ; log sans corps Twilio exposé au client.
- SES : `ClientError` capturé, log du code erreur AWS uniquement côté serveur.
- Échec d’envoi après création du challenge : **audit `send_failed` en session autonome** (`standalone=True`) pour survivre au rollback, puis `provider_unavailable` (503).

## Rate Limiting

- `api/services/security/two_factor_rate_limits.py`
- **Start** : 30 s par `(person_id, channel, purpose)` ; jusqu’à **5** challenges `sms`/`email` / 15 min / personne ; jusqu’à **10** / 15 min par cible ; jusqu’à **25** / 15 min par `source_ip` (colonne `two_factor_challenges.source_ip`, migration `097`).
- **Verify** : jusqu’à **25** échecs comptabilisés via `audit_events` (`two_factor.challenge.verify_failed`) / 10 min / personne (désactivé en mode relaxed).
- Audits associés aux blocages : `resend_blocked`, `rate_limited` (avec `reason` dans le payload).

## Auth / Ownership Safety

- `resolve_person_id(..., anti_enum_missing_person=True)` sur les routes 2FA : personne absente ou mismatch JWT/body → **403** `unauthorized_2fa_request` (message générique).
- Vérification : `challenge_id` + `person_id` JWT → impossible de valider le challenge d’un autre utilisateur (404 `challenge_not_found`).

## TOTP Hardening

- Activation effective seulement après verify d’enrôlement (promotion `totp_pending_cipher` → `totp_secret_cipher`), audit `two_factor.challenge.totp_activated`.
- `TOTP_VALID_WINDOW = 1` (pyotp).
- Prod : clé Fernet dédiée imposée au boot ; commentaire de rotation dans `crypto.py`.

## Error Model

- Source : `api/services/security/two_factor_errors.py` + `http_detail_for_code` dans le routeur.
- Réponse : `{"detail": {"code": "<external_code>", "message": "<ux_safe>"}}`.
- Anciens codes internes (`not_found`, `expired`, `rate_limited`) mappés vers les codes externes canoniques.

### Liste des codes externes (principaux)

`challenge_not_found`, `challenge_expired`, `invalid_code`, `too_many_attempts`, `challenge_not_verifiable`, `resend_rate_limited`, `start_quota_exceeded`, `target_rate_limited`, `ip_rate_limited`, `verify_rate_limited`, `provider_unavailable`, `channel_not_available`, `purpose_not_allowed`, `invalid_purpose`, `invalid_channel`, `target_required`, `target_mismatch`, `totp_not_configured`, `unauthorized_2fa_request`.

## Audit / Observabilité

- Réutilisation de `public.audit_events`.
- Types : `two_factor.challenge.created`, `.sent`, `.send_failed`, `.verify_succeeded`, `.verify_failed`, `.expired`, `.rate_limited`, `.resend_blocked`, `.totp_activated`.
- Jamais de code OTP ni secret en clair dans les payloads.

## Flutter UX Hardening

- `twoFactorUserMessage(...)` : mapping FR par `error_code` + repli sur le message serveur.
- Titre par défaut TOTP : précision « application d’authentification ».
- Anti double-soumission : garde `_verifying` sur `verify`.
- Timer de renvoi : relancé uniquement après `start` réussi (inchangé fonctionnellement, messages améliorés).

## Purposes autorisées (prod strict)

Définies dans `two_factor_purposes.py` :  
`verify_phone`, `verify_email`, `withdrawal` (legacy), `external_withdrawal`, `security_change`, `login_step_up`, `login`, `totp_setup`.  
Hors liste + non relaxed → `purpose_not_allowed`.

## Politique dev / test

- Relaxed si : `app.state.testing`, `TWO_FACTOR_RELAXED=true`, `PYTEST_CURRENT_TEST`, ou environnement **non** production-like.
- En relaxed : purposes libres, noop autorisé, rate limits IP/cible/longue fenêtre verify désactivés.

## Tests ajoutés

Fichier `api/tests/test_two_factor_hardening.py` : purpose strict, garde-fou config (mock noop), skip guard hors prod, isolation challenge inter-utilisateurs, échec SMS → 503 + pas de ligne challenge, mismatch email `verify_email`, plafond verify global (mock strict relaxed).

## Déploiement / runbook

Voir `TWO_FACTOR_PRODUCTION_HARDENING_RUNBOOK.md` (Alembic `097`, checks avant/après, validation noop interdit, rate limits).

## Gaps / prochaines étapes

- Désactivation TOTP sécurisée (second factor, délai, re-auth) — documentée uniquement.
- Vérification stricte du téléphone pour `verify_phone` si le modèle `Client` expose un numéro fiable.
- Redis / edge pour rate limit IP en multi-instance à très forte charge (actuellement DB + `source_ip`).
- Internationalisation côté API (messages actuellement en anglais, Flutter en français).
