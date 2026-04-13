import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../design_system/atoms/app_colors.dart';
import '../../../../design_system/atoms/app_spacing.dart';
import '../../../../design_system/components/app_top_nav_bar.dart';
import '../../../app_entry/application/post_login_local_security_flow.dart';
import '../../passcode/data/device_id_service.dart';
import '../../passcode/data/session_service.dart';
import '../../passkeys/application/passkey_service.dart';
import '../../passkeys/data/passkey_api.dart';
import '../../passkeys/data/passkey_platform_provider_factory.dart';
import '../../passkeys/presentation/passkey_login_coordinator.dart';
import 'login_otp_screen.dart';

/// Fast lane : passkey automatique après ``/auth/login/sms/start`` si le backend le recommande.
/// Repli immédiat vers [LoginOtpScreen] en cas d’échec, d’annulation ou d’action utilisateur.
class LoginAutoAuthScreen extends StatefulWidget {
  const LoginAutoAuthScreen({
    super.key,
    required this.phoneE164,
    required this.smsStartResult,
    required this.passkeyEmail,
    this.headline,
    this.subtitle,
  });

  final String phoneE164;
  final Map<String, dynamic> smsStartResult;
  final String passkeyEmail;
  /// Variantes UX (ex. fast lane orchestrateur).
  final String? headline;
  final String? subtitle;

  @override
  State<LoginAutoAuthScreen> createState() => _LoginAutoAuthScreenState();
}

class _LoginAutoAuthScreenState extends State<LoginAutoAuthScreen> {
  final _passkeyApi = PasskeyApi();
  late final PasskeyLoginCoordinator _coordinator = PasskeyLoginCoordinator(
    passkeyService: PasskeyService(
      api: _passkeyApi,
      provider: createPasskeyProvider(),
      getDeviceId: () => DeviceIdService.instance.getOrCreate(),
      getFingerprintHeader: () =>
          DeviceIdService.instance.buildFingerprintHeaderJson(),
    ),
    api: _passkeyApi,
  );

  bool _started = false;
  bool _navigatingToOtp = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _runAutoPasskey());
  }

  Future<void> _runAutoPasskey() async {
    if (_started || !mounted) return;
    _started = true;
    final email = widget.passkeyEmail.trim();
    if (email.isEmpty) {
      _openOtp();
      return;
    }
    await _coordinator.signInWithPasskey(
      email: email,
      autoAnalytics: (event, {detail}) => _passkeyApi.reportPrompt(
        event: event,
        email: email,
        detail: detail,
      ),
      onFallback: () {
        if (mounted) _openOtp();
      },
      onSuccess: () async {
        if (!mounted) return;
        await SessionService.instance.rememberLoginIdentifiers(
          email: email,
          phoneE164: widget.phoneE164,
        );
        await PostLoginLocalSecurityFlow.flagRegistrationResumeIfAccountNotActive();
        if (mounted) {
          await PostLoginLocalSecurityFlow.navigateReplacingLoginStack(context);
        }
      },
    );
  }

  void _openOtp() {
    if (_navigatingToOtp || !mounted) return;
    _navigatingToOtp = true;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<bool>(
        builder: (_) => LoginOtpScreen(
          phoneE164: widget.phoneE164,
          smsStartResult: widget.smsStartResult,
          resumeRegistrationHintFromSms:
              (widget.smsStartResult['resume_registration_hint'] as bool?) ??
                  false,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppTopNavBar(
        leadingType: AppTopNavBarLeading.back,
        onBackTap: () {
          _passkeyApi.reportPrompt(
            event: 'auth.login.passkey_auto_trigger_cancelled',
            email: widget.passkeyEmail,
            detail: 'back_tap',
          );
          _openOtp();
        },
        backgroundColor: AppColors.pageBackground,
        useDashboardStyle: true,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: AppSpacing.xl),
              Text(
                widget.headline ?? 'Connexion sécurisée disponible sur cet appareil',
                textAlign: TextAlign.center,
                style: GoogleFonts.inter(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  height: 28 / 22,
                  letterSpacing: -0.26,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              Text(
                widget.subtitle ?? 'Utilisation de votre passkey…',
                textAlign: TextAlign.center,
                style: GoogleFonts.inter(
                  fontSize: 15,
                  fontWeight: FontWeight.w400,
                  height: 22 / 15,
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: AppSpacing.xl * 2),
              const Center(
                child: CircularProgressIndicator(color: AppColors.indigo),
              ),
              const Spacer(),
              TextButton(
                onPressed: () {
                  _passkeyApi.reportPrompt(
                    event: 'auth.login.passkey_auto_trigger_fallback_otp',
                    email: widget.passkeyEmail,
                    detail: 'user_chose_sms',
                  );
                  _openOtp();
                },
                child: Text(
                  'Vous pouvez aussi recevoir un code par SMS',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: AppColors.indigo,
                  ),
                ),
              ),
              SizedBox(height: MediaQuery.paddingOf(context).bottom + 16),
            ],
          ),
        ),
      ),
    );
  }
}
