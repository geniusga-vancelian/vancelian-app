# Executive Summary

Audit **code + tests automatisés** (sans E2E instrumenté sur appareil réel) du modèle **utilisateur backend / session serveur / appareil local / passcode local** après les correctifs récours navigation.

**Confirmé dans le code :**

- Le passcode (hash, sel, lockout, biométrie) est stocké sous des clés **dérivées du claim JWT `sub`** (`PasscodeUserKeys.forBinding` + `PasscodeService._bindingIdFromSession`).
- `AuthLogout.signOut()` → `SessionService.revokeRemoteSession()` / `clearSession()` **sans** appeler `PasscodeService.clearPasscodeAndLockState()`.
- `SessionService.clearSession()` **ne supprime pas** les clés passcode par `sub` (test automatisé).
- Après login OTP réussi, `PostLoginLocalSecurityFlow` envoie vers **PasscodeSetup** si aucun PIN pour le `sub` courant, sinon vers **`AppEntryBootstrap.pushRootReplacingAll(forcePostAuthUnlock: true)`** → écran **déverrouillage PIN** (`PasscodeUnlockScreen`), et non vers `PasscodeSetup`.
- L’entrée app (splash / bootstrap) utilise **`AppEntryBootstrap.resolveInitialRootWidget`**, aligné sur la même logique que `AppEntrySession.resolveUxState()` (session valide + PIN présent → déverrouillage si `requireUnlockWhenPasscodeSet`).

**Non vérifié par exécution E2E sur device :** parcours utilisateur réel bout-en-bout (confirmé **probable** d’après chaîne de navigation auditée).

---

# Preconditions

| Élément | Statut | Référence code |
|--------|--------|----------------|
| PasscodeService scope par `sub` | **Confirmé** | `passcode_service.dart` : `_bindingIdFromSession` → `SessionService.extractJwtSubject` ; `_keys = PasscodeUserKeys.forBinding(_bindingSub)` |
| Clés distinctes par utilisateur | **Confirmé** | `passcode_user_keys.dart` : suffixe `passcodeBindingKeySuffix(jwtSub)` ; test `passcode_user_binding_test.dart` |
| `AuthLogout` n’efface pas le passcode | **Confirmé** | `auth_logout.dart` : `signOut()` n’importe pas / n’appelle pas `PasscodeService` ; doc inline |
| `clearSession` ne touche pas au hash PIN par `sub` | **Confirmé** | `session_service.dart` lignes 91–95 ; test `app_entry_session_routing_test.dart` |
| Post-login routing | **Confirmé** | `post_login_local_security_flow.dart` |
| App entry / `AppEntrySession` | **Confirmé** | `app_entry_session.dart` + `app_entry_bootstrap.dart` |
| `extractJwtSubject` | **Confirmé** | Délègue à `jwtExtractSubject` (`jwt_access_claims.dart`) ; test unitaire |

**Écart de vocabulaire produit vs code :** la destination enum `AppEntryDestination.secureGate` et le flux post-login « sécurisé » aboutissent en pratique à **`PasscodeUnlockScreen`** (et non au widget `SecureGateScreen` intermédiaire, désormais court-circuité au démarrage). **Probable** intention produit : « Secure Gate » = **porte à code PIN / biométrie**.

---

# Scenario A — premier login

| Étape | Attendu | Code |
|-------|---------|------|
| Pas de session | Login0 / welcome | `resolveInitialRootWidget` : `!hasServer` → `WelcomeLandingScreen` |
| Login OTP OK | Jetons stockés | `LoginOtpScreen` → `SessionService.storeTokens` |
| Pas de PIN pour ce `sub` | PasscodeSetup | `PostLoginLocalSecurityFlow` : `!isPasscodeConfigured` → route `passcodeSetupBootstrap` |
| Setup OK | App (puis déverrouillage forcé) | `PasscodeSetupScreen` → `AppEntryBootstrap.pushRootReplacingAll(forcePostAuthUnlock: true)` → `PasscodeUnlockScreen` si `requireUnlockWhenPasscodeSet` |

**Verdict scénario A :** **Confirmé** (chaîne de navigation + logique bootstrap).

---

# Scenario B — même user, relogin après logout

| Étape | Attendu | Code |
|-------|---------|------|
| Logout | Session effacée, PIN **conservé** pour le `sub` | `AuthLogout.signOut` → `clearSession` uniquement sur clés session |
| Re-login OTP | Nouveaux jetons, **même `sub`** (backend : e-mail) | `refresh_session.py` : `data={"sub": email}` |
| PIN déjà présent pour ce `sub` | **Pas** PasscodeSetup ; aller au déverrouillage | `PostLoginLocalSecurityFlow` : `isPasscodeConfigured` → `pushRootReplacingAll(..., forcePostAuthUnlock: true)` → `PasscodeUnlockScreen` |

