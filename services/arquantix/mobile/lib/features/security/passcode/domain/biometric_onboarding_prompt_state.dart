/// Réponse locale à l’écran onboarding biométrie (SecureStorage, par binding JWT).
///
/// **Produit (priorité sécurité / re-invite skip) :**
/// - [enabled] : biométrie activée → ne plus afficher l’onboarding bloquant.
/// - [skipped] : l’utilisateur a refusé sur un appareil compatible → **ré-inviter** à chaque déverrouillage tant que la politique backend le permet.
/// - [unavailable] : pas de biométrie utilisable sur l’appareil → ne pas boucler sur un écran bloquant inutile.
/// - [neverSeen] : pas encore de décision persistée → suivre le backend pour l’affichage.
enum BiometricOnboardingPromptState {
  neverSeen,
  enabled,
  skipped,
  unavailable;

  /// Valeur persistée (clé dédiée `biometricOnboardingPromptState`).
  String get storageValue {
    switch (this) {
      case BiometricOnboardingPromptState.neverSeen:
        return 'never_seen';
      case BiometricOnboardingPromptState.enabled:
        return 'enabled';
      case BiometricOnboardingPromptState.skipped:
        return 'skipped';
      case BiometricOnboardingPromptState.unavailable:
        return 'unavailable';
    }
  }

  static BiometricOnboardingPromptState? tryParse(String? raw) {
    if (raw == null || raw.isEmpty) return null;
    for (final v in BiometricOnboardingPromptState.values) {
      if (v.storageValue == raw) return v;
    }
    return null;
  }
}

/// Réconciliation quand la capacité biométrique **change** (ex. Face ID activé dans Réglages iOS
/// après un parcours [unavailable]) : repartir sur [neverSeen] pour permettre le gate onboarding.
///
/// Ne modifie pas [skipped] / [enabled] / [neverSeen] — uniquement la transition
/// `unavailable` + capteur désormais OK → [neverSeen].
BiometricOnboardingPromptState reconcileBiometricOnboardingPromptStateForDevice({
  required BiometricOnboardingPromptState stored,
  required bool deviceSupportsBiometric,
}) {
  if (stored == BiometricOnboardingPromptState.unavailable &&
      deviceSupportsBiometric) {
    return BiometricOnboardingPromptState.neverSeen;
  }
  return stored;
}
