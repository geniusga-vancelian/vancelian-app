import 'dart:async';

import 'package:flutter/material.dart';

import '../../../../core/privy_identity_bridge_service.dart';
import '../../../../core/post_auth_flow_security_events.dart';
import '../../../../design_system/atoms/app_colors.dart';
import '../../../../design_system/atoms/app_spacing.dart';
import '../../../../design_system/atoms/app_typography.dart';
import '../../../../design_system/atoms/kalai_icons.dart';
import '../../../../design_system/components/app_page_title.dart';
import '../../../../design_system/components/app_primary_button.dart';
import '../../../../design_system/components/app_sms_otp_verification_block.dart';
import '../../../../design_system/components/app_top_nav_bar.dart';
import '../../../../design_system/components/ds_stepper_avatar.dart';
import '../../../../design_system/components/ds_validation_result_body.dart';
import '../../../../design_system/components/kalai_icon.dart';
import '../../../../design_system/components/modale.dart';
import '../../../profile/presentation/screens/edit_account_email_screen.dart';
import '../../../security/login/application/auth_flow_lifecycle_guard.dart'
    show AuthFlowLifecycleObserver;
import '../../privy/privy_auth_provider.dart';
import '../privy_wallet_completion_flow.dart';

/// Création wallet Privy : code à 6 chiffres envoyé par **e-mail Privy** (pas l’OTP login Vancelian).
///
/// Gabarit aligné sur [LoginEmailOtpScreen] (OTP SMS / e-mail).
class PrivyWalletEmailOtpScreen extends StatefulWidget {
  const PrivyWalletEmailOtpScreen({super.key, required this.email});

  final String email;

  @override
  State<PrivyWalletEmailOtpScreen> createState() =>
      _PrivyWalletEmailOtpScreenState();
}

class _PrivyWalletEmailOtpScreenState extends State<PrivyWalletEmailOtpScreen> {
  late final PrivyAuthProvider _privy = createPrivyAuthProvider();

  late final AuthFlowLifecycleObserver _lifecycleObserver =
      AuthFlowLifecycleObserver(
    onStaleAfterBackground: ({required DateTime pausedAt}) {
      _onAuthFlowStaleAfterBackground(pausedAt: pausedAt);
    },
  );

  bool _sending = true;
  bool _verifying = false;
  bool _wrongCode = false;
  bool _sendSucceeded = false;
  int _resendCountdown = 0;
  Timer? _timer;
  int _otpGen = 0;
  bool _resendInProgress = false;

  static const _resendDefaultSeconds = 45;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(_lifecycleObserver);
    WidgetsBinding.instance.addPostFrameCallback((_) => _sendCode());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(_lifecycleObserver);
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _onAuthFlowStaleAfterBackground({
    required DateTime pausedAt,
  }) async {
    if (!mounted) return;
    _timer?.cancel();
    final bgSec = DateTime.now().difference(pausedAt).inSeconds.clamp(0, 86400);
    PostAuthFlowSecurityEvents.otpFlowInvalidatedOnResume(
      backgroundSeconds: bgSec,
    );
    setState(() {
      _verifying = false;
      _sending = false;
      _resendInProgress = false;
      _wrongCode = false;
      _sendSucceeded = false;
      _otpGen++;
    });
    await Modale.show<void>(
      context,
      ModaleParams(
        title: 'Wallet crypto',
        content: DsValidationResultBody(
          status: DsStepperAvatarStatus.warning,
          progress: 100,
          headline: 'Session expirée, veuillez recommencer',
        ),
        primaryButton: const ModaleButtonConfig(label: 'OK'),
      ),
    );
    if (!mounted) return;
    Navigator.of(context).maybePop();
  }

  Future<void> _showSendWarningModal(String message) async {
    if (!mounted || message.isEmpty) return;
    await Modale.show<void>(
      context,
      ModaleParams(
        title: 'Wallet crypto',
        content: DsValidationResultBody(
          status: DsStepperAvatarStatus.warning,
          progress: 100,
          headline: message,
        ),
        primaryButton: const ModaleButtonConfig(label: 'OK'),
      ),
    );
  }

