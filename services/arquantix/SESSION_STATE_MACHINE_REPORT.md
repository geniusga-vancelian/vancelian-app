# Rapport — Machine d’état de session (Flutter mobile)

## Partie 1 — Audit de l’existant (avant centralisation)

| Composant | Rôle | Décisions de session « dispersées » |
|-----------|------|-------------------------------------|
| **SessionService** | Stockage secure des jetons, `clearSession`, `refreshAccessToken`, `isSessionValid` | Effets de bord (refresh 401 → clear) — déjà documentés ailleurs |
| **SessionIdentityContext** | Claims JWT + `client.id` bootstrap | Pas d’état UI global |
| **SessionStateMachine** (nouveau) | États applicatifs + transitions | Centralise la logique « où en est la session ? » |
| **LoginOtpScreen / LoginEmailOtpScreen** | OTP → `storeTokens` + navigation | `loginFlowStarted` + `accessTokenPersisted` (via storeTokens) |
| **PasscodeUnlockScreen** | Déverrouillage → `passcodeUnlocked` | Hard reset / `logoutStarted` sur « code oublié » |
| **AppEntryBootstrap** | Cold start + `reconcileSessionLifecycleOnColdStart` + `passcodeUnlocked` si skip unlock | Alignement jetons présents / état |
| **HomeScreen** | Garde token + `homeBootstrapStarted` / `Completed` | Évite bootstrap sans jeton prêt |
| **AuthLogout** | `logoutStarted` avant révocation | Cohérent avec `tokensCleared` en fin de `clearSession` |

**États implicites avant la machine** : « session prête » vs « locked » était déduit du stockage + écrans, sans enum unique.

**Risques** : courses async (corrigées précédemment par guards Home + politique refresh), double vérité possible entre « jeton présent » et « UI autorisée » — la machine réduit la surface en **documentant** les transitions attendues.

---

## Partie 2 — États retenus (`SessionLifecycleState`)

| État | Sens métier | Invariant principal |
|------|-------------|----------------------|
| `anonymous` | Pas de jeton utilisable | Pas d’appels API authentifiés |
| `authenticating` | Flux login / OTP en cours | Pas encore de `accessTokenPersisted` final |
| `authenticatedLocked` | Jetons serveur OK, **garde locale** (PIN) non validée pour l’UI | Home wallet / bootstrap authentifié **interdit** jusqu’à unlock |
| `authenticatedReady` | Prêt pour API + Home authentifiée | Bootstrap authentifié autorisé |
| `bootstrappingHome` | Home charge bootstrap + données | Transition courte |
| `refreshingToken` | Refresh JWT en cours | Entre `refreshStarted` et `refreshSucceeded` / `refreshFailed` / `refreshAborted` ; l’état d’avant refresh est mémorisé pour y revenir (ex. `authenticatedLocked` reste verrouillé après refresh) |
| `expired` | Session invalide après refresh échoué | `tokensCleared` attendu |
| `loggingOut` | Déconnexion en cours | `tokensCleared` attendu |
| `hardResetRequired` | Reset sécurité PIN | `tokensCleared` attendu |
| `authError` | Erreur récupérable | Peu utilisé en v1 |

---

## Partie 3 — Table de transitions (résumé)

Événements clés : `loginFlowStarted`, `accessTokenPersisted`, `passcodeUnlocked`, `homeBootstrapStarted` / `Completed`, `refreshStarted` / `Succeeded` / `Failed` / `Aborted`, `logoutStarted`, `tokensCleared`, `hardResetSecurity`, `coldStartTokensPresent`.

| De → | Événement | Vers (si valide) |
|------|-----------|------------------|
| `anonymous` | `loginFlowStarted` | `authenticating` |
| `authenticating` | `accessTokenPersisted` | `authenticatedLocked` |
| `anonymous` | `accessTokenPersisted` | `authenticatedLocked` |
| `authenticatedLocked` | `passcodeUnlocked` | `authenticatedReady` |
| `authenticatedReady` | `homeBootstrapStarted` | `bootstrappingHome` |
| `bootstrappingHome` | `homeBootstrapCompleted` | `authenticatedReady` |
| `authenticatedReady` | `logoutStarted` | `loggingOut` |
| `*` (hors anonymous) | `tokensCleared` | `anonymous` |
| `authenticatedLocked` | `hardResetSecurity` | `hardResetRequired` |
| `anonymous` | `coldStartTokensPresent` | `authenticatedLocked` |
| `authenticatedReady` / `bootstrappingHome` / `authenticatedLocked` | `refreshStarted` | `refreshingToken` |
| `refreshingToken` | `refreshSucceeded` / `refreshAborted` | retour à l’état mémorisé avant refresh |
| `refreshingToken` | `refreshFailed` | `expired` |

Les transitions **invalides** loggent `session_state_guard_blocked` en debug.

---

## Partie 4 — Responsabilités

| Composant | Responsabilité |
|-----------|----------------|
| **SessionService** | I/O jetons, secure storage, `clearSession` physique |
| **SessionIdentityContext** | `sub`, `personId`, `client.id` bootstrap |
| **SessionStateMachine** | État applicatif + transitions + logs debug |
| **session_lifecycle_reconcile.dart** | Cold start : jetons présents → `coldStartTokensPresent` si `anonymous` |

