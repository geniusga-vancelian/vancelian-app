# APP_ENTRY_ROUTING_AND_POST_LOGIN_FLOW_REPORT.md

## Executive Summary

Le routage d’entrée et le flux post-login mobile ont été **orchestrés** sans refondre la stack auth serveur ni `SessionService`. Un **routeur maître** (`AppEntryRouter`) s’exécute après le splash ; une couche **`PostLoginLocalSecurityFlow`** enchaîne **configuration PIN** ou **Secure Gate** après OTP / passkey / e-mail OTP. Les routes nommées (`AppNavRoutes`) évitent un import circulaire entre `PasscodeSetupScreen` et `SecureGateScreen`. Les helpers **`AppEntrySession`** centralisent les critères « session serveur » vs « PIN local ».

## Current Flow Audit (avant changement)

| Situation | Comportement historique |
|-----------|-------------------------|
| Aucune session locale | Splash → `SecureGateScreen` → sans PIN → **`MainShellScreen` direct** (pas de Login0). |
| Session locale + PIN | Splash → Secure Gate → `PasscodeUnlockScreen` → MainShell. |
| Tokens présents, PIN absent | Accès **dashboard sans configuration PIN** (faille produit / UX). |
| Après OTP SMS valide | `LoginOtpScreen` stocke les tokens puis `pop(true)` ; `WelcomeLandingScreen` faisait **`pushReplacement(MainShellScreen)`** — **pas de Secure Gate ni setup PIN**. |
| Navigations | `SplashScreen` : `pushReplacement` → `SecureGateScreen`. `WelcomeLandingScreen._onLogin` : `push` LoginPhone puis `pushReplacement` MainShell si succès. |

## Target Routing Logic

1. **Entrée app** : Splash → **`AppEntryRouter`** (décision async unique).
2. **Pas de session serveur exploitable** → **Login0** (`WelcomeLandingScreen`).
3. **Session valide, pas de PIN** → **`PasscodeSetupScreen`** (mode bootstrap / post-login).
4. **Session valide + PIN** → **`SecureGateScreen`** → `PasscodeUnlockScreen` si `requireUnlockWhenPasscodeSet`, sinon `MainShellScreen`.
5. **Post-login serveur** (OTP, passkey, e-mail OTP) : après `storeTokens`, **`PostLoginLocalSecurityFlow.navigateReplacingLoginStack`** → setup PIN ou `SecureGateScreen(forceUnlock: true)` puis déverrouillage → MainShell.

## App Entry Router

- **Fichier** : `lib/features/app_entry/presentation/app_entry_router.dart`
- **Décision** : `AppEntrySession.resolveDestination()` → `login0` | `passcodeSetup` | `secureGate`
- **Tests** : `resolveDestinationOverride` pour court-circuiter le stockage réel.

## Post-Login Flow

- **Fichier** : `lib/features/app_entry/application/post_login_local_security_flow.dart`
- **Appelé depuis** : `WelcomeLandingScreen._onLogin` après succès du flux `LoginPhoneScreen` (OTP / passkey / e-mail inclus via `pop(true)`).
- **Comportement** :
  - Pas de PIN → `pushNamedAndRemoveUntil(AppNavRoutes.passcodeSetupBootstrap, …)`
  - PIN déjà là → `pushNamedAndRemoveUntil(AppNavRoutes.secureGatePostAuth, …)` (`forceUnlock: true` pour garder le passage local même si la config produit évolue).

## Secure Gate Integration

- **`SecureGateScreen`** : vérifie **session serveur** (`hasSessionCredentials` + `isSessionValid`) ; si invalide → **Login0** (route nommée). Si pas de PIN → **route bootstrap** setup. Sinon déverrouillage ou MainShell selon `SecureAccessConfig.requireUnlockWhenPasscodeSet` et `forceUnlock`.
- **`PasscodeUnlockScreen`** : inchangé pour biométrie / PIN ; **« Code oublié »** redirige vers **Login0** via `PostLoginLocalSecurityFlow.navigateToLogin0ReplacingStack` (plus de MainShell avec session effacée).

