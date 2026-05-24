import 'package:flutter/material.dart';

import '../../../core/privy_identity_bridge_service.dart';
import '../../../core/secure_api_config.dart';
import '../../../core/session_identity_context.dart';
import '../../../design_system/atoms/app_colors.dart';
import '../../deposit/presentation/screens/deposit_crypto_screen.dart';
import '../privy/privy_auth_provider.dart';

/// Issue quand la suite link + wallet + exchange se termine sans `pop(true)` (wallet déjà connu).
enum PrivyWalletCompletionOutcome {
  /// Succès : snackbar verte + [Navigator.pop] `true`.
  successPopped,

  /// Des wallets existaient déjà : navigation remplacée vers [DepositCryptoScreen].
  alreadyHadWalletNavigatedToDeposit,
}

/// Suite commune après authentification Privy (OAuth ou e-mail OTP) : lien `person`,
/// création wallet embarqué si besoin, échange session Vancelian.
///
/// Réutilisé par [PrivyWalletOAuthScreen] et [PrivyWalletEmailOtpScreen].
Future<PrivyWalletCompletionOutcome> runPrivyWalletLinkExchangeAndFinish({
  required BuildContext context,
  required PrivyAuthProvider privy,
}) async {
  if (!SecureApiConfig.hasAuthBackend) {
    throw PrivyExchangeException(
      0,
      'privy.exchange.no_auth_backend',
      'AUTH_API_BASE_URL / resolvedAuthApiBaseUrl vide.',
    );
  }
  final personId = SessionIdentityContext.instance.personId?.trim() ?? '';
  if (personId.isEmpty) {
    throw PrivyAuthProviderException(
      'person_id absent du JWT — se connecter à Vancelian d’abord (session avec person_id).',
    );
  }

  final persistedPre =
      await PrivyIdentityBridgeService.instance.fetchAuthenticatedPersonCryptoWallets();
  if (!context.mounted) {
    return PrivyWalletCompletionOutcome.successPopped;
  }
  if (persistedPre.isNotEmpty) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          persistedPre.first.address.length > 10
              ? 'Un wallet existe déjà (${persistedPre.first.address.substring(0, 10)}…).'
              : 'Un wallet existe déjà pour ce compte.',
        ),
        backgroundColor: AppColors.semanticWarning,
      ),
    );
    await Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(builder: (_) => const DepositCryptoScreen()),
    );
    return PrivyWalletCompletionOutcome.alreadyHadWalletNavigatedToDeposit;
  }

  final pUid = await privy.getLinkedPrivyUserId();
  if (pUid == null || pUid.trim().isEmpty) {
    throw PrivyAuthProviderException(
      'Identité Privy absente après authentification.',
    );
  }

  await PrivyIdentityBridgeService.instance.linkPrivyForAuthenticatedSession(
    privyUserId: pUid,
  );

  await privy.createEmbeddedWalletIfNeeded();

  final token = await privy.getAccessToken();
  if (token == null || token.trim().isEmpty) {
    throw PrivyAuthProviderException('Jeton Privy absent après connexion.');
  }
  final w = await privy.getPrimaryWallet();
  await PrivyIdentityBridgeService.instance.exchangePrivyToken(
    privyAccessToken: token,
    wallets: w != null ? <Map<String, dynamic>>[w.toExchangeJson()] : null,
  );

  if (!context.mounted) {
    return PrivyWalletCompletionOutcome.successPopped;
  }
  final addr = w?.address;
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text(
        addr != null && addr.isNotEmpty
            ? (addr.length > 8 ? '${addr.substring(0, 8)}…' : addr)
            : 'Wallet et session synchronisés.',
      ),
      backgroundColor: AppColors.semanticPositive,
    ),
  );
  Navigator.of(context).pop(true);
  return PrivyWalletCompletionOutcome.successPopped;
}
