# Secure passcode + session — Phase 1 (rapport d’implémentation)

## Features

| Zone | Livré |
|------|--------|
| **Flutter** | Module `features/security/passcode/` : setup PIN 6 chiffres, déverrouillage, biométrie (`local_auth`), stockage `flutter_secure_storage`, anti brute-force progressif, `SessionService` + `SessionApi` |
| **Démarrage** | Après le splash : `SecureGateScreen` → si PIN configuré, `PasscodeUnlockScreen` (Face ID / Touch ID puis fallback PIN), sinon `MainShellScreen` |
| **Configuration** | Onglet Design system : section « Sécurité — Code PIN & biométrie » → `PasscodeSetupScreen` |
| **Backend** | `POST /auth/login` renvoie `access_token` + `refresh_token` ; `POST /auth/refresh` (rotation) ; `POST /auth/revoke` (204, client-side discard) |
| **Plateforme** | iOS : `NSFaceIDUsageDescription` ; Android : `USE_BIOMETRIC` |

## Security design

- **PIN** : 6 chiffres stricts, **jamais** en clair sur disque ; dérivation **PBKDF2-HMAC-SHA256** (~120k itérations) avec **sel aléatoire** par appareil (stocké en secure storage).
- **Comparaison** : hash dérivé comparé en temps constant sur les octets (base64 décodé).
- **Lockout** : après **5** échecs → verrou **30 s** puis **5 min** puis **1 h** (tier incrémental) ; après **4** épisodes de verrouillage → **reset local** (PIN + préférences biométrie effacés, session API effacée) — à coupler côté produit avec **re-login / 2FA** obligatoire.
- **Logs** : aucun log du PIN ni du hash ; messages debug limités au mode debug (ex. lockout reset).
- **Backend** : **aucun** stockage de PIN ; refresh JWT avec claim `typ: "refresh"` (ne pas logger les jetons).

## Storage strategy

| Clé (préfixe `arqx.`) | Contenu |
|------------------------|---------|
| `sec.device_salt_b64` | Sel PBKDF2 |
| `sec.passcode_hash_b64` | Sortie dérivation (base64) |
| `sec.failed_attempts` | Compteur avant lock |
| `sec.lock_until_ms` | Fin de verrouillage |
| `sec.lockout_tier` / `sec.lockout_events` | Progression pénalités |
| `sec.biometric_enabled` | Opt-in biométrie |
| `sess.access_token` / `sess.refresh_token` / `sess.access_expires_at_ms` | Session API |

**iOS** : Keychain (`first_unlock_this_device`). **Android** : `EncryptedSharedPreferences`.

## Session handling

- `SessionService` lit/écrit les jetons en secure storage.
- `refreshAccessToken()` appelle `POST {AUTH_API_BASE_URL}/auth/refresh` si `--dart-define=AUTH_API_BASE_URL=...` est défini (sinon no-op réseau).
- `revokeRemoteSession()` : `POST /auth/revoke` puis effacement local.
- **Rotation** : chaque refresh renvoie une **nouvelle** paire access + refresh côté API.

**Note** : l’app mobile consomme surtout le **BFF Next.js** (`Config.apiBaseUrl`) ; l’URL FastAPI d’auth est **distincte** (`SecureApiConfig.authApiBaseUrl`).

## Tests

| Suite | Fichier |
|-------|---------|
| API | `api/tests/test_auth_refresh.py` — login + refresh + rejet access token + revoke 204 |
| Flutter | `mobile/test/passcode/lockout_policy_test.dart`, `passcode_crypto_test.dart` |

**Tests manuels suggérés**

1. Design → Configurer le code → double saisie → activer/désactiver biométrie → cold start → Face ID ou PIN.
2. 5 mauvais PIN → attente 30 s → nouvel essai.
3. Définir `AUTH_API_BASE_URL`, stocker des jetons via `SessionService.storeTokens`, vérifier `refreshAccessToken()`.

## Limites & prochaines étapes (Phase 2+)

- **Révocation** : stateless — un refresh volé reste valide jusqu’à **exp** sans denylist serveur (Redis / table `jti`).
- **Device binding** : clé `sess.device_id` réservée ; pas encore branchée côté API.
- **Re-lock au resume** : non implémenté (cold start uniquement) ; à ajouter avec `WidgetsBindingObserver` si besoin type Revolut.
- **Refactor recommandé** : enregistrer les routes `/auth/*` **dans** `create_app()` pour que **tous** les `TestClient(test_app)` les voient (aujourd’hui elles sont sur l’instance globale `main.app`).
