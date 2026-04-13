import 'dart:async';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/config.dart' as app_cfg;
import '../../../design_system/atoms/app_colors.dart';
import '../../../design_system/atoms/app_spacing.dart';
import '../../../design_system/components/app_primary_button.dart';
import '../../../design_system/components/app_sms_otp_verification_block.dart';
import '../../../design_system/components/modale.dart';
import '../../../design_system/components/transaction_success_overlay.dart';
import '../../security/data/two_factor_api.dart';
import '../data/registration_api.dart';
import '../data/registration_models.dart';

/// Inline SMS OTP pour l’écran registration `phone_verification_sms`.
///
/// Utilise [AppSmsOtpVerificationBlock] (même [AppOtpInput] que la connexion). Prépare le challenge au montage,
/// vérifie via `/api/2fa/verify`, finalise avec `interaction/complete`, puis
/// appelle [onCompleted].
class RegistrationPhoneSmsOtpPanel extends StatefulWidget {
  const RegistrationPhoneSmsOtpPanel({
    super.key,
    required this.screen,
    required this.sessionId,
    required this.registrationApi,
    required this.collectedData,
    required this.onGoBack,
    required this.onCompleted,
    this.twoFactorApiBuilder,
    this.skipCollectedPhoneGuard = false,
  });

  final RegistrationScreen screen;
  final String sessionId;
  final RegistrationApi registrationApi;
  final Map<String, dynamic> collectedData;

  /// Retour à l’écran précédent du flow (ex. saisie du numéro).
  final VoidCallback onGoBack;

  /// Après [completeInteraction] réussi (session déjà à jour côté serveur).
  final Future<void> Function() onCompleted;

  /// Tests : fabrique un [TwoFactorApi] à partir du jeton registration (verify mock).
  final TwoFactorApi Function(String accessToken)? twoFactorApiBuilder;

  /// Tests : ne pas bloquer si le numéro n’est pas encore dans [collectedData].
  final bool skipCollectedPhoneGuard;

  @override
  State<RegistrationPhoneSmsOtpPanel> createState() =>
      _RegistrationPhoneSmsOtpPanelState();
}

