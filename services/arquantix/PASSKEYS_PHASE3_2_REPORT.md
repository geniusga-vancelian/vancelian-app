# PASSKEYS_PHASE3_2_REPORT

## Executive Summary

La phase 3.2 introduit des **passkeys (WebAuthn)** côté API FastAPI pour les **admin users**, avec stockage **uniquement de clés publiques** et de métadonnées, challenges **à durée courte** en base, et **réutilisation** de `issue_fresh_auth_session` pour les jetons (sessions Phase 2, device binding, fingerprint). Le mobile expose une **couche abstraite** (`PasskeyPlatformProvider`) avec **stub** par défaut, un client HTTP, des écrans liste / enrôlement, et un **coordinator** de login avec **fallback** OTP / mot de passe. Les événements `auth.passkey.*` sont journalisés et persistés dans `auth_security_events` lorsque le flag est actif.

## Threat Model Addressed

- **Phishing résistant** (WebAuthn lié au domaine `rp_id` + origines attendues).
- **Pas de secret symétrique serveur** pour les passkeys : seule la **clé publique** et le **sign counter** sont stockés.
- **Anti-replay** : challenge enregistré avec TTL, supprimé après usage réussi ; vérification **sign_count** pour détecter copies de credential.
- **Énumération d’utilisateurs** : le login start ne révèle pas explicitement l’absence de compte (allowCredentials vide si pas de passkeys ou utilisateur inconnu).
- **Révocation** : soft `revoked_at` sur credential.

## Data Model

- **`auth_passkeys`** : `id`, `user_id`, `credential_id_b64` (unique), `public_key_b64`, `sign_count`, `transports_json`, `device_label`, `aaguid`, `created_at`, `last_used_at`, `revoked_at`.
- **`auth_webauthn_challenges`** : `id` (UUID token côté client), `challenge_b64` (unique), `flow_type` (`register` / `login`), `user_id` nullable, `identifier` (email normalisé), `expires_at`, `created_at`.

Migration Alembic **110** (revises 109).

## Backend Flow

- **register/start** (Bearer requis) : `generate_registration_options`, persistance challenge, audit `auth.passkey.register.started`.
- **register/finish** : `verify_registration_response`, insertion `auth_passkeys`, suppression challenge, `auth.passkey.register.succeeded` / `failed`.
- **login/start** (public) : `generate_authentication_options` avec allowCredentials si utilisateur connu et passkeys actives ; `auth.passkey.login.started`.
- **login/finish** : résolution credential, `verify_authentication_response`, mise à jour `sign_count` / `last_used_at`, **`issue_fresh_auth_session`** avec `auth.passkey.login.succeeded` (même pipeline que login mot de passe pour `auth_sessions` + refresh).
- **GET /auth/passkeys** / **POST /auth/passkeys/revoke** : gestion par utilisateur authentifié ; `auth.passkey.revoked`.

Bibliothèque **`webauthn`** (PyPI). Configuration env : `WEBAUTHN_RP_ID`, `WEBAUTHN_RP_NAME`, `WEBAUTHN_ORIGINS` (liste séparée par virgules), `WEBAUTHN_CHALLENGE_TTL_SEC`, `AUTH_PASSKEYS_ENABLED`.

## Mobile Flow

- **`PasskeyApi`** : appels REST ; `debugBaseUrl` pour tests sans `AUTH_API_BASE_URL`.
- **`PasskeyService`** : enrôlement et login (orchestration start → provider natif → finish).
- **`PasskeyProviderStub`** : `isAvailable == false` → **fallback** obligatoire jusqu’à branchement d’un plugin (Phase 3.3).
- **`PasskeyLoginCoordinator`** : en cas d’indisponibilité ou d’erreur API, appelle **`onFallback`** (OTP / mot de passe).
- **`PasskeyManagementScreen`** / **`PasskeySetupScreen`** : liste, révocation, tentative d’ajout ; entrée **Profil → Passkeys**.
- **`SessionService.readAccessToken`** ajouté pour les appels authentifiés passkeys.

## Challenge Storage

- Table **`auth_webauthn_challenges`** : un enregistrement par tentative ; **TTL** court ; suppression après succès ; lecture refuse les lignes expirées.

## Session Integration

- **`issue_fresh_auth_session`** dans `refresh_session.py` : factorise création `AuthSession`, fingerprint, audit, `commit`, paire access/refresh.
- **`perform_login`** (mot de passe) appelle cette fonction avec `auth.login.succeeded`.
- **Passkeys** appellent la même fonction avec `auth.passkey.login.succeeded` et métadonnées credential.
- En-têtes **`X-Device-ID`** et **`X-Device-Fingerprint`** supportés sur `login/finish` comme sur le login classique.

## Security Events

Événements ajoutés (logs + `auth_security_events` si activé) :  
`auth.passkey.register.started|succeeded|failed`, `auth.passkey.login.started|succeeded|failed`, `auth.passkey.revoked`.

## Tests Added

- **Backend** : `tests/test_passkeys.py` — challenge register, finish crée credential, login finish crée session, challenge expiré, credential révoqué, événement register.started (avec `main.app` + override DB).
- **Flutter** : `test/features/security/passkeys/passkey_service_test.dart` — stub indisponible, enrôlement mock HTTP + fake provider, login mock tokens, coordinator fallback.

## Remaining Gaps / Phase 3.3

- **Provider natif** : brancher `passkeys` / ASWebAuthenticationSession / Credential Manager sur `PasskeyPlatformProvider` (remplacer le stub).
- **Attestation** : politique stricte par `fmt`, certs racines si besoin (`pem_root_certs_bytes_by_fmt`).
- **Resident keys / username-less** : parcours sans email préalable.
- **Nettoyage** : job périodique des challenges expirés non consommés.
- **Parité produit** : flux OTP explicite dans l’UI login (bouton « Continuer avec passkey » branché au coordinator).
- **Tests E2E** : navigateur / device réel avec `WEBAUTHN_ORIGINS` alignés sur l’environnement.
