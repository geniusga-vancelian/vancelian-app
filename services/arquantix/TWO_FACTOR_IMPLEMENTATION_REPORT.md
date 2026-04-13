# Rapport d’implémentation — 2FA transverse (OTP + TOTP)

## Objectif

Un seul service capable de gérer **SMS OTP**, **email OTP** et **TOTP** (Google Authenticator), réutilisable partout via le champ libre **`purpose`** (ex. `verify_phone`, `verify_email`, `withdrawal`, `login`).

## Architecture backend (FastAPI)

### Modèle de données

Table **`public.two_factor_challenges`** (migration Alembic `096_two_factor_challenges.py`) :

| Colonne      | Rôle |
|-------------|------|
| `id` (UUID) | Identifiant du challenge |
| `person_id` | FK vers `persons` |
| `channel`   | `sms`, `email`, `totp` |
| `target`    | Téléphone ou email (nullable pour TOTP) |
| `code_hash` | Hash du code OTP (bcrypt) ; valeurs sentinelles pour flux TOTP enroll / verify |
| `expires_at`| Expiration (défaut ~5 min côté service) |
| `attempts`  | Tentatives de vérification |
| `status`    | `pending`, `verified`, `expired`, `failed` |
| `purpose`   | Chaîne métier (réutilisation) |
| `created_at`| Horodatage |

Index : `person_id`, `status`, `expires_at`, composite `(person_id, created_at)` pour le rate limit d’envoi.

### Couche service

Fichier : `api/services/security/two_factor_service.py`

- **`create_challenge`** : génère un code à 6 chiffres (SMS/email), hash bcrypt, persistance ; TOTP enroll (`purpose=totp_setup`) génère secret + `otpauth_url` et stocke le secret **chiffré** en attente dans `person.profile_json["security"]["totp_pending_cipher"]`.
- **`send_code`** : SMS (Twilio), email (SES), pas d’envoi pour TOTP.
- **`verify_code`** : contrôle expiration, plafond de tentatives (5), comparaison hash ou TOTP ; met à jour `status` / `attempts` via `flush()`.
- **`check_rate_limit`** : au plus un envoi OTP par **30 s** par personne (dernier challenge créé).

### Providers

- **`providers/sms_provider.py`** : Twilio via HTTP si `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` ; sinon noop (log **sans** code).
- **`providers/email_provider.py`** : AWS SES (boto3) si expéditeur configuré ; sinon noop.

### Chiffrement TOTP

- **`crypto.py`** : Fernet dérivé de `TWO_FACTOR_TOTP_MASTER_KEY` ou repli sur `JWT_SECRET_KEY`.
- Secret actif : `profile_json["security"]["totp_secret_cipher"]`.

### API HTTP

Préfixe : **`/api/2fa`** (`api/services/security/router.py`), enregistré dans `main.py`.

| Méthode | Chemin | Corps principal | Réponses clés |
|--------|--------|-----------------|---------------|
| POST | `/start` | `channel`, `purpose`, `target?`, `person_id?` (dev) | `challenge_id`, `masked_target`, `resend_after_seconds`, `otpauth_url?` |
| POST | `/verify` | `challenge_id`, `code`, `person_id?` (dev) | `success`, `status` |

Codes HTTP typiques : `422` (`invalid_code`), `410` (`expired`), `429` (`rate_limited`, `too_many_attempts`), `404` (challenge / personne).

**Persistance des tentatives** : en cas d’erreur métier après `verify_code`, le routeur effectue un **`commit`** (et non un `rollback`) pour ne pas annuler l’incrémentation de `attempts` ni les passages en `expired` / `failed`.

### Authentification

`api/services/security/deps.py` : `person_id` issu du JWT (`person_id` ou résolution via `Client.email` ↔ `sub`). Si **`TWO_FACTOR_REQUIRE_AUTH=false`**, acceptation de `person_id` dans le body (tests / dev uniquement).

### Tests

`api/tests/test_two_factor_api.py` : happy path email, mauvais codes + compteur, rate limit second `start`, challenge expiré, flux TOTP enroll + verify.

## Flutter

- **Config** : `mobile/lib/core/config.dart` — `Config.twoFactorStartUrl` / `twoFactorVerifyUrl` (base = `marketDataBaseUrl`, FastAPI).
- **Client** : `mobile/lib/features/security/data/two_factor_api.dart` — `TwoFactorApi.start` / `verify`, en-tête `Authorization: Bearer …`, parsing des erreurs `detail: { code, message }`.
- **UI** : `mobile/lib/features/security/presentation/screens/two_factor_screen.dart` — `TwoFactorScreen` (canal, `purpose`, `target?`, token, `personId?` dev) : 6 champs chiffres, envoi auto à 6 digits, message d’erreur inline, timer renvoi aligné sur `resend_after_seconds`, affichage optionnel `otpauth_url` pour l’enrôlement TOTP.

Exemple de navigation :

```dart
Navigator.push(
  context,
  MaterialPageRoute(
    builder: (_) => TwoFactorScreen(
      channel: TwoFactorChannel.email,
      purpose: 'verify_email',
      target: userEmail,
      accessToken: token,
      onVerified: () => context.go('/next'),
    ),
  ),
);
```

## Sécurité

- Codes OTP **jamais** stockés en clair ; hash **bcrypt** (salt par hash).
- Logs sans code ni secret TOTP.
- `masked_target` renvoyé au client pour l’UX.
- Limite **5** tentatives de vérification par challenge ; statut `failed` au-delà.
- Rate limit **30 s** entre deux `start` pour une même personne (logique service).

## Variables d’environnement (référence)

| Variable | Usage |
|----------|--------|
| `TWO_FACTOR_REQUIRE_AUTH` | `true` prod ; `false` dev/tests pour `person_id` body |
| `TWO_FACTOR_TOTP_MASTER_KEY` | Clé dédiée chiffrement TOTP (recommandé) |
| `JWT_SECRET_KEY` | Repli Fernet si pas de clé TOTP |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_FROM_NUMBER` | SMS |
| `SES_FROM_EMAIL` ou `AWS_SES_FROM` | Expéditeur SES |
| `AWS_REGION` + credentials IAM | Envoi SES |

## Pistes suivantes (hors périmètre actuel)

- Flags métier « 2FA activé », méthode préférée, fallback SMS si TOTP indisponible.
- Intégration explicite aux flux withdrawal / login côté routes métier (réutiliser les mêmes endpoints ou sessions internes).
