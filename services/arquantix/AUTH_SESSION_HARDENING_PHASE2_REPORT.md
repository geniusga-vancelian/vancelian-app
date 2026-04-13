# AUTH_SESSION_HARDENING_PHASE2_REPORT.md

## Executive Summary

La Phase 2 remplace le refresh JWT **stateless** par des **sessions persistées** (`auth_sessions`), une **rotation stricte** du refresh (un jti = une utilisation), une **denylist** via `auth_spent_refresh_jti`, un **device binding** (`device_id` dans le JWT + en-tête `X-Device-ID`), des endpoints **`/auth/revoke-all`** et **`GET /auth/sessions`**, des **événements de sécurité** structurés (logger `arquantix.auth.security`), et côté mobile un **device_id stable** en secure storage, les en-têtes sur refresh/revoke, un **relock local au resume** (après délai configurable), et la **purge locale des jetons** si le refresh renvoie 401.

## Threat Model Addressed

| Menace | Mitigation Phase 2 |
|--------|-------------------|
| Refresh volé rejoué indéfiniment | Session DB + jti courant ; après rotation, l’ancien jti est dans `auth_spent_refresh_jti` → réutilisation refusée |
| Refresh valide mais session révoquée | `revoked_at` sur la ligne session ; refresh impossible |
| Vol de refresh sur un autre appareil | `device_id` dans le claim + contrôle avec `X-Device-ID` ; mismatch → 401 + log `auth.device.mismatch` |
| Logout « client only » | `POST /auth/revoke` met à jour la session + marque le jti comme dépensé |
| Compromission multi-session | `POST /auth/revoke-all` avec Bearer access |
| Déploiement avec anciens jetons Phase 1 | Premier refresh sans `device_id` dans le JWT : upgrade contrôlé (utilisateur vérifié **avant** `claim` du jti) + jti legacy consommé une seule fois |

## Session Data Model

### `auth_sessions`

- `id` (UUID, PK)
- `user_id` (FK → `admin_users.id`, CASCADE)
- `device_id` (TEXT, max 128 côté API via normalisation)
- `refresh_jti` (TEXT, unique) — jti **courant** du refresh valide
- `created_at`, `last_used_at`, `expires_at` (timestamptz)
- `revoked_at`, `revoke_reason` (nullable)
- `ip_address`, `user_agent` (nullable)

### `auth_spent_refresh_jti`

- `jti` (PK) — tout jti ayant servi à une rotation ou à un upgrade legacy réussi
- `spent_at`

Insertion via `ON CONFLICT DO NOTHING` pour détecter la **réutilisation concurrente** ou rejouée.

## Refresh Rotation Design

1. Décoder le JWT refresh (`typ=refresh`, `sub`, `jti`, `device_id` si Phase 2).
2. Alignement **header** `X-Device-ID` (normalisé) avec le claim `device_id` si présent ; sinon refus si le claim existe (jeton Phase 2).
3. Charger la session par `refresh_jti` non révoquée.
4. Si trouvée : vérifier expiration, **égalité stricte** `session.device_id` / header, puis `claim_refresh_jti(jti)` ; en cas d’échec → **401 reuse**.
5. Mettre à jour `refresh_jti` → nouveau UUID, `last_used_at`, fenêtre `expires_at` glissante (+ `JWT_REFRESH_DAYS`).
6. Émettre nouvelle paire access + refresh.

**Ce qui n’est plus stateless :** la validité du refresh dépend d’une ligne DB active et d’un jti non dépensé, pas seulement de la signature JWT.

## Device Binding

- **Backend :** `normalize_device_id` ; sans en-tête → `legacy-unknown` (rétrocompat documentée).
- **JWT refresh :** claim `device_id` obligatoire pour tout nouveau jeton.
- **Flutter :** `DeviceIdService` persiste un UUID v4 dans `SessionStorageKeys.deviceId` ; `SessionApi` envoie `X-Device-ID` sur `/auth/refresh` et `/auth/revoke`.

**Comportement mismatch :** 401 immédiate ; log `auth.refresh.rejected` (reason `device_mismatch`) ou `auth.device.mismatch` selon le chemin.

## Mobile Resume Relock

- **Fichiers :** `SecureAccessConfig.enableResumeRelock`, `resumeRelockAfter` (défaut **45 s**), `resume_lock_logic.dart`, `MainShellScreen` + `WidgetsBindingObserver` (horodatage sur `AppLifecycleState.paused`).
- **UX :** ouverture de `PasscodeUnlockScreen(popOnSuccess: true)` en dialogue plein écran ; succès → `Navigator.pop` (pas de nouvelle instance de shell).
- **Audit local :** `developer.log('auth.app.relocked', name: 'arquantix.security')`.
- **Indépendant du backend :** purement local (PIN / biométrie).

