# PR D3 — Liaison attestation ↔ clé, nonces, cycle de vie, routes sensibles

## Objectif

Compléter PR D2 avec une **preuve d’alignement** attestation / `public_key`, des **signatures requête** (hors seul refresh), des **nonces** anti-replay, la **révocation** de credentials, et un **rate-limit** d’échecs — le tout derrière des flags.

## Phase 1 — Binding attestation ↔ clé

- Variable : `REGISTER_KEY_PK_ATTESTATION_BINDING=true`
- `POST /auth/device/register-key` exige alors `X-Device-Attestation` **valide** (pipeline existant `evaluate_header_for_auth`) **et** un champ `pk_sha256` / `public_key_sha256` (JSON racine ou `clientDataJSON` décodé) égal à `sha256(SPKI_DER).hexdigest()`.
- Mobile : inclure le hash dans `clientDataJSON` **avant** assertion App Attest pour que la preuve soit couverte par la signature Apple.

## Phase 2 — Routes sensibles

- Si `DEVICE_SECURITY_LEVEL >= 2` : dépendance `require_sensitive_device_signature` (voir `device_sensitive_signature.py`).
- En-têtes : `X-Device-Signature`, `X-Device-Signature-Timestamp`, `X-Device-Signature-Nonce`, `X-Content-SHA256` (hash hex du corps).
- Message : `ARQXD3|v1|nonce|ts|METHOD|path|body_sha256` (UTF-8).
- Démo : `POST /auth/device/sensitive-action` — à répliquer sur custody / transferts en ajoutant le même `Depends` aux handlers (ex. bénéficiaires : `require_continuous_auth_for_action` + `require_sensitive_device_signature`).

## Phase 3 — Nonces

- `POST /auth/device/signature-nonce` (Bearer + `X-Device-ID`) → `{ nonce, expires_at, ttl_seconds }`.
- Table `auth_device_signature_nonces` ; consommation au succès de la vérification.

## Phase 4 — Cycle de vie

- Colonnes : `revoked_at`, `device_label`, `public_key_sha256_hex`, `attestation_bound_at` sur `auth_device_credentials`.
- `GET /auth/device/list`, `POST /auth/device/{device_id}/revoke`.
- `GET /auth/device/policy` : niveau effectif + TTL nonce (pour clients).

## Phase 5 — Rate limit

- Échecs signature / attestation (binding) : `DEVICE_SIGNATURE_FAILURE_RL_MAX` (défaut 30 / fenêtre 60 s) via `device_signature_failure_rl.py`.

## Compatibilité

- PR D2 inchangé si `REGISTER_KEY_PK_ATTESTATION_BINDING` absent et `DEVICE_SECURITY_LEVEL<2`.
- Migration Alembic : `133_pr_d3_device_security.py`.

## Tests

- `tests/test_device_pr_d3.py` — message `ARQXD3` + ECDSA.
