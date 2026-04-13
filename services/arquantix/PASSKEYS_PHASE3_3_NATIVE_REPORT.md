# Passkeys Phase 3.3 — Intégration native (rapport)

## Executive Summary

La phase 3.3 remplace le stub par des providers **iOS** et **Android** basés sur le package Flutter [`passkeys`](https://pub.dev/packages/passkeys) (ASAuthorization sur iOS, Credential Manager côté Android via les implémentations du plugin). Un **écran de connexion API** (`ApiSessionLoginScreen`) propose « Continue with Passkey » et « Use verification code instead » (flux `TwoFactorScreen` e-mail). Le backend expose **`POST /auth/passkeys/prompt`** pour les événements `auth.passkey.prompt.*`, et un **thread daemon** purge les challenges WebAuthn expirés (défaut : toutes les 10 minutes, `WEBAUTHN_CHALLENGE_CLEANUP_INTERVAL_SEC`).

## Native Integration (iOS / Android)

| Fichier | Rôle |
|--------|------|
| `mobile/lib/features/security/passkeys/passkey_native_provider.dart` | `IOSPasskeyProvider`, `AndroidPasskeyProvider` — `PasskeyAuthenticator` + mapping des exceptions du package vers le domaine app. |
| `mobile/lib/features/security/passkeys/data/passkey_platform_provider_factory.dart` | Import conditionnel : IO → natif, sinon → stub. |
| `mobile/lib/features/security/passkeys/data/passkey_platform_provider_factory_io.dart` | `Platform.isIOS` / `isAndroid` ; `kIsWeb` → stub. |

**Disponibilité** : iOS = `hasPasskeySupport` ; Android = `hasPasskeySupport` et `isUserVerifyingPlatformAuthenticatorAvailable != false`.

## Login Flow

1. Profil → **Connexion compte** (si `AUTH_API_BASE_URL` non vide au compile-time).
2. Saisie e-mail → **Continue with Passkey** → `PasskeyLoginCoordinator.signInWithPasskey` → `/login/start` → provider `getCredential` → `/login/finish` → `SessionService.storeTokens` → retour shell.

## Fallback UX

- Bouton permanent **Use verification code instead** → `TwoFactorScreen` (e-mail, `purpose: login`).
- Fallback automatique (SnackBar) si passkey indisponible, annulation utilisateur, erreur authenticator ou API.

## Backend Cleanup

- `api/services/auth/webauthn_challenges_cleanup.py` : `cleanup_webauthn_challenges(db)` — `DELETE` où `expires_at < now(UTC)`.
- `main.py` : boucle périodique (hors `testing`), intervalle configurable.

## Tests

- **API** : `tests/test_passkeys.py` — cleanup challenge expiré, `POST /auth/passkeys/prompt` (204 / 400).
- **Flutter** : `test/.../passkey_service_test.dart` — succès mock, fallback stub, annulation (`PasskeyUserCancelledException`).

## Config (production)

À valider impérativement :

- **`WEBAUTHN_RP_ID`** : domaine réel aligné sur l’hôte servi aux clients (ex. même host que l’API ou domaine associé aux passkeys).
- **`WEBAUTHN_ORIGINS`** : liste d’origines HTTPS autorisées pour la vérification WebAuthn (séparateur virgule).
- **HTTPS** obligatoire en production pour les relying parties réelles ; mobile utilise le domaine RP pour l’association « domaine / applis » (cf. doc plugin : associated domains iOS, Digital Asset Links Android).

Variables utiles : `WEBAUTHN_RP_NAME`, `WEBAUTHN_CHALLENGE_TTL_SEC`, `WEBAUTHN_CHALLENGE_CLEANUP_INTERVAL_SEC`, `AUTH_PASSKEYS_ENABLED`.

## Security Events

| Événement | Source |
|-----------|--------|
| `auth.passkey.prompt.opened` | Mobile (login / add passkey) |
| `auth.passkey.prompt.cancelled` | Mobile (annulation système) |
| `auth.passkey.prompt.failed` | Mobile (indisponible, erreur, API) |
| `auth.passkey.login.succeeded` / `failed` | Backend (existant) |
| `auth.passkey.register.*` | Backend (existant) |

Rate limit : `/auth/passkeys/prompt` traité comme les autres chemins passkeys sensibles (IP, même limite que login).

## Remaining Gaps

- **OTP login** : dépend du support backend de `purpose=login` sur `POST /api/2fa/start` ; à valider en intégration.
- **Associated domains / asset links** : configuration Xcode / Android à finaliser pour le **RP ID** de prod (hors code).
- **Tests E2E** device réel : simulateurs / émulateurs peuvent limiter passkeys ou compte Google (Android).
- **Nettoyage challenges** : `commit()` dans la fonction de cleanup émet des avertissements SQLAlchemy dans la suite de tests transactionnelle ; acceptable ; option future : paramètre `commit=` pour les tests.
