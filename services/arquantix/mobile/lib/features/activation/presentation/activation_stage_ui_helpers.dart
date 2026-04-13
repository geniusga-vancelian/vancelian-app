import '../../profile/data/mobile_app_profile.dart';
import '../domain/activation_journey_models.dart';

/// Complétion d’étape : aligné sur l’API + filet si l’inscription affiche 100 % mais
/// le statut serveur reste « en cours » (désalignement profil / activation).
bool isActivationStageCompleted(
  ActivationJourneyStage stage,
  MobileAppProfile? profile,
) {
  if (stage.uxStatus == ActivationStageUxStatus.completed) {
    return true;
  }
  if (stage.key == 'account_verification' && profile != null) {
    final dp = profile.registrationDerivedProgressPercent;
    if (dp != null && dp >= 100) {
      return true;
    }
  }
  return false;
}

/// Prochaine action : première étape non terminée (route cible), sinon CTA principal API.
String? effectiveActivationPrimaryRoute(
  ActivationJourney journey,
  MobileAppProfile? profile,
) {
  for (final s in journey.stages) {
    if (!isActivationStageCompleted(s, profile)) {
      final t = s.targetRoute.trim();
      if (t.isNotEmpty) {
        return t;
      }
    }
  }
  final p = journey.primaryCtaTargetRoute?.trim();
  return p != null && p.isNotEmpty ? p : null;
}