## Routes nommées

- **Fichier** : `lib/core/app_nav_routes.dart`
- **Enregistrement** : `MaterialApp.routes` dans `lib/app.dart`
- **But** : `PasscodeSetupScreen` peut enchaîner vers Secure Gate **sans** importer `SecureGateScreen`.

## Session Service Checks

Centralisés dans **`AppEntrySession`** (`lib/features/app_entry/domain/app_entry_session.dart`) :

- `hasStoredTokens()` → délègue `SessionService.hasSessionCredentials()`
- `hasValidServerSession()` → jetons + `isSessionValid()` (refresh / clear inchangés)
- `hasPasscodeConfigured()` → `PasscodeService.init()` + `isPasscodeConfigured`
- `shouldOpenSecureGate()` → session valide **et** PIN configuré
- `resolveUxState()` → état UX explicite

Fonction pure **`resolveAppEntryDestination(...)`** dans `app_entry_destination.dart` pour les tests sans I/O.

## UX States

| État | Où c’est porté |
|------|----------------|
| `logged_out` | `AppEntryUxState.loggedOut` → destination `login0` |
| `server_authenticated_but_local_security_not_setup` | `…NotSetup` → `passcodeSetup` |
| `server_authenticated_and_local_security_ready` | `…Ready` → `secureGate` |
| `unlocking_local_access` | `PasscodeUnlockScreen` / biométrie (pas une destination du routeur bootstrap ; fallback `secureGate` si jamais utilisé dans `resolveDestination`) |

## Tests

- `test/features/app_entry/app_entry_destination_test.dart` — matrice `resolveAppEntryDestination` + `destinationForUxState(unlocking)` → null.
- `test/features/app_entry/app_entry_router_test.dart` — `AppEntryRouter` avec override ; Login0 = `WelcomeLandingScreen` ; PasscodeSetup = widget attendu ; route nommée `welcome`.

**Non couverts en widget test** (dépendent de SecureStorage / async Secure Gate) : scénarios OTP réel, Secure Gate → MainShell ; prévoir **tests d’intégration** ou mocks de `SessionService` / `PasscodeService` si besoin CI strict.

## Remaining Gaps

1. **Inscription** : si un parcours d’enregistrement pose des tokens et pousse un écran « principal » sans passer par `PostLoginLocalSecurityFlow`, aligner sur le même helper.
2. **Entrées alternatives** : tout écran qui appelle `LoginEmailFallbackScreen` / OTP **hors** `WelcomeLandingScreen` doit terminer par `PostLoginLocalSecurityFlow` si l’objectif est le même contrat produit.
3. **`forceUnlock`** : aujourd’hui `true` force le déverrouillage local si `requireUnlockWhenPasscodeSet` est `false` (filet produit) ; à documenter côté produit si la config change.
4. **Tests E2E** : enchaînement complet OTP → setup PIN → biométrie → MainShell.

## Fichiers touchés (référence)

- `lib/app.dart` — `routes` + imports
- `lib/core/app_nav_routes.dart` — **nouveau**
- `lib/features/app_entry/**` — **nouveau** (domain, router, post-login)
- `lib/features/splash/presentation/screens/splash_screen.dart` → `AppEntryRouter`
- `lib/features/auth/presentation/screens/welcome_landing_screen.dart` → `PostLoginLocalSecurityFlow`
- `lib/features/security/passcode/presentation/screens/secure_gate_screen.dart` — session + routes nommées
- `lib/features/security/passcode/presentation/screens/passcode_setup_screen.dart` — `PasscodeSetupOnSuccess`
- `lib/features/security/passcode/presentation/screens/passcode_unlock_screen.dart` — reset → Login0
