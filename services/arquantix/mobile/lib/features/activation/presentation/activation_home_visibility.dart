import '../domain/activation_journey_models.dart';
import '../../profile/data/mobile_app_profile.dart';

/// True si l’étape ``first_deposit`` est **completed** (API / profil).
bool isFirstDepositStageComplete(ActivationJourney aj) {
  for (final s in aj.stages) {
    if (s.key == 'first_deposit') {
      return s.uxStatus == ActivationStageUxStatus.completed;
    }
  }
  return false;
}

/// Carte activation / inscription : affichée tant que le **premier dépôt** n’est pas fait
/// (dès que le dépôt est validé, la carte disparaît — l’investissement est poussé ailleurs).
bool shouldShowActivationModuleCard(MobileAppProfile? profile) {
  if (profile == null) return false;
  if (!profile.shouldShowActivationJourney) return false;
  final aj = profile.activationJourney;
  if (aj == null) return true;
  return !isFirstDepositStageComplete(aj);
}

/// Carte « My accounts » : visible seulement après le premier dépôt, ou si pas de parcours activation.
///
/// [hasEuroCashAccount] : si vrai, afficher la carte dès qu’un compte cash EUR existe
/// (ex. inscription `PARTIAL` mais compte EUR déjà provisionné — priorité au dashboard standard).
bool shouldShowMyAccountsCard(
  MobileAppProfile? profile, {
  bool hasEuroCashAccount = false,
}) {
  if (hasEuroCashAccount) return true;
  if (profile == null) return true;
  final aj = profile.activationJourney;
  if (aj != null) {
    return isFirstDepositStageComplete(aj);
  }
  return !profile.shouldShowActivationJourney;
}
