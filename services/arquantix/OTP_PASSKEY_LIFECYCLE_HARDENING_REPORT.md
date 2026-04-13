# Executive Summary

Les écrans **OTP SMS** (`LoginOtpScreen`), **OTP e-mail** (`LoginEmailOtpScreen`) et le **fallback e-mail / passkey** (`LoginEmailFallbackScreen`) observent désormais le cycle de vie de l’app via un **`AuthFlowLifecycleObserver`** dédié. Après un **retour au premier plan** alors que l’app était en **pause** depuis au moins **`AuthFlowLifecycleConfig.backgroundStaleThreshold`** (défaut **5 minutes**, ajustable pour les tests), le flux sensible est **invalidé** : timers annulés, flags / génération OTP remis à zéro, événements debug, message utilisateur, puis **retour à l’accueil connexion** (OTP) ou **SnackBar** (passkey, sans quitter la page si l’utilisateur peut choisir une autre méthode). Le flux normal **dans la même session** et les retours courts du multitâche **ne sont pas affectés**.

# Current Behavior

| Zone | Comportement |
|------|----------------|
| **OTP SMS / e-mail** | `WidgetsBinding` + `AuthFlowLifecycleObserver` : à `paused` on mémorise l’instant ; à `resumed`, si `now - pausedAt >= seuil`, callback → reset + modale « Session expirée, veuillez recommencer » → `popUntil(isFirst)` ou `WelcomeLandingScreen`. |
| **Passkey (fallback)** | Même observer ; invalidation → `_busy` / `_autoPasskeyScheduled` remis à false, `auth.passkey_flow_invalidated_on_resume`, SnackBar « Authentification interrompue, utilisez une autre méthode ». Le **`PasskeyLoginCoordinator`** reste la source métier ; l’écran évite un état « bloqué » après absence longue. |
| **Cold start** | Non couvert ici : une fois le process tué, la pile Flutter disparaît ; le durcissement **passcode / session** existant reste la ligne de défense. |
| **Événements debug** | `PostAuthFlowSecurityEvents.otpFlowInvalidatedOnResume` et `.passkeyFlowInvalidatedOnResume` (`kDebugMode` uniquement). |

# Problems

- Après **background prolongé**, un écran OTP pouvait garder **timer actif**, **challenge / contexte** perçu comme valide et **tentatives de vérif** sans resynchronisation claire avec le backend.
- Le **mixin** `State` + `WidgetsBindingObserver` posait des **exigences d’API** strictes sur toutes les méthodes de l’observer ; une **classe déléguée** évite ce couplage.
- Les **tests widget** qui simulent le cycle de vie doivent respecter la **machine d’états** de Flutter 3.41+ (`inactive` → `hidden` → `paused`, etc.), sinon le binding lève une assertion.

# Lifecycle Detection

- **`AuthFlowLifecycleObserver`** : `didChangeAppLifecycleState` — `paused` enregistre l’horodatage ; `resumed` compare à `DateTime.now()` avec `authFlowShouldInvalidateAfterBackground` (logique pure, testée unitairement).
- **`AuthFlowLifecycleConfig.backgroundStaleThreshold`** : durée minimale « douteuse » (défaut 5 min ; tests : `Duration.zero`).
- Pas de détection « inactivité sans pause » : uniquement **pause → reprise** avec seuil temporel.

# UI Policy

- **OTP** : interruption significative (durée ≥ seuil) → **invalider**, **ne pas resoumettre** automatiquement, **retour login** (accueil).
- **Passkey** : même critère temporel → **réinitialiser l’état UI** et **message** invitant à **changer de méthode** ; le fallback OTP existant (`onFallback` dans le coordinator) reste disponible pour **indisponibilité passkey** au moment de l’appel, pas pour le seul lifecycle (comportement inchangé côté coordinator).

# Changes Applied

- **`mobile/lib/features/security/login/application/auth_flow_lifecycle_guard.dart`** : `AuthFlowLifecycleConfig`, `authFlowShouldInvalidateAfterBackground`, `AuthFlowLifecycleObserver`.
- **`mobile/lib/core/post_auth_flow_security_events.dart`** : `otpFlowInvalidatedOnResume`, `passkeyFlowInvalidatedOnResume`.
- **`login_otp_screen.dart`**, **`login_email_otp_screen.dart`** : enregistrement / retrait de l’observer, invalidation (timer, `_otpGen`, navigation).
- **`login_email_fallback_screen.dart`** : migration vers `AuthFlowLifecycleObserver` (plus de mixin obsolète).
- **`passkey_login_coordinator.dart`** : commentaire pointant vers l’observer pour le lifecycle côté UI.
- **`test/features/security/login/auth_flow_lifecycle_guard_test.dart`** : tests de la fonction pure.
- **`test/features/security/login/login_otp_screen_test.dart`** : scénario « background prolongé » avec séquence de cycle de vie valide pour Flutter 3.41+.

# UX Improvements

- Messages imposés : **« Session expirée, veuillez recommencer »** (OTP) ; **« Authentification interrompue, utilisez une autre méthode »** (passkey / fallback).
- Flux inchangé si l’utilisateur **revient rapidement** (sous le seuil).

# Tests

| Test | Rôle |
|------|------|
| `auth_flow_lifecycle_guard_test.dart` | Seuil atteint / non atteint / `pausedAt` null. |
| `login_otp_screen_test.dart` | « Background prolongé » (seuil à zéro) → modale + OK. |

**Manuel recommandé** : OTP → kill → rouvrir (vérifier landing / pas d’OTP fantôme) ; OTP → background long → reprise ; passkey → interruption → vérifier message + possibilité **code e-mail** ; flux nominal OTP inchangé.

# Final Verdict

Objectif atteint **sans sur-ingénierie** : invalidation **ciblée** des états douteux après **reprise tardive**, orchestration **locale** alignée sur le backend déjà sécurisé, **UX** claire et **tests** automatisés sur la logique et un écran OTP représentatif.

# Remaining Gaps

- **Inactivité sans `paused`** (app toujours au premier plan) : non couvert ; faible risque pour OTP typique.
- **Tests widget** pour `LoginEmailOtpScreen` / `LoginEmailFallbackScreen` : optionnels ; la logique partagée est déjà testée au niveau **guard** + **SMS OTP**.
- **Kill process** : pas de réhydratation d’écran OTP côté Flutter sans état restauré ; si la restauration d’état OS était activée un jour, il faudrait **refuser** la reprise sur ces routes.
