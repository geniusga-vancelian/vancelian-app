import 'dart:async';
import 'dart:developer' as developer;

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../design_system/atoms/app_colors.dart';
import '../../../../design_system/atoms/app_spacing.dart';
import '../../../../design_system/components/app_sms_otp_verification_block.dart';
import '../../../../design_system/components/app_top_nav_bar.dart';
import '../../../../design_system/components/ds_stepper_avatar.dart';
import '../../../../design_system/components/ds_validation_result_body.dart';
import '../../../../core/post_auth_flow_security_events.dart';
import '../../../../core/session/session_lifecycle_state.dart';
import '../../../../core/session/session_state_machine.dart';
import '../../../auth/presentation/screens/welcome_landing_screen.dart';
import '../../../../design_system/components/modale.dart';
import '../../../app_entry/application/post_login_local_security_flow.dart';
import '../application/auth_flow_lifecycle_guard.dart'
    show AuthFlowLifecycleObserver;
import '../../passcode/data/device_id_service.dart';
import '../../passcode/data/session_service.dart';
import '../../passkeys/data/passkey_api.dart';
import '../../passkeys/domain/passkey_exceptions.dart';
import '../widgets/login_confirmation_code_page_template.dart';

/// OTP connexion par **e-mail** (admin email OTP) — fallback hors flux SMS principal.
/// Gabarit titre / espacements alignés sur [LoginOtpScreen] ([LoginConfirmationCodePageHeader]).
class LoginEmailOtpScreen extends StatefulWidget {
  const LoginEmailOtpScreen({
    super.key,
    required this.email,
    this.phoneE164,
  });

  final String email;
  final String? phoneE164;

  @override
  State<LoginEmailOtpScreen> createState() => _LoginEmailOtpScreenState();
}

class _LoginEmailOtpScreenState extends State<LoginEmailOtpScreen> {
  final _api = PasskeyApi();
  late final AuthFlowLifecycleObserver _lifecycleObserver =
      AuthFlowLifecycleObserver(
    onStaleAfterBackground: ({required DateTime pausedAt}) {
      _onAuthFlowStaleAfterBackground(pausedAt: pausedAt);
    },
  );
  /// ``true`` jusqu’à la fin du premier ``start`` (évite un flash « Réessayer » au montage).
  bool _sending = true;
  bool _verifying = false;
  bool _wrongCode = false;
  /// Code renvoyé par l’API en dev (`dev_code`) pour affichage / préremplissage léger.
  String? _devExposedCode;
  /// ``true`` après au moins un ``start`` HTTP 2xx (évite « Code envoyé à » si l’envoi a échoué).
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

  void _onAuthFlowStaleAfterBackground({required DateTime pausedAt}) {
    if (!mounted) return;
    _timer?.cancel();
    final bgSec = DateTime.now().difference(pausedAt).inSeconds.clamp(0, 86400);
    PostAuthFlowSecurityEvents.otpFlowInvalidatedOnResume(backgroundSeconds: bgSec);
    setState(() {
      _verifying = false;
      _sending = false;
      _resendInProgress = false;
      _wrongCode = false;
      _sendSucceeded = false;
      _devExposedCode = null;
      _otpGen++;
    });
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted) return;
      await Modale.show<void>(
        context,
        ModaleParams(
          title: 'Connexion',
          content: DsValidationResultBody(
            status: DsStepperAvatarStatus.warning,
            progress: 100,
            headline: 'Session expirée, veuillez recommencer',
          ),
          primaryButton: const ModaleButtonConfig(label: 'OK'),
        ),
      );
      if (!mounted) return;
      final nav = Navigator.of(context);
      if (nav.canPop()) {
        nav.popUntil((route) => route.isFirst);
      } else {
        await nav.pushReplacement(
          MaterialPageRoute<void>(
            builder: (_) => const WelcomeLandingScreen(),
          ),
        );
      }
    });
  }

  /// Même gabarit que [LoginOtpScreen._showResendWarningModal] (avertissement orange).
  Future<void> _showSendWarningModal(String message) async {
    if (!mounted || message.isEmpty) return;
    await Modale.show<void>(
      context,
      ModaleParams(
        title: 'Connexion',
        content: DsValidationResultBody(
          status: DsStepperAvatarStatus.warning,
          progress: 100,
          headline: message,
        ),
        primaryButton: const ModaleButtonConfig(label: 'OK'),
      ),
    );
  }

  /// Même gabarit que [LoginOtpScreen._showOtpVerifyErrorModal] (erreur rouge).
  Future<void> _showVerifyErrorModal(String message) async {
    if (!mounted || message.isEmpty) return;
    await Modale.show<void>(
      context,
      ModaleParams(
        title: 'Connexion',
        content: DsValidationResultBody(
          status: DsStepperAvatarStatus.error,
          progress: 100,
          headline: message,
        ),
        primaryButton: const ModaleButtonConfig(label: 'J’ai compris'),
      ),
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
      final body = await _api.adminEmailOtpStart(email: widget.email);
      if (!mounted) return;
      final dc = body['dev_code'];
      setState(() {
        _sending = false;
        _sendSucceeded = true;
        _devExposedCode = dc is String && dc.length == 6 ? dc : null;
      });
      _startCountdown();
    } on PasskeyApiException catch (e) {
      if (!mounted) return;
      setState(() => _sending = false);
      FocusScope.of(context).unfocus();
      final msg = loginEmailOtpStartFailureUserMessage(e);
      await _showSendWarningModal(msg);
    }
  }

  Future<void> _verify(String code) async {
    if (code.length < 6 || _verifying) return;
    SessionStateMachine.instance.apply(SessionLifecycleEvent.loginFlowStarted);
    setState(() {
      _verifying = true;
      _wrongCode = false;
    });
    try {
      final deviceId = await DeviceIdService.instance.getOrCreate();
      final fp = await DeviceIdService.instance.buildFingerprintHeaderJson();
      final tokens = await _api.adminEmailOtpVerify(
        email: widget.email,
        code: code,
        deviceId: deviceId,
        fingerprintHeader: fp,
      );
      final at = tokens['access_token'] as String?;
      final rt = tokens['refresh_token'] as String?;
      if (at == null || at.isEmpty) {
        if (mounted) {
          setState(() {
            _verifying = false;
            _wrongCode = true;
          });
          _unfocusOtpAfterError();
          await _showVerifyErrorModal('Réponse serveur inattendue.');
          if (mounted) {
            setState(() {
              _wrongCode = false;
              _otpGen++;
            });
          }
        }
        return;
      }
      await SessionService.instance.storeTokens(accessToken: at, refreshToken: rt);
      await SessionService.instance.rememberLoginIdentifiers(
        email: widget.email,
        phoneE164: widget.phoneE164,
      );
      if (!mounted) return;
      developer.log('otp_success', name: 'RegistrationFlow');
      await PostLoginLocalSecurityFlow.navigateReplacingLoginStack(context);
    } on PasskeyApiException catch (e) {
      if (!mounted) return;
      final msg = loginEmailOtpVerifyFailureUserMessage(e);
      setState(() {
        _verifying = false;
        _wrongCode = true;
      });
      _unfocusOtpAfterError();
      await _showVerifyErrorModal(msg);
      if (!mounted) return;
      setState(() {
        _wrongCode = false;
        _otpGen++;
      });
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
              const LoginConfirmationCodePageHeader(title: 'Code par e-mail'),
              if (_devExposedCode != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                  child: Text(
                    'Mode test : utilisez ${_devExposedCode!}',
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      height: 20 / 14,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ),
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
                      descriptionLead: 'Code envoyé à',
                      maskedTarget: widget.email,
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
