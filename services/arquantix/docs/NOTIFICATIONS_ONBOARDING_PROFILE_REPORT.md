# Notifications Onboarding and Profile Integration Report

## Files Created

- `services/arquantix/mobile/lib/features/security/passcode/domain/push_notification_onboarding_prompt_state.dart` — Enum produit local (`neverSeen`, `enabled`, `skippedRegistration`, `skippedFirstRelogin`) persisté avec le passcode (par `sub` JWT).

- `services/arquantix/mobile/lib/features/app_entry/application/post_auth_navigation_flags.dart` — Drapeau one-shot pour supprimer le re-prompt push sur la **première** montée du shell juste après la fin d’inscription.

- `services/arquantix/mobile/lib/features/profile/presentation/screens/notification_settings_screen.dart` — Écran Profil > Notifications : titre, texte d’intro, carte avec interrupteur « Toutes les notifications », demande de permission OS à l’activation, PATCH best-effort aligné sur le flux push existant.

- `services/arquantix/docs/NOTIFICATIONS_ONBOARDING_PROFILE_REPORT.md` — Ce rapport (structure demandée).

- `services/arquantix/mobile/test/security/push_notification_onboarding_prompt_test.dart` — Tests ciblés sur l’enum et les règles `SecurityPreferencesCoordinator` (registration vs re-login).

## Files Updated

- `services/arquantix/mobile/lib/features/security/passcode/domain/passcode_storage_keys.dart` — Clés SecureStorage pour l’état d’onboarding push et la préférence globale locale.

- `services/arquantix/mobile/lib/features/security/passcode/domain/passcode_user_keys.dart` — Même clés scoping par utilisateur (et legacy).

- `services/arquantix/mobile/lib/features/security/passcode/data/passcode_service.dart` — Lecture/écriture état onboarding push, préférence « toutes les notifs », migration legacy → utilisateur, purge avec `clearPasscodeAndLockState`.

- `services/arquantix/mobile/lib/features/app_entry/application/app_entry_bootstrap.dart` — Paramètre `suppressNextMainShellPushReloginPrompt` sur `pushRootReplacingAll`.

- `services/arquantix/mobile/lib/features/registration/screens/registration_flow_screen.dart` — Après OTP : si état local `neverSeen`, présentation de `PushNotificationsOnboardingScreen(kind: registration)` puis `_goNext()` (vers création du code, etc.) ; fin de session : `suppressNextMainShellPushReloginPrompt: true` lors du passage au shell.

- `services/arquantix/mobile/lib/features/security/onboarding/push_notifications_onboarding_screen.dart` — `PushNotificationsOnboardingKind` (registration / reloginReprompt), persistance locale avant sync, libellé secondaire « Passer pour l’instant », feedback si permission refusée à l’activation.

- `services/arquantix/mobile/lib/features/shell/presentation/screens/main_shell_screen.dart` — Après le premier frame : si `skippedRegistration` et pas de suppression one-shot, ouverture du modal re-prompt (`reloginReprompt`).

- `services/arquantix/mobile/lib/features/profile/application/security_preferences_coordinator.dart` — `shouldOfferRegistrationPushOnboarding` et `shouldOfferReloginPushOnboarding` (documentation ; la logique d’écran utilise surtout `PasscodeService` directement).

- `services/arquantix/mobile/lib/features/profile/presentation/screens/profile_screen.dart` — Entrée « Notifications » (icône + chevron) vers `NotificationSettingsScreen` ; suppression de l’interrupteur push inline dans « Paramètres ».

## Registration Flow Changes

- L’écran onboarding push est inséré dans le **callback `onCompleted`** du panneau `RegistrationPhoneSmsOtpPanel` : après `_refreshSession()` (session serveur avancée après OTP), le client lit `PasscodeService.getPushOnboardingPromptState()`.

- Si la valeur est **`neverSeen`**, on affiche le modal **avant** `_goNext()`, ce qui place bien l’étape **entre confirmation SMS/OTP et l’écran suivant** du parcours serveur (typiquement création du code / étapes suivantes), sans dépendre d’un `fetchProfile` réussi (correctif du trou précédent).

## Re-Prompt Logic

- **Skip à l’inscription** → état local `skippedRegistration` + préférence locale désactivée ; sync push best-effort comme avant.

- **Fin d’inscription** → `AppEntryBootstrap.pushRootReplacingAll(..., suppressNextMainShellPushReloginPrompt: true)` : le **premier** `MainShellScreen` ne déclenche **pas** le re-prompt (évite boucle / double demande dans la même montée).

- **Sessions suivantes** : au premier frame de `MainShellScreen`, si état `skippedRegistration` et pas de suppression active, ouverture **une fois** de `PushNotificationsOnboardingScreen(kind: reloginReprompt)`.

- **Skip au re-prompt** → `skippedFirstRelogin` : plus d’invite automatique ; l’utilisateur peut activer depuis Profil.

- **Activation** (inscription ou re-prompt) → `enabled` + préférence locale à vrai ; pas de re-prompt ultérieur.

## Profile Notifications Screen

- Structure : `PageSimpleNavBarTopTitlePageContent`, texte d’intro, `SettingsCard` + `SettingsListItem` avec `AppToggleSwitch`.

- **ON** : `Permission.notification.request()` ; si accord (ou équivalent limité/provisional), persistance locale + état `enabled` + PATCH asynchrone ; sinon snackbar explicite, interrupteur reste à faux.

- **OFF** : préférence locale à faux, PATCH `onboarding_outcome: disabled` best-effort ; l’état d’onboarding produit n’est pas forcé vers `skippedFirstRelogin` (réservé aux flux onboarding).

## State Model Implemented

- **`PushNotificationOnboardingPromptState`** (SecureStorage, clés par utilisateur) :  
  `never_seen` → `enabled` | `skipped_registration` → (`skipped_first_relogin` après second skip ou `enabled`).

- **`pushNotificationsPreferenceEnabled`** (`1`/`0`) : reflet immédiat pour l’UI « toutes les notifications ».

- Le **backend** reste en **best-effort** via `MobileProfileApi.patchSecurityPreferencesV1` + `SecurityPreferencesSyncService` (retry), comme pour la biométrie / push existant.

## Permission Handling

- **Onboarding — Activer** : demande OS ; refus → message clair, pas de changement d’état local « enable », l’utilisateur peut utiliser « Passer pour l’instant ».

- **Onboarding — Passer** : pas de permission ; état skip + sync `preference_enabled: false`, `onboarding_outcome: skipped`.

- **Profil — interrupteur ON** : même logique de demande ; refus → snackbar + toggle visuellement OFF.

- **Profil — interrupteur OFF** : pas de modale obligatoire ; désactivation directe + sync.

## Tests Added or Updated

- `services/arquantix/mobile/test/security/push_notification_onboarding_prompt_test.dart` : parsing des valeurs stockées ; `shouldOfferRegistrationPushOnboarding` (uniquement `neverSeen`) ; `shouldOfferReloginPushOnboarding` (uniquement `skippedRegistration`).

- (Les scénarios **E2E** device / navigation shell complets restent à couvrir par tests d’intégration ou manuels si besoin.)

## Remaining TODOs

- Centre de notifications **granulaire** (catégories, seuils, historique).

- Cohérence **email** / autres canaux avec le même hub « Notifications » si le produit unifie les réglages.

- Métriques analytics sur les outcomes (`skipped` vs `enabled`) par source (`registration` vs `relogin_reprompt`).

- Tests widget/integration : enchaînement OTP → modal → `_goNext`, et MainShell + `skippedRegistration` sans flag suppress.
