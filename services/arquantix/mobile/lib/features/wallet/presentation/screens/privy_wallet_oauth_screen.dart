import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'package:privy_flutter/privy_flutter.dart';

import '../../../../core/privy_identity_bridge_service.dart';
import '../../../../core/secure_api_config.dart';
import '../../../../core/session_identity_context.dart';
import '../../../../design_system/design_system.dart';
import '../../../deposit/presentation/screens/deposit_crypto_screen.dart';
import '../../privy/privy_auth_provider.dart';
import '../privy_wallet_completion_flow.dart';
import '../../privy/privy_dart_defines.dart';

/// Parcours **réduit** : OAuth Privy → liaison `person` (`POST /auth/privy/link` sous JWT)
/// → embedded wallet → échange JWT (session + device headers comme le login SMS).
///
/// Visible sur le dashboard quand Privy et l’API auth sont configurés.
class PrivyWalletOAuthScreen extends StatefulWidget {
  const PrivyWalletOAuthScreen({super.key});

  @override
  State<PrivyWalletOAuthScreen> createState() => _PrivyWalletOAuthScreenState();
}

class _PrivyWalletOAuthScreenState extends State<PrivyWalletOAuthScreen> {
  late final PrivyAuthProvider _privy = createPrivyAuthProvider();
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _redirectIfAlreadyHasWallet());
  }

  Future<void> _redirectIfAlreadyHasWallet() async {
    if (!SecureApiConfig.hasAuthBackend || !mounted) return;
    try {
      final list =
          await PrivyIdentityBridgeService.instance.fetchAuthenticatedPersonCryptoWallets();
      if (!mounted || list.isEmpty) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute<void>(builder: (_) => const DepositCryptoScreen()),
      );
    } catch (_) {
      // Laisser l’écran s’afficher si l’API est indisponible.
    }
  }

  Future<void> _run(Future<void> Function() body) async {
    if (_busy || !mounted) return;
    setState(() => _busy = true);
    try {
      await body();
    } on PrivyExchangeException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('[${e.code}] ${e.message}')),
        );
      }
    } on PrivyAuthProviderException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _fullFlow(OAuthProvider provider) async {
    final personId =
        SessionIdentityContext.instance.personId?.trim() ?? '';

    await _run(() async {
      if (!SecureApiConfig.hasAuthBackend) {
        throw PrivyExchangeException(
          0,
          'privy.exchange.no_auth_backend',
          'AUTH_API_BASE_URL / resolvedAuthApiBaseUrl vide.',
        );
      }
      if (personId.isEmpty) {
        throw PrivyAuthProviderException(
          'person_id absent du JWT — se connecter à Vancelian d’abord (session avec person_id).',
        );
      }

      final persistedPre =
          await PrivyIdentityBridgeService.instance.fetchAuthenticatedPersonCryptoWallets();
      if (!mounted) return;
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
        return;
      }

      await _privy.loginWithOAuth(provider);

      if (!mounted) return;
      await runPrivyWalletLinkExchangeAndFinish(context: context, privy: _privy);
    });
  }

  @override
  Widget build(BuildContext context) {
    final configured =
        PrivyDartDefines.isConfigured && PrivyDartDefines.isOAuthRedirectConfigured;
    final personId =
        SessionIdentityContext.instance.personId?.trim();

    final showApple = Platform.isIOS;

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppBar(
        title: const Text('Wallet Privy (OAuth)'),
        backgroundColor: AppColors.pageBackground,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          children: [
            Text(
              'Un clic lance : OAuth → liaison compte (JWT) → création du wallet ETH embarqué → échange session Vancelian.',
              style: AppTypography.bodyRegular,
            ),
            const SizedBox(height: AppSpacing.md),
            if (!configured)
              Text(
                'Configurer PRIVY_APP_ID et PRIVY_APP_CLIENT_ID, et déclarer le scheme « ${PrivyDartDefines.oauthRedirectScheme} » en natif (voir doc Privy identity).',
                style: AppTypography.bodySmRegular.copyWith(
                  color: AppColors.semanticWarning,
                ),
              )
            else
              Text(
                'OAuth scheme : ${PrivyDartDefines.oauthRedirectScheme}\nBackend auth : ${PrivyIdentityBridgeService.privyExchangeUrl.split('/auth').first}',
                style: AppTypography.bodySmRegular.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            const SizedBox(height: AppSpacing.md),
            if (personId == null || personId.isEmpty)
              Text(
                'Aucune person_id dans la session JWT — ouvrir une session Vancelian (SMS / PIN) puis revenir.',
                style: AppTypography.bodySmRegular.copyWith(
                  color: AppColors.semanticDanger,
                ),
              )
            else
              Text(
                'Person cible : $personId',
                style: AppTypography.bodySmRegular.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            const SizedBox(height: AppSpacing.xl),
            AppPrimaryButton(
              label:
                  _busy ? 'En cours…' : 'Créer mon wallet Privy (avec Google)',
              onPressed:
                  !_busy && configured ? () => _fullFlow(OAuthProvider.google) : null,
            ),
            if (showApple) ...[
              const SizedBox(height: AppSpacing.md),
              AppPrimaryButton(
                label: _busy
                    ? 'En cours…'
                    : 'Créer mon wallet Privy (avec Apple)',
                onPressed:
                    !_busy && configured ? () => _fullFlow(OAuthProvider.apple) : null,
              ),
            ],
            const SizedBox(height: AppSpacing.xl),
            Text(
              'Le fournisseur (Google ou Apple) doit être activé pour votre app Privy dashboard.',
              style: AppTypography.bodySmRegular.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