## Audit Events

Émis via `logging.getLogger("arquantix.auth.security")` (pas de jetons en clair ; device/jti partiellement masqués) :

- `auth.login.succeeded` / `auth.login.failed`
- `auth.login.legacy_device` (login sans `X-Device-ID`)
- `auth.refresh.succeeded` / `auth.refresh.rejected` (+ raisons : `invalid_token`, `device_mismatch`, `refresh_token_reuse`, etc.)
- `auth.refresh.legacy_upgrade`
- `auth.device.mismatch`
- `auth.session.revoked` / `auth.session.revoked_all`

Les événements **ne remplacent pas** la table `audit_events` métier (liée aux `person_id`) ; une table dédiée « auth audit DB » peut être ajoutée en Phase 3 si exigence compliance.

## API Additions

| Méthode | Auth | Rôle |
|---------|------|------|
| `POST /auth/login` | — | Crée `auth_sessions` ; accepte `X-Device-ID` |
| `POST /auth/refresh` | — | Rotation + binding |
| `POST /auth/revoke` | — | Révocation réelle |
| `POST /auth/revoke-all` | Bearer access | Révoque toutes les sessions de l’utilisateur |
| `GET /auth/sessions` | Bearer access | Sessions actives (non révoquées, non expirées) |

## Tests Added

### Backend (`api/tests/test_auth_refresh.py`)

- Login crée une ligne `AuthSession` (avec `X-Device-ID`)
- Refresh refuse la **réutilisation** de l’ancien refresh
- Refresh refuse un **device** différent
- Après `revoke`, refresh refusé
- Après `revoke-all`, refresh refusé

### Flutter (`mobile/test/security/`)

- Format UUID du `device_id` généré
- Logique pure `shouldRequireResumeUnlock` (seuil 45 s)

## Compatibilité Phase 1

- Clients sans `X-Device-ID` : `device_id = legacy-unknown` côté serveur et dans le JWT ; ils **doivent** continuer à omettre l’en-tête de façon cohérente (sinon mismatch).
- Anciens refresh **sans** claim `device_id` : **un** refresh réussi peut créer la session Phase 2 et consommer le jti legacy ; rejeu du même jeton → 401.
- Passcode / biométrie / secure storage : inchangés ; pas de secret utilisateur côté serveur.

## Refresh volé — scénario

1. Attaquant vole le refresh **avant** rotation : il peut obtenir une nouvelle paire **une fois** ; le jti volé est alors dépensé et la session pointe vers un **nouveau** jti — la victime perd l’usage de l’ancien (détection possible côté client si refresh échoue).
2. Si l’attaquant tente de **rejouer** l’ancien refresh après rotation : `claim_refresh_jti` échoue → 401.

## Remaining Gaps / Next Steps

- **Rate limiting** / anti brute-force sur `/auth/login` et `/auth/refresh` (couche WAF ou middleware).
- **Persistance audit** en base dédiée si SIEM ne lit pas les logs applicatifs.
- **Nettoyage** périodique de `auth_spent_refresh_jti` (rétention > durée de vie max refresh + marge).
- **Mobile :** écran dédié « Session expirée » (au-delà de `clearSession` sur 401) + appel optionnel `revoke-all` depuis les réglages.
- **Phase 3 :** passkeys, moteur de risque, step-up auth.

## Fichiers principaux touchés

- `api/database.py` — modèles `AuthSession`, `AuthSpentRefreshJti`
- `api/alembic/versions/108_auth_sessions_phase2.py`
- `api/auth.py` — `create_refresh_token(email, device_id, jti=...)`
- `api/services/auth/refresh_session.py` — logique métier
- `api/main.py` — routes auth
- `api/schemas.py` — `AuthSessionItem`
- `api/tests/test_auth_refresh.py`
- `mobile/lib/features/security/passcode/data/device_id_service.dart`, `session_api.dart`, `session_service.dart`
- `mobile/lib/features/security/passcode/domain/secure_access_config.dart`, `resume_lock_logic.dart`
- `mobile/lib/features/security/passcode/presentation/screens/passcode_unlock_screen.dart`
- `mobile/lib/features/shell/presentation/screens/main_shell_screen.dart`
- `mobile/test/security/*.dart`
