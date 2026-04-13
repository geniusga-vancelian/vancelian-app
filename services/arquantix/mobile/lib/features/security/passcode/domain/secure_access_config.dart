/// Configuration produit — accès sécurisé (Phase 1 + 2).
class SecureAccessConfig {
  SecureAccessConfig._();

  /// Si un code PIN est configuré, exiger déverrouillage après le splash (cold start).
  static const bool requireUnlockWhenPasscodeSet = true;

  /// Durée d’inactivité après laquelle la session API est considérée « à rafraîchir »
  /// (indicateur local ; le serveur reste la référence).
  static const Duration sessionStaleAfter = Duration(minutes: 25);

  /// Re-verrouillage local après retour depuis le background (indépendant du JWT serveur).
  static const bool enableResumeRelock = true;

  /// Délai minimal en arrière-plan avant d’exiger à nouveau PIN / biométrie (contexte normal).
  static const Duration resumeRelockAfter = Duration(seconds: 45);

  /// Seuil plus court si session à risque (step-up requis, appareil peu fiable, etc.).
  static const Duration resumeRelockAfterHighRisk = Duration(seconds: 15);

  /// Plafond de « grâce » après auth serveur forte / action sensible récente (allonge le seuil effectif).
  static const Duration relockMaxGracePeriod = Duration(minutes: 3);

  /// Évite un second relock immédiat après un déverrouillage local réussi.
  static const Duration relockDebounceAfterLocalUnlock = Duration(seconds: 4);

  /// Fenêtre pour considérer un échec biométrique comme « récent » (forcer PIN).
  static const Duration biometricFailureRecentWindow = Duration(minutes: 2);

  /// Nombre d’échecs biométriques récents avant d’exiger le PIN en premier.
  static const int biometricFailuresBeforePinFirst = 2;
}
