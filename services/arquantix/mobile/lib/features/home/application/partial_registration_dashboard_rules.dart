import '../../profile/data/mobile_app_profile.dart';
import '../../wallet/domain/models/cash_data.dart';

/// Profil [MobileAppProfile.clientStatus] == `PARTIAL` (aligné hero « inscription partielle »).
bool isPartialRegistrationClientStatus(MobileAppProfile? profile) {
  if (profile == null) return false;
  return (profile.clientStatus ?? '').trim().toUpperCase() == 'PARTIAL';
}

/// Règle métier : UX « inscription partielle » (hero dédié) uniquement tant qu’il n’existe
/// pas encore de compte cash EUR — indépendamment du parcours activation (branché au niveau Home).
bool shouldShowPartialRegistrationDashboardExperience({
  required MobileAppProfile? profile,
  required CashData? cash,
}) {
  return isPartialRegistrationClientStatus(profile) && !hasEuroCashAccount(cash);
}

/// Présence d’un compte cash EUR côté BFF [GET /api/mobile/flutter/cash] :
/// objet `cash_account` avec `currency == EUR` (solde peut être nul).
bool hasEuroCashAccount(CashData? cash) {
  final acc = cash?.cashAccount;
  if (acc == null) return false;
  return acc.currency.trim().toUpperCase() == 'EUR';
}

/// Hero / header « pré-dépôt » (parcours activation) sauf si inscription partielle
/// **et** qu’un compte EUR existe déjà — dans ce cas le dashboard standard (balance, etc.).
bool shouldUsePreDepositActivationHeader({
  required bool basePreDepositConditionsMet,
  required MobileAppProfile? profile,
  required CashData? cash,
}) {
  if (!basePreDepositConditionsMet) return false;
  if (isPartialRegistrationClientStatus(profile) && hasEuroCashAccount(cash)) {
    return false;
  }
  return true;
}

/// Mode choisi pour l’orchestration Home (debug / tests).
enum HomeDashboardOrchestrationMode {
  /// Header balance classique + sous-titre patrimoine.
  standard,

  /// Hero activation pré-dépôt (image CTA, variante vault inscription partielle si PARTIAL).
  preDepositActivation,
}

HomeDashboardOrchestrationMode resolveHomeDashboardOrchestrationMode({
  required bool usePreDepositActivationHeader,
}) {
  return usePreDepositActivationHeader
      ? HomeDashboardOrchestrationMode.preDepositActivation
      : HomeDashboardOrchestrationMode.standard;
}