---

## Partie 5 — Plan de migration progressive

### v1 (réalisé)

Machine + tests + intégration minimale sur chemins critiques (login OTP, `storeTokens`, passcode, logout, hard reset, Home bootstrap, cold start reconcile).

### v2 (réalisé)

1. **Refresh JWT** : `SessionService.refreshAccessToken` émet `refreshStarted`, puis `refreshSucceeded` / `refreshFailed` / `refreshAborted` ; `storeTokens(..., notifySessionLifecycle: false)` pendant le refresh pour éviter un double `accessTokenPersisted` incohérent avec l’état `refreshingToken`.
2. **Restauration d’état après refresh** : `_stateBeforeRefresh` — succès ou abandon reviennent à l’état précédent (ex. `authenticatedLocked` après refresh depuis l’écran verrouillé).
3. **Flux auth homogènes** : `loginFlowStarted` avant connexion passkey (`passkey_login_coordinator`) et avant vérif OTP admin e-mail (`admin_email_otp_login_screen`).
4. **Helpers UI** : `isAnonymous`, `isLocked`, `isReady`, `isBootstrappingHome`, `isRefreshingToken`, `shouldAttemptRefresh`, `canEnterApp`, `canBootstrapHomeAuthenticated` / `canStartAuthenticatedHomeBootstrap`, `shouldBlockAuthenticatedHomeUntilUnlock`, `isAuthenticatedPhase`.
5. **Logs noop** : `tokensCleared` alors que l’état est déjà `anonymous` → `session_state_tokensCleared_noop_already_anonymous` (détail optionnel pour distinguer appels attendus vs suspects en debug).

**Optionnel plus tard** : `ListenableBuilder` global sur la machine pour indicateur debug.

---

## Partie 6 — Garde-fous

| Risque | Mitigation v1 |
|--------|----------------|
| Home bootstrap sans token | Garde Home inchangée + `homeBootstrapStarted` refusé si pas `authenticatedReady` |
| `clearSession` sur succès passcode | **Interdit** : succès PIN n’appelle pas `clearSession` (inchangé) |
| Refresh au mauvais moment | Politique déjà assouplie dans `SessionService` ; machine prête pour refresh explicite |
| Fallback public avec session | `hasSession` + token guard dans Home ; machine en parallèle |

---

## Partie 7 — Logs debug

Préfixe `[SessionStateMachine]` : `session_state_transition`, `session_state_guard_blocked`, `session_state_noop`, `session_state_replace`, `session_state_tokensCleared_noop_already_anonymous` (+ détail optionnel).

---

## Partie 8 — Tests

Fichier : `mobile/test/core/session/session_state_machine_test.dart`

Scénarios : login, `passcodeUnlocked`, bootstrap Home (succès + refus), refresh (ready + locked, succès, abandon, échec), logout, hard reset, cold start, garde tokens, noop `tokensCleared` en `anonymous`, helpers métier.

Commande : `flutter test test/core/session/session_state_machine_test.dart`

---

## Partie 9 — Fichiers ajoutés / modifiés

**Ajoutés**

- `mobile/lib/core/session/session_lifecycle_state.dart`
- `mobile/lib/core/session/session_state_machine.dart`
- `mobile/lib/core/session/session_lifecycle_reconcile.dart`
- `mobile/test/core/session/session_state_machine_test.dart`

**Modifiés**

- `lib/features/security/passcode/data/session_service.dart` — `accessTokenPersisted`, `tokensCleared`, `storeTokens(notifySessionLifecycle)`, `refreshAccessToken` + événements refresh
- `lib/features/security/passkeys/presentation/passkey_login_coordinator.dart` — `loginFlowStarted`
- `lib/features/security/passkeys/presentation/admin_email_otp_login_screen.dart` — `loginFlowStarted`
- `lib/features/security/passcode/presentation/screens/passcode_unlock_screen.dart`
- `lib/features/security/login/presentation/login_otp_screen.dart`
- `lib/features/security/login/presentation/login_email_otp_screen.dart`
- `lib/features/app_entry/application/app_entry_bootstrap.dart`
- `lib/features/home/presentation/screens/home_screen.dart`
- `lib/features/auth/application/auth_logout.dart`

---

## Limites restantes

- **Mémoire process** : au redémarrage app, l’état machine repart en `anonymous` puis `reconcileSessionLifecycleOnColdStart` restaure `authenticatedLocked` si jetons présents.
- **`isSessionValid` échoue** au cold start : retour Welcome **sans** forcer la machine en `anonymous` si les jetons restent stockés (évite incohérence ; alignement futur possible avec `SessionService`).
- **UI** : les écrans peuvent encore mélanger conditions locales et machine — les helpers v2 réduisent la dette ; migration progressive possible.

---

## Validation

- `flutter test test/core/session/session_state_machine_test.dart` : **OK** (14 tests).
- Contraintes produit : login / registration / passcode / Home — intégration par **hooks** ; refresh et flux passkey / admin OTP alignés sur les mêmes événements que la v1.
