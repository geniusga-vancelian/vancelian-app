# Rapport — Device attestation Tier 1 (niveau bancaire, itération 1)

## Objectif

Réduire le risque de **spoof de `device_id`** en vérifiant une **attestation matérielle** côté serveur (Apple App Attest / DeviceCheck, Google Play Integrity), en stockant un **niveau de confiance** sur la session, et en déclenchant un **step-up OTP** lorsque la politique l’exige.

## Fichiers livrés

| Zone | Fichier |
|------|---------|
| Service | `api/services/auth/device_attestation_service.py` |
| Challenge HTTP | `api/services/auth/device_attestation_routes.py` |
| Auth | `api/services/auth/refresh_session.py`, `api/auth.py`, `api/main.py` |
| Modèle / migration | `api/database.py`, `api/alembic/versions/112_auth_device_attestation_tier1.py` |
| Sessions admin | `api/schemas.py` (`AuthSessionItem` enrichi) |
| Passkeys / OTP | `api/services/auth/passkeys_service.py`, `api/services/auth/admin_email_otp_routes.py` (confiance `TRUSTED`) |
| Mobile | `mobile/lib/features/security/device_attestation/data/device_attestation_service.dart`, `mobile/.../session_api.dart` |
| Tests | `api/tests/test_device_attestation_tier1.py` |

## API

- **`POST /auth/attestation/challenge`** — retourne `{ nonce, expires_at }` (nécessite `DEVICE_ATTESTATION_ENABLED=true`). Rate-limit aligné sur le login (IP).
- **`POST /auth/login`**, **`POST /auth/refresh`** — en-tête optionnel **`X-Device-Attestation`** : JSON UTF-8 ou **base64url** d’un JSON.

Payload attendu (exemples) :

- **Play Integrity** : `format: play_integrity`, `integrity_token`, `nonce`, optionnel `verdict` (mode lenient sans API Google).
- **App Attest** : `format: apple_app_attest`, `assertion` (CBOR base64), `nonce`, optionnel `key_id`.
- **DeviceCheck (fallback)** : `format: apple_devicecheck`, `device_token`, `nonce`.

## Modèle de confiance

- **AttestationResult** : `is_valid`, `trust_level` (`HIGH` / `MEDIUM` / `LOW` / `BLOCKED`), `risk_flags`, `attestation_type`, `metadata`.
- **Session / JWT** : `device_trust_level` ∈ `TRUSTED`, `UNKNOWN`, `SUSPICIOUS`, `BLOCKED` ; JWT access : claims `dtrust`, `step_up_otp` si OTP requis.

## Variables d’environnement

| Variable | Rôle |
|----------|------|
| `DEVICE_ATTESTATION_ENABLED` | Active le flux (défaut `false`) |
| `DEVICE_ATTESTATION_STRICT` | Exige une vérif crypto / API plus stricte |
| `DEVICE_ATTESTATION_FAIL_BLOCKS_LOGIN` | `403` si attestation invalide (sinon login avec confiance basse + step-up) |
| `DEVICE_ATTESTATION_STEP_UP_ON_FAIL` | Active `step_up_otp` côté JWT / session si échec d’attestation |
| `DEVICE_ATTESTATION_HEADER_REQUIRED` | Oblige l’en-tête pour les appareils non `legacy-unknown` |
| `DEVICE_ATTEST_NONCE_TTL_SEC` | TTL du nonce (60–900 s) |
| `DEVICE_ATTEST_ARTIFACT_TTL_SEC` | TTL anti-rejeu assertion / jeton |
| `IOS_ATTEST_APP_ID` | Identifiant app (hash RP en mode strict Apple) |
| `PLAY_INTEGRITY_USE_GOOGLE_API` | Appeler l’API Google pour décoder le jeton |
| `ANDROID_PACKAGE_NAME`, `GOOGLE_APPLICATION_CREDENTIALS` | Play Integrity API |

## Stratégie d’échec

1. Événement d’audit `auth.device.attestation_failed` (via `_auth_audit`).
2. **Downgrade** : `device_trust_level` → `SUSPICIOUS` si non bloquant.
3. **Step-up** : `step_up_otp_required` + claim JWT `step_up_otp` ; chemin OTP admin documenté dans le `403` : `otp_login_path` = `/auth/login/email-otp/start`.

## Limites Tier 1 (à durcir en prod)

- **Apple** : la vérification **ECDSA complète** et la **chaîne x5c → racine Apple** ne sont pas entièrement implémentées ici ; en `STRICT`, une attestation initiale (`attestation_object_b64`) est requise pour aller au-delà du contrôle structurel CBOR + binding d’app (hash).
- **Play Integrity** : sans `PLAY_INTEGRITY_USE_GOOGLE_API`, le mode **lenient** s’appuie sur un `verdict` JSON fourni par le client — **à utiliser uniquement en dev / tests**, pas en production.
- **Passkeys / OTP e-mail** : considérés comme **TRUSTED** pour la session (facteur fort ou second facteur).

## Mobile Flutter

- `DeviceAttestationService` + providers **stub** (`IosAppAttestProvider`, `AndroidPlayIntegrityProvider`) : à brancher sur les SDK natifs (App Attest, Play Integrity).
- `SessionApi.refresh` accepte `attestationServerNonce` : après `POST /auth/attestation/challenge`, passer le `nonce` pour construire l’en-tête.

## Tests

```bash
cd api && alembic upgrade head
pytest tests/test_device_attestation_tier1.py tests/test_auth_refresh.py -v
```

Scénarios couverts : verdict Play lenient + nonce, format inconnu, login avec en-tête valide (`dtrust` dans le JWT), faux jeton avec blocage, **rejeu de nonce** sur second login.

## Dépendances Python

- `cbor2` — parsing CBOR App Attest.
- `google-auth` — optionnel pour l’API Play Integrity (avec `httpx` déjà présent).
