# BIOMETRIC_LOCAL_RELOCK_REPORT

## Executive Summary

L’accès local à l’app après connexion serveur est renforcé par une **politique biométrique** (Face ID / Touch ID / empreinte), un **moteur de relock** au retour depuis l’arrière-plan, et un **contexte de sécurité minimal** dérivé du JWT (`step_up_otp`, `dtrust`, `auth_str`) sans coupler le client à l’implémentation FastAPI. Le **PIN reste obligatoire** en repli ; l’auth serveur n’est pas remplacée. Les seuils et fenêtres sont centralisés dans `SecureAccessConfig` ; la logique pure vit dans `local_relock_engine.dart` et `biometric_policy_service.dart`.

## Biometric Policy

Fichier : `mobile/lib/features/security/local_access/biometric_policy_service.dart`.

- **`isBiometricAvailable()`** : capteurs / support `local_auth` (matériel).
- **`shouldUseBiometricByDefault()`** : disponibilité matérielle **et** opt-in stocké (`PasscodeService.isBiometricUnlockEnabled`).
- **`shouldRelockNow(...)`** : délègue à `LocalRelockEngine` avec des durées issues de `SecureAccessConfig` ; accepte `lastActiveAt` et/ou `AppLifecycleSecurityContext.backgroundDuration`.
- **`shouldForcePinInsteadOfBiometric(...)`** : PIN d’abord si `step_up_otp` côté snapshot JWT, ou si **≥ 2** échecs biométriques **dans la fenêtre** `biometricFailureRecentWindow` (compteur persisté via `SessionService`).

Les échecs biométriques sont enregistrés sur l’écran de déverrouillage ; un succès (PIN ou biométrie) appelle `SessionService.recordLocalUnlockSuccess()` qui remet le compteur à zéro.

## Relock Engine

Fichier : `mobile/lib/features/security/local_access/local_relock_engine.dart`.

Règles minimales :

- Retour **sans** durée d’arrière-plan connue → pas de relock.
- Durée en arrière-plan **≥ seuil effectif** → relock.
- Contexte **à risque** (`SessionSecuritySnapshot.isElevatedLocalRisk` : step-up JWT ou `dtrust` suspect) → seuil **court** (`resumeRelockAfterHighRisk`), **sans** extension de grâce.
- Contexte normal avec **auth serveur forte** (`auth_str` passkey / webauthn / otp / mfa) ou **action sensible récente** (`touchSensitiveAction`) → seuil effectif allongé jusqu’à `relockMaxGracePeriod` (non cumulatif avec le risque élevé).
- **Debounce** après `lastLocalUnlockAt` (`relockDebounceAfterLocalUnlock`) pour éviter un second relock immédiat après un unlock réussi.

Paramètres : `SecureAccessConfig.resumeRelockAfter`, `resumeRelockAfterHighRisk`, `relockMaxGracePeriod`, `relockDebounceAfterLocalUnlock`.

## Lifecycle Integration

Fichier : `mobile/lib/features/shell/presentation/screens/main_shell_screen.dart`.

- `WidgetsBindingObserver` : `paused` mémorise l’horodatage ; `resumed` appelle `_maybeRequireResumeUnlock`.
- Décision : `SessionService.readSecuritySnapshot()` + `BiometricPolicyService.shouldRelockNow`.
- **Garde** `_resumeUnlockOpen` conservée pour éviter l’empilement de modales / doubles prompts pendant un unlock en cours.
- Navigation : une seule `push` plein écran vers `PasscodeUnlockScreen(popOnSuccess: true)`.

## UX

Fichier : `mobile/lib/features/security/passcode/presentation/screens/passcode_unlock_screen.dart`.

- Texte sobre (accueil + phrase courte), erreurs discrètes (« Autre méthode ? Utilisez votre code. »).
- **Biométrie auto** au premier frame si autorisée par la politique (pas de forçage PIN).
- Bouton principal **« Déverrouiller avec Face ID »** / **Touch ID** / **Empreinte** / **biométrie** via `BiometricAuthService.primaryUnlockLabel()`.
- **« Utiliser le code PIN »** : désactive le déclenchement automatique suivant (pas de boucle de prompts).
- Si la politique impose le PIN d’abord : sous-texte **« Pour cet accès, saisissez votre code. »** sans jargon.

## Tests

Fichiers :

- `mobile/test/security/local_relock_engine_test.dart` — seuils court/long, risque élevé, debounce, grâce auth forte.
- `mobile/test/security/biometric_policy_service_test.dart` — forçage PIN (step-up, échecs récents), `shouldRelockNow` lifecycle.
- `mobile/test/security/session_security_snapshot_test.dart` — décodage JWT claims.

**Limite** : « pas de double navigation » est garanti côté produit par `_resumeUnlockOpen` + debounce moteur ; un test widget/driver pourrait verrouiller la régression sur `Navigator`.

## Remaining Gaps

- **Actions sensibles** : `SessionService.touchSensitiveAction()` existe mais n’est pas encore branché sur les flux métier (virement, clés, etc.) ; sans appels, seule la claim `auth_str` alimente la grâce.
- **Remote Config** : les durées sont des constantes compile-time ; pas d’A/B ni de tuning distant.
- **Indicateur « device suspect » serveur** : seul le libellé `dtrust` JWT est utilisé ; alignement exact des valeurs API ↔ heuristique `isElevatedLocalRisk` à documenter côté backend.
- **Tests d’intégration** : pas de scénario `Navigator` / double `resumed` automatisé dans cette livraison.