**Verdict scénario B :** **Confirmé** pour « pas de PasscodeSetup » ; **Confirmé** pour « écran déverrouillage PIN » (équivalent « Secure Gate » produit). **Non exécuté** en E2E device dans cet audit.

---

# Scenario C — autre user, même device

| Étape | Attendu | Code |
|-------|---------|------|
| User B login | `sub` B ≠ `sub` A | JWT payload `sub` |
| Pas de hash pour clés B | `isPasscodeConfigured == false` | `PasscodeService.init` + lecture clés `forBinding(subB)` |
| Routing | PasscodeSetup | `PostLoginLocalSecurityFlow` + `AppEntryBootstrap` |

**Verdict scénario C :** **Confirmé** ; **test automatisé** : `multi-compte : PIN user A en stockage, session user B → passcodeSetup`.

---

# Scenario D — relance app (session valide + PIN)

| Condition | Attendu | Code |
|-----------|---------|------|
| Jetons présents, `isSessionValid` true, PIN configuré pour `sub` | Déverrouillage (cold start) | `AppEntryBootstrap` : `requireUnlockWhenPasscodeSet` → `PasscodeUnlockScreen` |

**Verdict scénario D :** **Confirmé** dans le code. **Non vérifié** par test widget sur `SplashScreen` + bootstrap (seulement logique `AppEntrySession` testée).

---

# Scenario E — session valide sans PIN pour ce `sub`

| Condition | Attendu | Code |
|-----------|---------|------|
| Session OK, aucune entrée hash pour le `sub` courant | PasscodeSetup | `resolveInitialRootWidget` / `resolveUxState` |

**Verdict scénario E :** **Confirmé** ; test : `jeton valide + aucun PIN pour ce sub → passcodeSetup`.

---

# sub Audit

## Extraction (mobile)

- **Fonction :** `SessionService.extractJwtSubject` → `jwtExtractSubject(accessToken)`.
- **Algorithme :** découpage `accessToken.split('.')` ; exige **3 segments** ; décode le payload JSON ; lit `sub` si `String` non vide.
- **Token non-JWT / opaque :** `sub == null` → `PasscodeUserKeys.forBinding(null)` → **clés legacy globales** (`arqx.sec.passcode_hash_b64`, etc.) — **un seul pool** pour l’appareil.

## Backend (confirmé dans le dépôt)

- `api/services/auth/refresh_session.py` : `create_access_token(data={"sub": email})` pour la paire émise dans `_issue_pair_for_session_row`.

## Stabilité

- **Pour un même compte** dont l’e-mail de session ne change pas : **`sub` stable** (égal à cet e-mail). **Confirmé** pour le chemin audité.
- **Si le backend changeait** la valeur de `sub` (ex. passage email → id opaque) sans migration des clés locales : **risque** de traiter l’utilisateur comme « nouveau » (nouveau setup PIN) ou de retomber sur legacy si token non-JWT. **Non vérifié** (pas de scénario serveur alternatif dans cet audit).

## Comportement si `sub` absent (opaque)

- **Confirmé** : repli **legacy** ; **isolation multi-compte non garantie** sur ce mode.

---

# Local Storage Audit

## Passcode / sécurité locale (`FlutterSecureStorage`, par `sub`)

| Donnée | Clé (schéma) |
|--------|----------------|
| Hash PIN | `arqx.sec.passcode_hash_b64.u.<suffix>` ou legacy |
| Sel | `arqx.sec.device_salt_b64.u.<suffix>` |
| Tentatives / lockout | `failed_attempts`, `lock_until_ms`, `lockout_tier`, `lockout_events` (suffixés) |
| Biométrie (préf) | `arqx.sec.biometric_enabled.u.<suffix>` |
| Prénom accueil (miroir) | `arqx.sec.client_greeting_first_name.u.<suffix>` (`PasscodeClientGreetingStorage`) |

## Session (`SessionStorageKeys`)

| Donnée | Clé (extraits) |
|--------|----------------|
| Access / refresh / exp | `arqx.sess.access_token`, `refresh_token`, `access_expires_at_ms` |
| Greeting session | `arqx.sess.greeting_first_name` |
| Claims sécurité JSON | `arqx.sess.security_claims_json` |
| Unlock / sensible / bio compteurs | `last_local_unlock_ms`, `last_sensitive_action_ms`, `bio_*` |
| UX login | `login_last_email`, `login_last_phone_e164` |

## Effacements

