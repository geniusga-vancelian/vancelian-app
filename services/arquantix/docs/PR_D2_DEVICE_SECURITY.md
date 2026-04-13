# PR D2 — Identité device crypto + attestation session

## Objectif

Renforcer le modèle PR B (cohérence `device_id`) avec une **identité cryptographique** optionnelle et une **politique d’attestation** sur le refresh, sans casser les clients existants (feature flags à **0** par défaut).

## Composants

### 1. Table `auth_device_credentials`

- Clé logique : `(user_id, device_id)` avec `public_key_spki_b64` (ECDSA P-256, SPKI DER en base64).
- Enregistrement : `POST /auth/device/register-key` (Bearer + `X-Device-ID`).

### 2. Signatures refresh

- Message UTF-8 : `ARQXD2|v1|{unix_ts}|{sha256_hex(refresh_token)}` (SHA-256 sur le **string** refresh, hex minuscule).
- En-têtes : `X-Device-Signature` (base64), `X-Device-Signature-Timestamp` (secondes).
- Vérification : `services/auth/device_request_signature.py`.

### 3. Variables d’environnement

| Variable | Défaut | Rôle |
|----------|--------|------|
| `DEVICE_SECURITY_LEVEL` | `0` | `0` = off, `1` = si credential + strict ou tentative signée, `2` = refuse si credential + signature invalide |
| `DEVICE_SIGNATURE_STRICT` | `false` | Avec niveau 1, exige signature valide dès qu’un credential existe |
| `ATTESTATION_SESSION_MAX_AGE_SEC` | *(vide)* | Si défini, `refresh` exige `attestation_verified_at` récente (sinon 403 `device_attestation_stale`) |
| `DEVICE_SIGNATURE_CLOCK_SKEW_SEC` | `120` | Fenêtre horloge signature |

### 4. Mobile (Flutter)

- `lib/features/security/device_signing/data/device_signing_service.dart`
- Stockage clé privée : `SessionStorageKeys.deviceSigningEcdsaSecretB64`
- Build : `--dart-define=PR_D2_DEVICE_SIGNING=true` pour envoyer les en-têtes sur `/auth/refresh`.

## Compatibilité PR B

- `device_id` reste la clé de session ; les signatures **s’ajoutent** après le binding device.
- Sans migration DB exécutée ou sans flag, aucun changement de comportement.

## Tests

- `tests/test_device_pr_d2.py` — roundtrip crypto, SEC1→SPKI, fraîcheur attestation.
