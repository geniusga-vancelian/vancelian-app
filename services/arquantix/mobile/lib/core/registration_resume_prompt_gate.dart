import 'session_identity_context.dart';

/// Limite la modal « Reprendre votre inscription ? » à une fois par cycle d’identité
/// (jusqu’à logout / changement de compte). Réinitialisé quand [SessionIdentityContext.epoch] change.
class RegistrationResumePromptGate {
  RegistrationResumePromptGate._();

  static int? _suppressedForEpoch;

  /// `false` après fermeture de la modal (tout bouton ou backdrop).
  static bool shouldOfferPrompt() {
    final e = SessionIdentityContext.instance.epoch;
    return _suppressedForEpoch != e;
  }

  static void suppressForCurrentIdentity() {
    _suppressedForEpoch = SessionIdentityContext.instance.epoch;
  }
}
