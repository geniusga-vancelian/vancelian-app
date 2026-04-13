/// État produit local — onboarding notifications push (SecureStorage, par binding JWT).
///
/// **Produit :**
/// - [neverSeen] : pas encore d’écran onboarding registration → afficher après OTP.
/// - [enabled] : opt-in (ou équivalent profil) → plus de prompt automatique.
/// - [skippedRegistration] : refus pendant l’inscription → **une** re-demande au premier retour
///   après fin de session (hors flux registration).
/// - [skippedFirstRelogin] : refus au re-prompt → plus de prompt automatique (réglages profil).
enum PushNotificationOnboardingPromptState {
  neverSeen,
  enabled,
  skippedRegistration,
  skippedFirstRelogin;

  String get storageValue {
    switch (this) {
      case PushNotificationOnboardingPromptState.neverSeen:
        return 'never_seen';
      case PushNotificationOnboardingPromptState.enabled:
        return 'enabled';
      case PushNotificationOnboardingPromptState.skippedRegistration:
        return 'skipped_registration';
      case PushNotificationOnboardingPromptState.skippedFirstRelogin:
        return 'skipped_first_relogin';
    }
  }

  static PushNotificationOnboardingPromptState? tryParse(String? raw) {
    if (raw == null || raw.isEmpty) return null;
    for (final v in PushNotificationOnboardingPromptState.values) {
      if (v.storageValue == raw) return v;
    }
    return null;
  }
}
