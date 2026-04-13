# Rapport — Bootstrap Home après login mobile + passcode

## Résumé exécutif

**Symptôme** : après saisie du numéro mobile, validation OTP, puis déverrouillage par passcode, la Home ne charge pas les données liées au client connecté (cash, crypto, bootstrap, etc.).

**Cause racine identifiée (Flutter)** : sur le chemin **déverrouillage passcode → `MainShellScreen` → `HomeScreen`**, le code appelait `SessionService.isSessionValid()` dans `PasscodeUnlockScreen._enterApp()`. Cette méthode peut déclencher un **`refreshAccessToken()`** vers l’API d’auth FastAPI. Lorsque le refresh répond **401**, `SessionService.refreshAccessToken()` appelle **`clearSession()`**, ce qui **efface l’access token (et le contexte d’identité)** *avant* la navigation vers la Home. Les requêtes suivantes (`GET /api/mobile/flutter/bootstrap`, `cash`, etc.) partent alors **sans en-tête `Authorization`**.

**Facteur aggravant** : `shouldRefreshAccessToken()` retournait **`true` dès qu’un jeton était présent mais qu’aucune date d’expiration locale n’était stockée** (`accessExpiresAtMs` absent après `storeTokens` sans `accessExpiresAt`). Le login OTP n’envoyait pas systématiquement cette date ; le refresh était donc **systématiquement tenté** au déverrouillage, maximisant le risque d’effacement de session si le refresh échoue.

**Correctifs appliqués** :

1. **`PasscodeUnlockScreen._enterApp`** : suppression de l’appel à `isSessionValid()` ; synchronisation explicite de `SessionIdentityContext` avec le jeton lu localement après déverrouillage (sans refresh bloquant).
2. **`SessionService.storeTokens`** : si `accessExpiresAt` n’est pas fourni, **persistance de l’expiration depuis le claim JWT `exp`** (`jwtExtractExpiryMs`).
3. **`SessionService.shouldRefreshAccessToken`** : si aucune expiration n’est connue ni en stockage ni dans le JWT, **ne pas forcer de refresh** (évite le scénario « refresh agressif + 401 » au déverrouillage).

**Logs d’audit (temporaires / dev)** : Flutter (`kDebugMode`), BFF bootstrap (`NODE_ENV !== 'production'`), API (`mobile_identity: bearer_resolved`).

---

## Partie 1 — Audit Flutter

### 1. Stockage du token après login / passcode

- **Login OTP** : `LoginOtpScreen` → `SessionService.storeTokens(accessToken:, refreshToken:)` — jetons en **Flutter Secure Storage**.
- **Passcode** : le PIN est local ; il ne modifie pas les jetons. **Exception** : ancien code appelait `isSessionValid()` après succès PIN, ce qui pouvait **supprimer** les jetons (voir cause racine).

### 2. Moment où la session est « prête »

- **Après OTP** : `storeTokens` termine → `SessionIdentityContext.syncFromAccessToken` (fin de `storeTokens`).
- **Après déverrouillage** : désormais `syncFromAccessToken` explicite dans `_enterApp` si un access token est lu.
- **`HomeScreen._loadAll`** : si `hasSessionCredentials()`, attente `ensureAccessTokenReadyForDashboard()` (course token → premier frame).

### 3. Navigation vers Home

- Post-login : `PostLoginLocalSecurityFlow.navigateReplacingLoginStack` → setup PIN ou `AppEntryBootstrap.pushRootReplacingAll(forcePostAuthUnlock: true)` → **`PasscodeUnlockScreen`** → succès → **`MainShellScreen`** (onglet Home = `HomeScreen`).
- Cold start avec session : `AppEntryBootstrap` → unlock → même enchaînement.

### 4. Quand le bootstrap Home est déclenché

- `HomeScreen.initState` → `_loadAll` → `_loadBootstrap` puis chargements parallèles (layout, feed, cash, crypto, etc.).

### 5. Bearer sur les requêtes Home