  /// Détecte les retours Privy typiques d’un **code OTP invalide**
  /// (`invalid_credentials` / `Invalid email and code combination`).
  /// Ces messages remontent côté SDK Privy sous forme d’une chaîne contenant
  /// la pile `PrivyError(... apiError(... errorCode: "invalid_credentials" ...))`.
  bool _isWrongCodePrivyError(Object error) {
    final s = error.toString().toLowerCase();
    return s.contains('invalid_credentials') ||
        s.contains('invalid email and code combination') ||
        s.contains('invalid code') ||
        s.contains('code expired') ||
        s.contains('expired');
  }

  Future<void> _showVerifyErrorModal(Object error) async {
    if (!mounted) return;
    final emailDisplay = widget.email.trim();
    final wrongCode = _isWrongCodePrivyError(error);
    final headline = wrongCode
        ? 'Le code saisi ne correspond pas'
        : 'Validation du code impossible';
    final description = wrongCode
        ? 'Vérifiez le code à 6 chiffres reçu à $emailDisplay, '
            'puis saisissez-le à nouveau.'
        : 'Vérifiez le code à 6 chiffres reçu à $emailDisplay puis '
            'réessayez. Si le problème persiste, demandez un nouveau code.';

    await Modale.show<void>(
      context,
      ModaleParams(
        title: 'Confirmation code',
        content: DsValidationResultBody(
          status: DsStepperAvatarStatus.error,
          progress: 100,
          headline: headline,
          messageDescription: description,
          messageDescriptionStyle: AppTypography.paragraph.copyWith(
            color: AppColors.textSecondary,
            height: 1.4,
          ),
        ),
        primaryButton: const ModaleButtonConfig(label: 'Réessayer'),
        secondaryButton: ModaleButtonConfig(
          label: 'Non, modifier mon e-mail',
          variant: AppPrimaryButtonVariant.ghost,
          foregroundColor: AppColors.black,
          trailing: const KalaiIcon(
            KalaiIcons.arrowRight,
            size: 16,
            color: AppColors.black,
          ),
          onTap: _onOpenEditEmailFromVerifyError,
        ),
      ),
    );
  }

  void _onOpenEditEmailFromVerifyError() {
    if (!mounted) return;
    // Remplace l’écran OTP par l’écran d’édition d’e-mail (gated par FaceID) :
    // après modification, l’utilisateur retombe sur l’écran « Créer un wallet »
    // (l’ancien push<bool> est résolu avec `false`).
    Navigator.of(context).pushReplacement<String?, bool>(
      MaterialPageRoute<String?>(
        builder: (_) => EditAccountEmailScreen(
          initialEmail: widget.email,
        ),
      ),
      result: false,
    );
  }