| Action | Effet |
|--------|--------|
| **`SessionService.clearSession()`** | Supprime : `access_token`, `refresh_token`, `access_expires_at_ms`, `arqx.sess.greeting_first_name`. **Ne supprime pas** : hash PIN par `sub`, `security_claims_json`, horodatages unlock/sensible, login_last_*, deviceId, etc. (**confirmé** lecture `session_service.dart`). |
| **`AuthLogout.signOut()`** | Même effet session que ci-dessus via `revokeRemoteSession` / `clearSession` ; **pas** de clear passcode (**confirmé**). |
| **« Code oublié »** (`PasscodeUnlockScreen`) | `clearPasscodeAndLockState()` + `clearSession()` + navigation welcome (**confirmé**). |
| **Hard reset lockout** (`PasscodeVerifyHardReset`) | `clearPasscodeAndLockState()` pour le **binding courant** ; unlock écran appelle aussi `clearSession()` (**confirmé** `passcode_unlock_screen.dart` + `passcode_service.dart`). |

**Probable / mineur :** `clearPasscodeAndLockState()` ne supprime pas explicitement `clientGreetingFirstName` par `sub` ; une valeur pourrait rester orpheline pour ce `sub` après « code oublié » (donnée non secrète).

---

# Manual QA

Checklist **à exécuter sur build réel** (staging / prod) — non exécutée dans cet audit automatisé.

1. **Premier login (compte neuf sur device)**  
   - Étapes : installer / vider données app → login OTP → terminer setup PIN.  
   - Attendu : `PasscodeSetup` puis, après confirmation, écran **déverrouillage** ou shell selon config ; **pas** de retour login entre OTP et PIN setup (correctifs navigation récents).

2. **Même user, logout, relogin**  
   - Étapes : déconnexion depuis accueil → login OTP même compte.  
   - Attendu : **pas** de `PasscodeSetup` ; affichage **déverrouillage PIN** (ou biométrie).

3. **User B sur même device**  
   - Étapes : logout → login compte B → compléter OTP.  
   - Attendu : `PasscodeSetup` si B n’a jamais défini de PIN sur **ce** device pour ce `sub`.

4. **Retour user A**  
   - Étapes : logout → login A → OTP.  
   - Attendu : déverrouillage avec le **PIN de A** (pas celui de B).

5. **Cold start**  
   - Étapes : tuer l’app avec session valide + PIN configuré → relancer.  
   - Attendu : une transition principale vers **déverrouillage** (pas double écran spinner intermédiaire — correctif splash/bootstrap).

6. **Code oublié**  
   - Étapes : depuis écran PIN → réinitialiser → confirmer.  
   - Attendu : welcome + session locale vidée ; **nouveau** setup PIN après prochain login.

7. **Optionnel** : compte avec token **non-JWT** (si environnement de test l’expose) — vérifier absence de régression **legacy** (un seul PIN partagé).

---

# Verdict (réponses directes)

| Question | Réponse | Base |
|----------|---------|------|
| Même user relogin → « Secure Gate » (déverrouillage PIN), **pas** PasscodeSetup ? | **OUI** | `PostLoginLocalSecurityFlow` + `AppEntryBootstrap` ; scénario B |
| Autre user → PasscodeSetup si pas de PIN pour ce `sub` ? | **OUI** | Code + test `multi-compte` |
| Passcode isolé entre users (JWT avec `sub` distinct) ? | **OUI** | `PasscodeUserKeys` + tests clés / routing |
| `sub` fiable ? | **À SURVEILLER** | **OUI** tant que JWT 3 segments + `sub` = e-mail stable côté API ; **non** si token opaque (legacy) ou changement de politique `sub` serveur sans migration |

---

# Remaining Risks

1. **Token opaque ou JWT mal formé** : `sub == null` → clés **legacy** partagées — **risque multi-compte** sur ce mode (**confirmé** par code).
2. **`clearSession` partiel** : `security_claims_json`, horodatages unlock/sensible, identifiants login_last_*, restent — **cohérence privacy / UX** à trancher produit (hors scope passcode strict).
3. **Changement futur du `sub` côté backend** : risque de désaligner clés SecureStorage existantes (**non vérifié**).
4. **E2E device** : scénarios A–E **non rejoués** sur iOS/Android réels dans cet audit (**procédure manuelle** ci-dessus).
5. **Tests automatisés** : pas de test widget sur `PostLoginLocalSecurityFlow` ni sur `SplashScreen` + `AppEntryBootstrap` (logique session couverte par `AppEntrySession.resolveDestination` + `clearSession`).

---

# Tests automatisés ajoutés / existants

| Fichier | Couverture |
|---------|------------|
| `test/features/security/passcode/passcode_user_binding_test.dart` | `extractJwtSubject`, unicité des clés par `sub`, legacy si `sub` null |
| `test/features/app_entry/app_entry_session_routing_test.dart` | `clearSession` préserve hash PIN par `sub` ; `resolveDestination` login0 / secureGate / passcodeSetup ; multi-compte A/B |

**Commande :**  
`flutter test test/features/app_entry/app_entry_session_routing_test.dart test/features/security/passcode/passcode_user_binding_test.dart`

---

*Document généré par audit statique du dépôt `services/arquantix/mobile` (+ référence API `refresh_session.py`). Date de référence : alignée sur l’état du code au moment de la rédaction.*