- `_loadBootstrap` : `Authorization: Bearer <accessToken>` si token non vide.
- `CashApi` et autres APIs wallet : même pattern via `SessionService.readAccessToken()`.

**Si `clearSession()` a été appelé avant** : pas de Bearer → bootstrap anonyme (selon env) ou 401.

### 6. Cache / état local

- `CurrencyPreference` / `ProfileLeadingPreference` : réinitialisés au logout / changement de `sub` (`SessionService`).
- Pas de `selectedClient` multi-comptes côté mobile dans ce flux : le client courant vient du **JWT + résolution backend**.

---

## Partie 2 — Audit BFF / API

### 1. Header Authorization côté BFF

- `GET /api/mobile/flutter/bootstrap` : `upstreamHeadersWithAuth(request)` reprend `request.headers.get('authorization')` et le transmet au backend.

### 2. Forward vers l’API Python

- `buildBackendUrl('/api/app/bootstrap')` + headers avec `Authorization` si présent côté client.

### 3. Résolution user / person / client

- `services/test_clients/mobile_identity.py` : `decode_bearer_payload` → `pe_client_from_jwt_payload` (`person_id` / `pid` / `sub` email) → `PeClient`.

### 4. Réponses possibles pour la Home

| Cas | Comportement |
|-----|----------------|
| Bearer valide + `PeClient` lié | **200** + JSON `client` |
| Bearer invalide / expiré | **401** |
| Bearer valide, aucun `PeClient` | **404** « No client profile… » |
| Pas de Bearer | **401** (prod) ou client test si `ARQUANTIX_ALLOW_UNAUTHENTICATED_APP_ROUTES=1` (dev) |

### 5. Rail legacy

- Le seul « anonyme » documenté est le **client test** lorsque la variable d’env ci-dessus est activée **et** qu’il n’y a pas de Bearer — pas un bootstrap « silencieux » avec utilisateur connecté si le Bearer est correctement envoyé.

---

## Partie 3 — Logs ciblés ajoutés

| Couche | Fichier | Contenu |
|--------|---------|---------|
| Flutter | `home_screen.dart` | `[HomeScreen][session]`, `[HomeScreen][bootstrap] bearer=… status=…` (debug uniquement) |
| BFF | `bootstrap/route.ts` | `Authorization header present: true/false` (hors production) |
| API | `mobile_identity.py` | `mobile_identity: bearer_resolved client_id=… person_id=…` |

Aucun jeton complet n’est loggé.

---

## Partie 4 — Correctif (rappel)

- **Ne plus** invalider la session locale au simple passage déverrouillage passcode via refresh 401.
- **Persister `exp` JWT** pour des décisions de refresh cohérentes.
- **Ne pas** considérer « refresh obligatoire » sans date d’expiration connue.

---

## Partie 5 — Validation manuelle recommandée

1. Login utilisateur existant (OTP) → passcode → Home : **soldes / bootstrap** cohérents avec le compte.
2. **Cold start** : session + PIN → unlock → Home : données présentes.
3. **Logout** puis **login autre utilisateur** : pas de données du compte précédent.
4. Vérifier les logs debug / serveur : `bearer=true`, status bootstrap **200**, logs API `bearer_resolved` avec le bon `client_id`.

---

## Fichiers modifiés (piste de revue)

- `mobile/.../passcode_unlock_screen.dart` — `_enterApp`
- `mobile/.../session_service.dart` — `storeTokens`, `shouldRefreshAccessToken`
- `mobile/.../jwt_access_claims.dart` — `jwtExtractExpiryMs`
- `mobile/.../home_screen.dart` — logs debug
- `web/.../bootstrap/route.ts` — log présence Authorization
- `api/.../mobile_identity.py` — log résolution Bearer

---

## Conclusion

Le dysfonctionnement était **principalement côté Flutter** : effacement de session déclenché par la politique de **refresh JWT** au mauvais moment (après passcode), combiné à une **politique de refresh trop agressive** lorsque l’expiration n’était pas stockée. Le BFF et l’API se comportent comme attendus lorsque le **Bearer** est présent et valide.
