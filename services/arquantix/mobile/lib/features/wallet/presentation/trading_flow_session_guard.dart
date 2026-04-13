import 'package:flutter/material.dart';

import '../../security/passcode/data/session_service.dart';

/// Vérifie qu’une session API existe **et** que le JWT indique un compte **ACTIVE**
/// (pas PARTIAL / ``sec_inc``) avant d’ouvrir les flux achat / vente / swap.
///
/// Les endpoints d’échange (`/api/mobile/flutter/exchange/*`) résolvent le client via le
/// JWT ([mobile_app_client]). Sans Bearer ou compte incomplet, l’utilisateur ne doit pas entrer dans ces écrans.
final class TradingFlowSessionGuard {
  TradingFlowSessionGuard._();

  static Future<bool> ensureSessionOrPrompt(BuildContext context) async {
    final has = await SessionService.instance.hasSessionCredentials();
    if (!has) {
      if (!context.mounted) return false;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Connectez-vous pour acheter, vendre ou échanger des actifs.',
          ),
        ),
      );
      return false;
    }
    if (!await SessionService.instance.isLastStoredAccessAccountActive()) {
      if (!context.mounted) return false;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Finalisez votre inscription pour continuer.',
          ),
        ),
      );
      return false;
    }
    return true;
  }
}

/// Même contrôle que [TradingFlowSessionGuard] — nom explicite pour investissements
/// (bundles, offres exclusives, tout flux « customer money » hors order book).
final class CustomerAccountSessionGuard {
  CustomerAccountSessionGuard._();

  static Future<bool> ensureActiveAccountOrPrompt(BuildContext context) =>
      TradingFlowSessionGuard.ensureSessionOrPrompt(context);
}