class _RegistrationPhoneSmsOtpPanelState
    extends State<RegistrationPhoneSmsOtpPanel> {
  TwoFactorApi _buildTwoFactorForToken(String token) {
    final b = widget.twoFactorApiBuilder;
    if (b != null) return b(token);
    return TwoFactorApi(
      startUrl: app_cfg.Config.twoFactorStartUrl,
      verifyUrl: app_cfg.Config.twoFactorVerifyUrl,
      accessToken: token,
    );
  }

  String get _sourceSlug =>
      widget.screen.interactionConfig?['source_field_slug'] as String? ??
          'phone_number';

  String _phoneSnapshot(Map<String, dynamic> data) =>
      (data[_sourceSlug] ?? '').toString().trim();

  bool get _hasCollectedPhone =>
      widget.skipCollectedPhoneGuard ||
      _phoneSnapshot(widget.collectedData).isNotEmpty;

  bool _preparing = true;
  bool _verifying = false;
  bool _resendInProgress = false;

  String? _fatalError;
  String? _prepareErrorCode;
  /// Code SMS refusé : bordures rouges (sans texte sous le champ).
  bool _wrongCode = false;

  String? _challengeId;
  String? _maskedTarget;
  int _resendAfterSeconds = 30;
  int _resendCountdown = 0;
  Timer? _resendTimer;

  TwoFactorApi? _twoFactorApi;
  int _otpGeneration = 0;

  String? get _payloadErrorMessage {
    final pay = widget.screen.interactionPayload;
    if (pay == null || pay['error_code'] == null) return null;
    return pay['message'] as String? ??
        'Veuillez d’abord indiquer un numéro de mobile valide à l’étape précédente.';
  }

  String? get _payloadErrorCode {
    final pay = widget.screen.interactionPayload;
    if (pay == null) return null;
    return pay['error_code'] as String?;
  }

  bool get _showRetryOnBlocking {
    final c = _prepareErrorCode ?? _payloadErrorCode;
    if (c == null) return true;
    if (c == 'phone_number_required' || c == 'phone_number_required_local') {
      return false;
    }
    return true;
  }

  @override
  void initState() {
    super.initState();
    final msg = _payloadErrorMessage;
    if (msg != null) {
      _preparing = false;
      _fatalError = msg;
      _prepareErrorCode = _payloadErrorCode;
      return;
    }
    if (!_hasCollectedPhone) {
      _preparing = false;
      _fatalError =
          'Indiquez votre numéro de mobile à l’étape précédente, puis revenez sur cet écran.';
      _prepareErrorCode = 'phone_number_required_local';
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) => _prepare());
  }

  @override
  void didUpdateWidget(RegistrationPhoneSmsOtpPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.screen.id == widget.screen.id) {
      final o = _phoneSnapshot(oldWidget.collectedData);
      final n = _phoneSnapshot(widget.collectedData);
      if (o != n && n.isNotEmpty && _fatalError != null) {
        _resendTimer?.cancel();
        setState(() {
          _fatalError = null;
          _prepareErrorCode = null;
          _preparing = true;
          _wrongCode = false;
          _challengeId = null;
          _maskedTarget = null;
          _twoFactorApi = null;
          _otpGeneration++;
        });
        WidgetsBinding.instance.addPostFrameCallback((_) => _prepare());
        return;
      }
    }
    if (oldWidget.screen.id != widget.screen.id) {
      _resendTimer?.cancel();
      _fatalError = _payloadErrorMessage;
      _prepareErrorCode = _payloadErrorCode;
      _challengeId = null;
      _maskedTarget = null;
      _wrongCode = false;
      _twoFactorApi = null;
      _otpGeneration++;
      if (_fatalError != null) {
        setState(() => _preparing = false);
        return;
      }
      if (!_hasCollectedPhone) {
        setState(() {
          _preparing = false;
          _fatalError =
              'Indiquez votre numéro de mobile à l’étape précédente, puis revenez sur cet écran.';
          _prepareErrorCode = 'phone_number_required_local';
        });
        return;
      }
      setState(() {
        _preparing = true;
        _verifying = false;
        _resendInProgress = false;
        _resendCountdown = 0;
      });
      WidgetsBinding.instance.addPostFrameCallback((_) => _prepare());
    }
  }

  @override
  void dispose() {
    _resendTimer?.cancel();
    super.dispose();
  }

  void _startResendCountdown(int seconds) {
    _resendTimer?.cancel();
    _resendAfterSeconds = seconds;
    _resendCountdown = seconds;
    _resendTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() {
        if (_resendCountdown > 0) {
          _resendCountdown -= 1;
        }
      });
    });
  }

  Future<void> _prepare() async {
    if (_payloadErrorMessage != null) return;
    if (!_hasCollectedPhone) return;
    setState(() {
      _preparing = true;
      _fatalError = null;
      _prepareErrorCode = null;
      _wrongCode = false;
    });

    final prep =
        await widget.registrationApi.prepareInteraction(widget.sessionId);
    if (!mounted) return;

    if (!prep.isSuccess || prep.data == null) {
      setState(() {
        _preparing = false;
        _prepareErrorCode = prep.errorCode;
        _fatalError = prep.errorMessage ??
            'Impossible d’envoyer le code. Vérifiez votre connexion.';
      });
      return;
    }

    final d = prep.data!;
    final token = d['otp_token'] as String? ?? '';
    final challengeId = d['challenge_id'] as String? ?? '';
    final masked = d['target_masked'] as String? ?? '';
    final resendSecs = (d['resend_after_seconds'] as num?)?.toInt() ?? 30;

    if (token.isEmpty || challengeId.isEmpty) {
      setState(() {
        _preparing = false;
        _prepareErrorCode = null;
        _fatalError = 'Réponse serveur incomplète. Réessayez dans un instant.';
      });
      return;
    }

    setState(() {
      _preparing = false;
      _challengeId = challengeId;
      _maskedTarget = masked.isNotEmpty ? masked : null;
      _twoFactorApi = _buildTwoFactorForToken(token);
    });
    _startResendCountdown(resendSecs);
  }

  Future<void> _onOtpCompleted(String code) async {
    final api = _twoFactorApi;
    final id = _challengeId;
    if (api == null || id == null || _verifying) return;

    setState(() {
      _verifying = true;
      _wrongCode = false;
    });

    final r = await api.verify(challengeId: id, code: code);
    if (!mounted) return;

    if (!r.isSuccess) {
      if (!mounted) return;
      setState(() {
        _verifying = false;
        _wrongCode = true;
      });
      await _showIncorrectOtpModal();
      return;
    }

    final comp = await widget.registrationApi.completeInteraction(
      widget.sessionId,
      screenId: widget.screen.id,
      interactionType: 'phone_verification_sms',
      challengeId: id,
      verified: true,
    );
    if (!mounted) return;

    if (!comp.isSuccess) {
      setState(() => _verifying = false);
      if (!mounted) return;
      await Modale.show<void>(
        context,
        ModaleParams(
          title: 'Unable to continue',
          description:
              comp.errorMessage ?? 'Please try again in a moment.',
          primaryButton: const ModaleButtonConfig(label: 'Got it'),
        ),
      );
      if (mounted) {
        setState(() => _otpGeneration++);
      }
      return;
    }

    setState(() => _verifying = false);
    await widget.onCompleted();
  }

  Future<void> _onResendPressed() async {
    if (_resendCountdown > 0 || _challengeId == null || _resendInProgress) {
      return;
    }
    setState(() {
      _resendInProgress = true;
      _wrongCode = false;
    });

    final r2 = await widget.registrationApi.resendInteraction(
      widget.sessionId,
      screenId: widget.screen.id,
      interactionType: 'phone_verification_sms',
    );
    if (!mounted) return;

    if (!r2.isSuccess) {
      setState(() => _resendInProgress = false);
      if (mounted) {
        final msg = r2.errorMessage ??
            (r2.isRateLimited
                ? 'Veuillez patienter avant un nouveau code.'
                : 'Échec du renvoi du SMS.');
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(msg),
            behavior: SnackBarBehavior.floating,
            margin: const EdgeInsets.all(AppSpacing.md),
          ),
        );
      }
      return;
    }

    final m = r2.data!;
    final token = m['otp_token'] as String?;
    final newId = m['challenge_id'] as String?;
    final masked = m['target_masked'] as String?;
    final secs = (m['resend_after_seconds'] as num?)?.toInt() ?? _resendAfterSeconds;

    if (token != null && token.isNotEmpty) {
      _twoFactorApi = _buildTwoFactorForToken(token);
    }
    if (newId != null && newId.isNotEmpty) {
      _challengeId = newId;
    }
    if (masked != null && masked.isNotEmpty) {
      _maskedTarget = masked;
    }

    setState(() {
      _resendInProgress = false;
      _otpGeneration++;
    });
    _startResendCountdown(secs);

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Nouveau code envoyé'),
          behavior: SnackBarBehavior.floating,
          margin: EdgeInsets.all(AppSpacing.md),
        ),
      );
    }
  }

  Future<void> _showIncorrectOtpModal() async {
    if (!mounted) return;
    await showTransactionErrorOverlay(
      context: context,
      title: 'Incorrect code entered',
      message: 'Please check the code and try again',
      buttonLabel: 'Got it',
    );
    if (!mounted) return;
    setState(() {
      _wrongCode = false;
      _otpGeneration++;
    });
  }

  Widget _buildBlockingUi() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          _fatalError!,
          style: GoogleFonts.inter(
            fontSize: 15,
            height: 22 / 15,
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        if (_showRetryOnBlocking) ...[
          AppPrimaryButton(
            label: 'Réessayer',
            shrinkWrap: true,
            onPressed: () {
              if (!_hasCollectedPhone) {
                widget.onGoBack();
                return;
              }
              setState(() {
                _fatalError = null;
                _prepareErrorCode = null;
                _preparing = true;
              });
              _prepare();
            },
          ),
          const SizedBox(height: AppSpacing.sm),
        ],
        TextButton(
          onPressed: widget.onGoBack,
          child: Text(
            'Retour',
            style: GoogleFonts.inter(
              fontSize: 15,
              fontWeight: FontWeight.w600,
              color: AppColors.indigo,
            ),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_fatalError != null) {
      return _buildBlockingUi();
    }

    if (_preparing) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: AppSpacing.xl),
        child: Center(
          child: Column(
            children: [
              CircularProgressIndicator(color: AppColors.indigo),
              SizedBox(height: AppSpacing.md),
              Text(
                'Envoi du code…',
                style: TextStyle(fontSize: 14, color: AppColors.textSecondary),
              ),
            ],
          ),
        ),
      );
    }

    final rawSubtitle = (widget.screen.subtitle ?? '').trim();
    final descriptionLead = rawSubtitle.isEmpty
        ? 'Enter the 6-digit code sent to your phone'
        : rawSubtitle;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AppSmsOtpVerificationBlock(
          descriptionLead: descriptionLead,
          maskedTarget: _maskedTarget,
          otpGeneration: _otpGeneration,
          locked: _verifying,
          wrongCode: _wrongCode,
          resendCountdown: _resendCountdown,
          resendInProgress: _resendInProgress,
          onCompleted: _onOtpCompleted,
          onResend: _onResendPressed,
          onOtpChanged: (_) {
            if (_wrongCode) setState(() => _wrongCode = false);
          },
        ),
      ],
    );
  }
}
