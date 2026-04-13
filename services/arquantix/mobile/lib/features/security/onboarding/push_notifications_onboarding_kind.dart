/// Contexte d’affichage onboarding push — microcopy associée.
enum PushNotificationsOnboardingKind {
  /// Après OTP inscription, avant création du code.
  registration,

  /// Une seule fois au premier retour session si refus inscription (hors cooldown).
  reloginReprompt;

  /// Valeur `source` pour analytics.
  String get analyticsSource => switch (this) {
        PushNotificationsOnboardingKind.registration => 'registration',
        PushNotificationsOnboardingKind.reloginReprompt => 'relogin_reprompt',
      };
}

/// Textes onboarding push — centralisés par [PushNotificationsOnboardingKind].
class PushOnboardingCopy {
  PushOnboardingCopy._();

  static String title(PushNotificationsOnboardingKind kind) {
    return switch (kind) {
      PushNotificationsOnboardingKind.registration =>
        'Restez informé en temps réel',
      PushNotificationsOnboardingKind.reloginReprompt =>
        'Activez vos notifications importantes',
    };
  }

  static String body(PushNotificationsOnboardingKind kind) {
    return switch (kind) {
      PushNotificationsOnboardingKind.registration =>
        'Recevez vos alertes de sécurité, confirmations d’opérations et '
        'mises à jour importantes dès qu’elles surviennent.',
      PushNotificationsOnboardingKind.reloginReprompt =>
        'Suivez vos alertes de sécurité et les événements clés de votre compte, '
        'sans rien manquer.',
    };
  }

  static String primaryCta(PushNotificationsOnboardingKind kind) {
    return switch (kind) {
      PushNotificationsOnboardingKind.registration =>
        'Activer les notifications',
      PushNotificationsOnboardingKind.reloginReprompt => 'Activer maintenant',
    };
  }

  static const String secondaryCta = 'Passer pour l’instant';
}
