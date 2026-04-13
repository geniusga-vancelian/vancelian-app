import 'dart:async';
import 'dart:developer' as developer;

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../design_system/atoms/app_colors.dart';
import '../../../../design_system/atoms/app_spacing.dart';
import '../../../../design_system/components/app_snackbar.dart';
import '../../../../design_system/components/app_sms_otp_verification_block.dart';
import '../../../../core/auth_http_logging.dart';
import '../../../../design_system/components/app_top_nav_bar.dart';
import '../../../../design_system/components/ds_stepper_avatar.dart';
import '../../../../design_system/components/ds_validation_result_body.dart';
import '../../../../core/post_auth_flow_security_events.dart';
import '../../../../core/session/session_lifecycle_state.dart';
import '../../../../core/session/session_state_machine.dart';
import '../../../auth/presentation/screens/welcome_landing_screen.dart';
import '../../../../design_system/components/modale.dart';
import '../application/auth_flow_lifecycle_guard.dart';
import '../../passcode/data/device_id_service.dart';
import '../../passcode/data/session_service.dart';
import '../../passkeys/data/passkey_api.dart';
import '../../passkeys/domain/passkey_exceptions.dart';
import '../../../app_entry/application/post_login_local_security_flow.dart';
import 'login_email_fallback_screen.dart';
import 'login_method_sheet.dart';
import '../widgets/login_confirmation_code_page_template.dart';

/// Connexion par OTP SMS — ``POST /auth/login/sms/start`` + ``/auth/login/sms/verify``.
/// Réutilise [AppSmsOtpVerificationBlock] (même [AppOtpInput] que l’inscription).
class LoginOtpScreen extends StatefulWidget {
  const LoginOtpScreen({
    super.key,
    required this.phoneE164,
    this.passkeyApi,
    /// Réponse déjà obtenue sur l’écran téléphone — évite un second chargement plein écran.
    this.smsStartResult,
    /// Variante orchestrateur (ex. step-up) : court texte rassurant sous le titre.
    this.extraSecurityMessage,
    /// Inscription mobile : ``/auth/signup/sms/verify`` + flag registration EU après PIN.
    this.signUpMode = false,
    /// ``POST /auth/login/sms/start`` : compte pas encore ACTIVE — UX reprise inscription (pas « login complet »).
    this.resumeRegistrationHintFromSms = false,
  });

  final String phoneE164;

  /// Tests : client HTTP factice (sinon [PasskeyApi] par défaut).
  final PasskeyApi? passkeyApi;

  /// Si non null, l’écran n’appelle pas ``mobileLoginStart`` au montage (déjà fait avant la navigation).
  final Map<String, dynamic>? smsStartResult;

  final String? extraSecurityMessage;

  final bool signUpMode;

  final bool resumeRegistrationHintFromSms;

  @override
  State<LoginOtpScreen> createState() => _LoginOtpScreenState();
}

