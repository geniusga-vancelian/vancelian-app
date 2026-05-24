import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../../../core/profile_identity_coordinator.dart';
import '../../../../design_system/atoms/app_colors.dart';
import '../../../../design_system/atoms/app_spacing.dart';
import '../../../../design_system/atoms/app_typography.dart';
import '../../../../design_system/components/app_page_title.dart';
import '../../../../design_system/components/app_sms_otp_verification_block.dart';
import '../../../../design_system/components/app_top_nav_bar.dart';
import '../../../../design_system/components/modale.dart';
import '../../../../design_system/components/ds_stepper_avatar.dart';
import '../../../../design_system/components/ds_validation_result_body.dart';
import '../../../wallet/privy/privy_auth_provider.dart';
import '../../../wallet/privy/privy_dart_defines.dart';
import '../../data/mobile_contact_email_api.dart';

/// Validation OTP Privy pour confirmer une nouvelle adresse e-mail (persistance API).
class EditAccountEmailOtpScreen extends StatefulWidget {
  const EditAccountEmailOtpScreen({
    super.key,
    required this.email,
    this.skipInitialSend = true,
  });

  final String email;

  /// `true` si [PrivyAuthProvider.sendPrivyEmailCode] a déjà été appelé avant navigation.
  final bool skipInitialSend;

  @override
  State<EditAccountEmailOtpScreen> createState() =>
      _EditAccountEmailOtpScreenState();
}

class _EditAccountEmailOtpScreenState extends State<EditAccountEmailOtpScreen> {
  static const MobileContactEmailApi _contactEmailApi = MobileContactEmailApi();

  late final PrivyAuthProvider _privy = createPrivyAuthProvider();

  bool _sending = false;
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
    if (widget.skipInitialSend) {
      _sendSucceeded = true;
      _startCountdown();
    } else {
      WidgetsBinding.instance.addPostFrameCallback((_) => _sendCode());
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _showErrorModal(String headline, {String? description}) async {
    if (!mounted) return;
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
        primaryButton: const ModaleButtonConfig(label: 'OK'),
      ),
    );
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
    if (!PrivyDartDefines.isConfigured) {
      await _showErrorModal(
        'Privy non configuré',
        description:
            'Impossible d’envoyer le code. Vérifiez PRIVY_APP_ID dans la build.',
      );
      return;
    }
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
      await _showErrorModal('Envoi impossible', description: e.message);
    } catch (e) {
      if (!mounted) return;
      setState(() => _sending = false);
      await _showErrorModal('Envoi impossible', description: '$e');
    }
  }

  Future<void> _verify(String code) async {
    if (code.length < 6 || _verifying) return;
    setState(() {
      _verifying = true;
      _wrongCode = false;
    });
    try {
      await _privy.completePrivyEmailVerification(
        email: widget.email.trim(),
        code: code.trim(),
      );
      final token = await _privy.getAccessToken();
      if (token == null || token.trim().isEmpty) {
        throw PrivyAuthProviderException(
          'Jeton Privy indisponible après validation du code.',
        );
      }
      final result = await _contactEmailApi.confirmChange(
        email: widget.email.trim(),
        privyAccessToken: token,
      );
      if (!mounted) return;
      if (result.status != 'confirmed') {
        throw MobileContactEmailApiException(
          'Le serveur n’a pas confirmé l’e-mail (statut ${result.status}).',
        );
      }
      await ProfileIdentityCoordinator.instance.loadAccountProfile(
        forceRefresh: true,
        debugTag: 'EditAccountEmailOtpScreen',
      );
      if (!mounted) return;
      setState(() => _verifying = false);
      Navigator.of(context).pop(true);
    } on MobileContactEmailApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _verifying = false;
        _wrongCode = true;
      });
      await _showErrorModal(
        'Enregistrement impossible',
        description: e.message,
      );
      if (mounted) {
        setState(() {
          _wrongCode = false;
          _otpGen++;
        });
      }
    } on PrivyAuthProviderException catch (e) {
      if (!mounted) return;
      if (kDebugMode) {
        debugPrint('[EditAccountEmailOtp] Privy verify failed: $e');
      }
      setState(() {
        _verifying = false;
        _wrongCode = true;
      });
      final wrongCode = isPrivyWrongCodeError(e);
      await _showErrorModal(
        wrongCode
            ? 'Le code saisi ne correspond pas'
            : 'Validation du code impossible',
        description: wrongCode
            ? 'Vérifiez le code à 6 chiffres reçu à ${widget.email.trim()}, '
                'puis saisissez-le à nouveau.'
            : 'Le code ne peut être utilisé qu’une fois. Demandez un nouveau code '
                '(« Renvoyer le code »), saisissez-le aussitôt, puis réessayez.',
      );
      if (mounted) {
        setState(() {
          _wrongCode = false;
          _otpGen++;
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _verifying = false;
        _wrongCode = true;
      });
      await _showErrorModal('Validation impossible', description: '$e');
      if (mounted) {
        setState(() {
          _wrongCode = false;
          _otpGen++;
        });
      }
    }
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
                ' pour confirmer votre nouvelle adresse e-mail.',
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
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
                const Expanded(
                  child: Center(
                    child: CircularProgressIndicator(color: AppColors.indigo),
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
            ],
          ),
        ),
      ),
    );
  }
}
