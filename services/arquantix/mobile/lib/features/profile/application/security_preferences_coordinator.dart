import '../../security/passcode/data/passcode_service.dart';
import '../../security/passcode/domain/biometric_onboarding_prompt_state.dart';
import '../../security/passcode/domain/push_notification_onboarding_prompt_state.dart';
import '../domain/security_preferences_models.dart';

/// Décisions d’affichage onboarding (backend + état local explicite).
class SecurityPreferencesCoordinator {
  SecurityPreferencesCoordinator._();

  /// Gate **bloquant** biométrie.
  ///
  /// Politique produit :
  /// - [BiometricOnboardingPromptState.enabled] → ne plus afficher.
  /// - [skipped] → **ré-afficher** à chaque déverrouillage (ignore le flag backend « completed »).
  /// - [unavailable] → ne pas bloquer (pas de boucle sur appareil incompatible).
  /// - [neverSeen] → afficher seulement si le backend indique encore un onboarding à faire.
  ///
  /// Si profil indisponible (`null`), ne pas bloquer (évite boucle réseau).
  static bool shouldShowBlockingBiometricOnboarding(
    MobileSecurityPreferences? sp, {
    required BiometricOnboardingPromptState localPromptState,
  }) {
    switch (localPromptState) {
      case BiometricOnboardingPromptState.enabled:
        return false;
      case BiometricOnboardingPromptState.unavailable:
        return false;
      case BiometricOnboardingPromptState.skipped:
        return true;
      case BiometricOnboardingPromptState.neverSeen:
        if (sp == null) return false;
        return !sp.isBiometricOnboardingCompleted;
    }
  }

  /// Gate onboarding push **côté backend** (outil / diagnostics). Le parcours inscription
  /// utilise [shouldOfferRegistrationPushOnboarding] (état local prioritaire).
  static bool shouldShowBlockingPushOnboarding(
    MobileSecurityPreferences? sp,
  ) {
    if (sp == null) return false;
    return !sp.isPushOnboardingCompleted;
  }

  /// Premier prompt automatique **post-auth** (OTP, etc.) lorsque [neverSeen] : anti-spam
  /// via cooldown 24h sur [lastAutomaticPromptAt] (même clé stockage que l’écran affiché).
  ///
  /// Nom historique « registration » : le gate vit aussi dans [PostLoginLocalSecurityFlow],
  /// pas seulement dans le parcours KYC.
  static bool shouldOfferRegistrationPushOnboarding(
    PushNotificationOnboardingPromptState local, {
    DateTime? lastAutomaticPromptAt,
    DateTime? now,
  }) {
    if (local != PushNotificationOnboardingPromptState.neverSeen) {
      return false;
    }
    final clock = now ?? DateTime.now();
    return !PasscodeService.isWithinAutomaticPushOnboardingCooldown(
      lastAutomaticPromptAt,
      clock,
    );
  }

  /// Alias explicite — même logique que [shouldOfferRegistrationPushOnboarding].
  static bool shouldOfferPostAuthInitialPushOnboarding(
    PushNotificationOnboardingPromptState local, {
    DateTime? lastAutomaticPromptAt,
    DateTime? now,
  }) =>
      shouldOfferRegistrationPushOnboarding(
        local,
        lastAutomaticPromptAt: lastAutomaticPromptAt,
        now: now,
      );

  /// Re-prompt au **premier** chargement du shell après « skip » à l’inscription.
  ///
  /// **Ne pas** appliquer le cooldown 24h ici : le timestamp d’affichage du prompt
  /// inscription/post-auth est le même que pour ce gate ; sinon un skip récent bloquerait
  /// la promesse produit « une seconde chance à la première vraie reprise ».
  static bool shouldOfferReloginPushOnboarding(
    PushNotificationOnboardingPromptState local,
  ) {
    if (local != PushNotificationOnboardingPromptState.skippedRegistration) {
      return false;
    }
    return true;
  }
}