  void _unfocusOtpAfterError() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      FocusManager.instance.primaryFocus?.unfocus();
    });
  }

  void _startCountdown([int seconds = _resendDefaultSeconds]) {
    _timer?.cancel();
    setState(() => _resendCountdown = seconds);
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() {
        if (_resendCountdown > 0) {
          _resendCountdown--;
        }
      });
    });
  }

  Future<void> _sendCode() async {
    setState(() {
      _sending = true;
      _wrongCode = false;
    });
    try {
      await _privy.sendPrivyEmailCode(widget.email.trim());
      if (!mounted) return;
      setState(() {
        _sending = false;
        _sendSucceeded = true;
      });
      _startCountdown();
    } on PrivyAuthProviderException catch (e) {
      if (!mounted) return;
      setState(() => _sending = false);
      FocusScope.of(context).unfocus();
      await _showSendWarningModal('$e');
    } catch (e) {
      if (!mounted) return;
      setState(() => _sending = false);
      await _showSendWarningModal('Envoi impossible : $e');
    }
  }

  Future<void> _verify(String code) async {
    if (code.length < 6 || _verifying) return;
    setState(() {
      _verifying = true;
      _wrongCode = false;
    });
    try {
      await _privy.completePrivyEmailLogin(
        email: widget.email.trim(),
        code: code.trim(),
      );
      if (!mounted) return;
      try {
        await runPrivyWalletLinkExchangeAndFinish(
          context: context,
          privy: _privy,
        );
      } on PrivyExchangeException catch (e) {
        if (!mounted) return;
        setState(() {
          _verifying = false;
          _wrongCode = true;
        });
        _unfocusOtpAfterError();
        await _showVerifyErrorModal(e);
        if (mounted) {
          setState(() {
            _wrongCode = false;
            _otpGen++;
          });
        }
        return;
      } on PrivyAuthProviderException catch (e) {
        if (!mounted) return;
        setState(() {
          _verifying = false;
          _wrongCode = true;
        });
        _unfocusOtpAfterError();
        await _showVerifyErrorModal(e);
        if (mounted) {
          setState(() {
            _wrongCode = false;
            _otpGen++;
          });
        }
        return;
      }
      if (!mounted) return;
      setState(() => _verifying = false);
    } on PrivyAuthProviderException catch (e) {
      if (!mounted) return;
      setState(() {
        _verifying = false;
        _wrongCode = true;
      });
      _unfocusOtpAfterError();
      await _showVerifyErrorModal(e);
      if (!mounted) return;
      setState(() {
        _wrongCode = false;
        _otpGen++;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _verifying = false;
        _wrongCode = true;
      });
      _unfocusOtpAfterError();
      await _showVerifyErrorModal(e);
      if (!mounted) return;
      setState(() {
        _wrongCode = false;
        _otpGen++;
      });
    }
  }

  Widget _buildOtpDescription() {
    final email = widget.email.trim();
    return RichText(
      text: TextSpan(
        style: AppTypography.paragraph.copyWith(
          color: AppColors.textSecondary,
          height: 1.4,
        ),
        children: [
          const TextSpan(
            text: 'Saisissez le code à 6 chiffres reçu à ',
          ),
          TextSpan(
            text: email,
            style: AppTypography.paragraph.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w600,
              height: 1.4,
            ),
          ),
          const TextSpan(
            text:
                ' pour valider la création de votre wallet crypto.',
          ),
        ],
      ),
    );
  }

  Future<void> _onResend() async {
    if (_resendCountdown > 0 || _resendInProgress) return;
    setState(() {
      _resendInProgress = true;
      _wrongCode = false;
    });
    await _sendCode();
    if (mounted) setState(() => _resendInProgress = false);
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.paddingOf(context).bottom;

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppTopNavBar(
        leadingType: AppTopNavBarLeading.back,
        onBackTap: () => Navigator.of(context).maybePop(),
        backgroundColor: AppColors.pageBackground,
        useDashboardStyle: true,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: AppSpacing.md),
              const AppPageTitle('Code de validation'),
              const SizedBox(height: AppSpacing.sm),
              if (_sending && !_sendSucceeded)
                Expanded(
                  child: Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: const [
                        CircularProgressIndicator(color: AppColors.indigo),
                        SizedBox(height: AppSpacing.md),
                        Text(
                          'Envoi du code…',
                          style: TextStyle(
                            fontSize: 14,
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                )
              else if (_sendSucceeded)
                Expanded(
                  child: SingleChildScrollView(
                    physics: const ClampingScrollPhysics(),
                    child: AppSmsOtpVerificationBlock(
                      description: _buildOtpDescription(),
                      otpGeneration: _otpGen,
                      locked: _verifying,
                      wrongCode: _wrongCode,
                      resendCountdown: _resendCountdown,
                      resendInProgress: _resendInProgress,
                      onCompleted: _verify,
                      onResend: _onResend,
                      onOtpChanged: (_) {
                        if (_wrongCode) setState(() => _wrongCode = false);
                      },
                    ),
                  ),
                )
              else
                Expanded(
                  child: Align(
                    alignment: Alignment.topCenter,
                    child: Padding(
                      padding: const EdgeInsets.only(top: AppSpacing.lg),
                      child: FilledButton(
                        onPressed: _sending ? null : _sendCode,
                        child: const Text('Réessayer l’envoi'),
                      ),
                    ),
                  ),
                ),
              SizedBox(height: bottomInset),
            ],
          ),
        ),
      ),
    );
  }
}