class _LoginOtpScreenState extends State<LoginOtpScreen> {
  late PasskeyApi _api;
  late final AuthFlowLifecycleObserver _lifecycleObserver =
      AuthFlowLifecycleObserver(
    onStaleAfterBackground: ({required DateTime pausedAt}) {
      _onAuthFlowStaleAfterBackground(pausedAt: pausedAt);
    },
  );
  bool _preparing = true;
  bool _verifying = false;
  bool _wrongCode = false;
  String? _fatalError;
  String _maskedDisplay = '';
  int _resendAfterSeconds = 30;
  int _resendCountdown = 0;
  Timer? _timer;
  int _otpGen = 0;
  bool _resendInProgress = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(_lifecycleObserver);
    _api = widget.passkeyApi ?? PasskeyApi();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (widget.smsStartResult != null) {
        _applySmsStartPayload(widget.smsStartResult!);
      } else {
        _startLogin();
      }
    });
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
      _preparing = false;
      _resendInProgress = false;
      _wrongCode = false;
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

  void _applySmsStartPayload(Map<String, dynamic> data) {
    if (!mounted) return;
    final masked = (data['masked_target'] as String?)?.trim() ?? '';
    final secs = (data['resend_after_seconds'] as num?)?.toInt() ?? 30;
    setState(() {
      _preparing = false;
      _fatalError = null;
      _wrongCode = false;
      _maskedDisplay = masked.isNotEmpty ? masked : widget.phoneE164;
      _resendAfterSeconds = secs;
    });
    _startCountdown(secs);
  }

  void _startCountdown(int seconds) {
    _timer?.cancel();
    setState(() => _resendCountdown = seconds);
    if (seconds <= 0) return;
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() {
        if (_resendCountdown > 0) {
          _resendCountdown--;
        }
        if (_resendCountdown <= 0) {
          _timer?.cancel();
          _timer = null;
        }
      });
    });
  }

  Future<void> _startLogin() async {
    setState(() {
      _preparing = true;
      _fatalError = null;
      _wrongCode = false;
    });
    try {
      final data = widget.signUpMode
          ? await _api.signupSmsStart(phone: widget.phoneE164)
          : await _api.mobileLoginStart(phone: widget.phoneE164);
      if (!mounted) return;
      final masked = (data['masked_target'] as String?)?.trim() ?? '';
      final secs = (data['resend_after_seconds'] as num?)?.toInt() ?? 30;
      setState(() {
        _preparing = false;
        _maskedDisplay = masked.isNotEmpty ? masked : widget.phoneE164;
        _resendAfterSeconds = secs;
      });
      _startCountdown(secs);
    } on PasskeyApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _preparing = false;
        _fatalError = widget.signUpMode
            ? signupSmsStartFailureUserMessage(e)
            : loginSmsStartFailureUserMessage(e);
      });
    } catch (e, st) {
      if (!mounted) return;
      logAuthHttpFailure(
        operation: 'login_otp_sms_start',
        error: e,
        stackTrace: st,
      );
      setState(() {
        _preparing = false;
        _fatalError = authFlowSmsStartUnknownUserMessage(
          e,
          signUpMode: widget.signUpMode,
        );
      });
    }
  }

  Future<void> _resend() async {
    if (_resendCountdown > 0 || _resendInProgress || _preparing) return;
    setState(() {
      _resendInProgress = true;
      _wrongCode = false;
    });
    try {
      final data = widget.signUpMode
          ? await _api.signupSmsStart(phone: widget.phoneE164)
          : await _api.mobileLoginStart(phone: widget.phoneE164);
      if (!mounted) return;
      final secs =
          (data['resend_after_seconds'] as num?)?.toInt() ?? _resendAfterSeconds;
      setState(() {
        _resendInProgress = false;
        _otpGen++;
      });
      _startCountdown(secs);
      if (mounted) {
        _showResendSuccessDsNotification();
      }
    } on PasskeyApiException catch (e) {
      if (!mounted) return;
      setState(() => _resendInProgress = false);
      FocusScope.of(context).unfocus();
      final msg = widget.signUpMode
          ? signupSmsStartFailureUserMessage(e)
          : loginSmsStartFailureUserMessage(e);
      await _showResendWarningModal(msg);
    }
  }

  /// [AppSnackbar] DS (pill + ombre Figma), au-dessus du clavier si besoin.
  void _showResendSuccessDsNotification() {
    if (!mounted) return;
    final mq = MediaQuery.of(context);
    final bottomInset =
        mq.viewInsets.bottom + mq.padding.bottom + AppSpacing.md;
    ScaffoldMessenger.of(context).hideCurrentSnackBar();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        elevation: 0,
        backgroundColor: Colors.transparent,
        padding: EdgeInsets.zero,
        behavior: SnackBarBehavior.floating,
        margin: EdgeInsets.fromLTRB(
          AppSpacing.pageEdge,
          0,
          AppSpacing.pageEdge,
          bottomInset,
        ),
        duration: const Duration(seconds: 3),
        content: const AppSnackbar(
          text: 'Nouveau code envoyé',
          variant: AppSnackbarVariant.dark,
        ),
      ),
    );
  }

  /// Même gabarit que l’écran téléphone (Modale + icône orange) : patienter / SMS indisponible / rate limit.
  Future<void> _showResendWarningModal(String message) async {
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

  /// Feuille DS [Modale] + [DsValidationResultBody] en `error` (croix rouge, pas l’avertissement orange).
  /// Comportement : chiffres conservés + bordure erreur jusqu’à fermeture (croix / J’ai compris), puis reset OTP.
  Future<void> _showOtpVerifyErrorModal(String message) async {
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
      final tokens = widget.signUpMode
          ? await _api.signupSmsVerify(
              phone: widget.phoneE164,
              code: code,
              deviceId: deviceId,
              fingerprintHeader: fp,
            )
          : await _api.mobileLoginVerify(
              phone: widget.phoneE164,
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
          await _showOtpVerifyErrorModal('Réponse serveur inattendue.');
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
        phoneE164: widget.phoneE164,
      );
      if (widget.signUpMode) {
        await SessionService.instance.setPendingEuRegistrationAfterPasscode(true);
      } else {
        await PostLoginLocalSecurityFlow.flagRegistrationResumeIfAccountNotActive();
      }
      if (!mounted) return;
      developer.log('otp_success', name: 'RegistrationFlow');
      await PostLoginLocalSecurityFlow.navigateReplacingLoginStack(context);
    } on PasskeyApiException catch (e) {
      if (!mounted) return;
      final msg = loginSmsVerifyFailureUserMessage(e);
      setState(() {
        _verifying = false;
        _wrongCode = true;
      });
      _unfocusOtpAfterError();
      await _showOtpVerifyErrorModal(msg);
      if (!mounted) return;
      setState(() {
        _wrongCode = false;
        _otpGen++;
      });
    }
  }

  Future<void> _openFallbackOptions() async {
    final c = await showLoginOtpFallbackSheet(context);
    if (!mounted || c == null) return;
    switch (c) {
      case LoginOtpFallbackChoice.email:
        final ok = await Navigator.of(context).push<bool>(
          MaterialPageRoute<bool>(
            builder: (_) => LoginEmailFallbackScreen(
              phoneE164: widget.phoneE164,
            ),
          ),
        );
        if (ok == true && mounted) {
          Navigator.of(context).pop(true);
        }
      case LoginOtpFallbackChoice.passkey:
        final ok = await Navigator.of(context).push<bool>(
          MaterialPageRoute<bool>(
            builder: (_) => LoginEmailFallbackScreen(
              phoneE164: widget.phoneE164,
            ),
          ),
        );
        if (ok == true && mounted) {
          Navigator.of(context).pop(true);
        }
    }
  }

  /// Fusionne paramètres explicites et [smsStartResult] (``resume_registration_hint`` du backend).
  bool get _resumeHintEffective {
    if (widget.resumeRegistrationHintFromSms) return true;
    final m = widget.smsStartResult;
    if (m == null) return false;
    return m['resume_registration_hint'] == true;
  }

  String get _titleForHeader {
    if (widget.signUpMode) return 'Inscription';
    if (_resumeHintEffective) return 'Finalisez votre inscription';
    return 'Connexion';
  }

  String? get _secondaryUxLine {
    if (widget.extraSecurityMessage != null &&
        widget.extraSecurityMessage!.trim().isNotEmpty) {
      return widget.extraSecurityMessage!.trim();
    }
    if (widget.signUpMode) return null;
    if (_resumeHintEffective) {
      return 'Votre inscription doit être finalisée avant de pouvoir vous connecter entièrement.';
    }
    return null;
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
              LoginConfirmationCodePageHeader(
                title: _titleForHeader,
              ),
              if (_secondaryUxLine != null &&
                  _secondaryUxLine!.trim().isNotEmpty) ...[
                Text(
                  _secondaryUxLine!.trim(),
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    height: 20 / 14,
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: AppSpacing.sm),
              ],
              if (_fatalError != null) ...[
                Text(
                  _fatalError!,
                  style: GoogleFonts.inter(
                    fontSize: 15,
                    height: 22 / 15,
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: AppSpacing.md),
                TextButton(
                  onPressed: _preparing ? null : _startLogin,
                  child: Text(
                    'Réessayer',
                    style: GoogleFonts.inter(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: AppColors.indigo,
                    ),
                  ),
                ),
                const SizedBox(height: AppSpacing.lg),
                TextButton(
                  onPressed: _openFallbackOptions,
                  child: Text(
                    'Autres options de connexion',
                    style: GoogleFonts.inter(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: AppColors.indigo,
                    ),
                  ),
                ),
                const Spacer(),
              ] else if (_preparing)
                const Expanded(
                  child: Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
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
              else ...[
                Expanded(
                  child: SingleChildScrollView(
                    child: AppSmsOtpVerificationBlock(
                      descriptionLead: 'Code envoyé à',
                      maskedTarget: _maskedDisplay,
                      otpGeneration: _otpGen,
                      locked: _verifying,
                      wrongCode: _wrongCode,
                      resendCountdown: _resendCountdown,
                      resendInProgress: _resendInProgress,
                      onCompleted: _verify,
                      onResend: _resend,
                      onOtpChanged: (_) {
                        if (_wrongCode) setState(() => _wrongCode = false);
                      },
                    ),
                  ),
                ),
                TextButton(
                  onPressed: _verifying ? null : _openFallbackOptions,
                  child: Text(
                    'Autres options de connexion',
                    style: GoogleFonts.inter(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: AppColors.indigo,
                    ),
                  ),
                ),
                SizedBox(height: MediaQuery.paddingOf(context).bottom),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
