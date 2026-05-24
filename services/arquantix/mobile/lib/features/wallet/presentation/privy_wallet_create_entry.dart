import 'package:flutter/material.dart';

import '../../../core/profile_identity_coordinator.dart';
import '../../profile/presentation/screens/account_info_screen.dart';
import '../../profile/presentation/screens/edit_account_email_screen.dart';
import 'screens/privy_wallet_email_otp_screen.dart';
import 'widgets/privy_wallet_email_confirm_sheet.dart';

/// Parcours produit : profil avec e-mail → feuille de confirmation → OTP e-mail Privy → [runPrivyWalletLinkExchangeAndFinish] dans l’écran OTP.
///
/// Retourne `true` si l’écran OTP se ferme avec succès (`pop(true)` après exchange).
Future<bool> openPrivyWalletEmailCreationFlow(BuildContext context) async {
  final profile =
      await ProfileIdentityCoordinator.instance.loadAccountProfile();
  if (!context.mounted) {
    return false;
  }
  final email = profile?.displayEmailOrNull?.trim();
  if (email == null || email.isEmpty) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Text(
          'Renseignez une adresse e-mail dans Mon compte pour créer votre wallet crypto.',
        ),
        action: SnackBarAction(
          label: 'Mon compte',
          onPressed: () {
            Navigator.of(context).push<void>(
              MaterialPageRoute<void>(
                builder: (_) => const AccountInfoScreen(),
              ),
            );
          },
        ),
      ),
    );
    return false;
  }

  final confirmed = await showPrivyWalletEmailConfirmSheet(
    context: context,
    email: email,
  );
  if (!context.mounted) {
    return false;
  }
  if (confirmed == false) {
    final emailUpdated = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => EditAccountEmailScreen(initialEmail: email),
      ),
    );
    if (!context.mounted) {
      return false;
    }
    if (emailUpdated == true) {
      await ProfileIdentityCoordinator.instance.loadAccountProfile(
        forceRefresh: true,
        debugTag: 'openPrivyWalletEmailCreationFlow.afterEmailEdit',
      );
      if (!context.mounted) {
        return false;
      }
      return openPrivyWalletEmailCreationFlow(context);
    }
    return false;
  }
  if (confirmed != true) {
    return false;
  }

  final created = await Navigator.of(context).push<bool>(
        MaterialPageRoute<bool>(
          builder: (_) => PrivyWalletEmailOtpScreen(email: email),
        ),
      ) ??
      false;
  return created;
}
