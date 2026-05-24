import 'dart:async';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../core/auth_http_logging.dart';
import '../../../../core/interaction_warmup.dart';
import '../../../../core/jank_trace.dart';
import '../../../../core/phone_e164.dart';
import '../../../../design_system/atoms/app_colors.dart';
import '../../../../design_system/atoms/app_spacing.dart';
import '../../../../design_system/components/app_page_title.dart';
import '../../../../design_system/components/app_phone_input.dart';
import '../../../../design_system/components/app_primary_button.dart';
import '../../../../design_system/components/app_top_nav_bar.dart';
import '../../../../design_system/components/ds_stepper_avatar.dart';
import '../../../../design_system/components/ds_validation_result_body.dart';
import '../../../../design_system/components/modale.dart';
import '../../../registration/registration_phone_format_validation.dart';
import '../../../app_entry/application/post_login_local_security_flow.dart';
import '../../passcode/data/session_service.dart';
import '../../../auth/orchestrator/login_orchestrator.dart';
import '../../passkeys/data/passkey_api.dart';
import '../../passkeys/domain/passkey_exceptions.dart';
import 'login_email_fallback_screen.dart';
import 'login_method_sheet.dart';
import 'login_otp_screen.dart';

/// Étape 1 connexion : mobile + pays, puis OTP SMS ([LoginOtpScreen]) ; e-mail / passkey en secours.
/// [signUpMode] : inscription (``/auth/signup/sms/*``) au lieu de la connexion.
class LoginPhoneScreen extends StatefulWidget {
  const LoginPhoneScreen({
    super.key,
    this.hydrateLastSession = true,
    this.signUpMode = false,
  });

  /// Désactiver en tests widget (évite SecureStorage + indicateur indéterminé).
  final bool hydrateLastSession;

  /// ``true`` : flux création de compte (SMS signup + OTP + PIN + registration EU).
  final bool signUpMode;

  @override
  State<LoginPhoneScreen> createState() => _LoginPhoneScreenState();
}

class _LoginPhoneScreenState extends State<LoginPhoneScreen> {
  final _phoneCtrl = TextEditingController();
  final _phoneFocusNode = FocusNode();
  String _countryIso = 'FR';
  String _nationalDigits = '';
  bool _busy = false;
  String? _lastEmail;

  /// Styles résolus dans [initState] — évite [GoogleFonts.inter] au premier [build].
  late final TextStyle _subtitleStyle;
  late final TextStyle _linkStyle;

  @override
  void initState() {
    super.initState();
    _subtitleStyle = GoogleFonts.inter(
      fontSize: 15,
      fontWeight: FontWeight.w400,
      height: 22 / 15,
      color: AppColors.textSecondary,
    );
    _linkStyle = GoogleFonts.inter(
      fontSize: 15,
      fontWeight: FontWeight.w600,
      color: AppColors.indigo,
    );
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      JankTrace.markRouteFirstFrame('LoginPhoneScreen');
      // Warmup secours : frame suivante pour ne pas concurrencer le premier frame / slide.
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        unawaited(scheduleInteractionWarmup(context));
      });
    });
    if (widget.hydrateLastSession) {
      // Ne pas bloquer le premier frame : le secure storage peut coûter >1 s au
      // premier accès ; l’écran s’affiche tout de suite, le titre s’ajuste ensuite.
      unawaited(_loadPrefs());
    }
  }

  Future<void> _loadPrefs() async {
    final email = await SessionService.instance.readLastLoginEmail();
    if (!mounted) return;
    setState(() => _lastEmail = email);
  }

  @override
  void dispose() {
    _phoneFocusNode.dispose();
    _phoneCtrl.dispose();
    super.dispose();
  }

  String get _e164 =>
      normalizePhoneFieldToE164(_nationalDigits, phoneDialCodeForIso(_countryIso));

  /// Même règles que l’inscription mobile ([isRegistrationPhoneFormatValid]) :
  /// masque national + pays ; le `0` initial est géré à l’envoi via [normalizePhoneFieldToE164].
  bool get _phoneFormatOk =>
      isRegistrationPhoneFormatValid(_nationalDigits, _countryIso);

  void _unfocusPhoneField() {
    FocusScope.of(context).unfocus();
  }

  /// Succès auth serveur : enchaîne PIN / Secure Gate **sans** repasser par Login0
  /// (évite un flash de [WelcomeLandingScreen] et une double transition).
  Future<void> _finishServerLoginSuccess() async {
    if (!mounted) return;
    await PostLoginLocalSecurityFlow.navigateReplacingLoginStack(context);
  }

  /// Numéro inconnu / web-only / gel : le backend n’envoie pas de SMS — proposer inscription ou autre méthode.
  Future<void> _showSmsLoginUnavailableModal() async {
    if (!mounted) return;
    await Modale.show<void>(
      context,
      ModaleParams(
        title: 'Connectez-vous',
        content: DsValidationResultBody(
          status: DsStepperAvatarStatus.warning,
          progress: 100,
          headline:
              'Ce numéro ne permet pas la connexion par SMS. Créez un compte ou utilisez une autre option de connexion.',
        ),
        primaryButton: ModaleButtonConfig(
          label: 'Créer un compte',
          onTap: () {
            if (!mounted) return;
            Navigator.of(context).pushReplacement(
              MaterialPageRoute<void>(
                builder: (_) => const LoginPhoneScreen(signUpMode: true),
              ),
            );
          },
        ),
        secondaryButton: const ModaleButtonConfig(label: 'OK'),
      ),
    );
  }

  Future<void> _showContinueErrorModal(
    String message, {
    VoidCallback? onRetry,
  }) async {
    if (!mounted || message.isEmpty) return;
    await Modale.show<void>(
      context,
      ModaleParams(
        title: 'Connectez-vous',
        content: DsValidationResultBody(
          status: DsStepperAvatarStatus.error,
          progress: 100,
          headline: message,
        ),
        primaryButton: const ModaleButtonConfig(label: 'OK'),
        secondaryButton: onRetry == null
            ? null
            : ModaleButtonConfig(
                label: 'Réessayer',
                onTap: () {
                  WidgetsBinding.instance.addPostFrameCallback((_) {
                    onRetry();
                  });
                },
              ),
      ),
    );
  }

  Future<void> _onContinue() async {
    _unfocusPhoneField();
    if (!_phoneFormatOk) return;

    setState(() => _busy = true);
    try {
      await SessionService.instance.rememberLoginIdentifiers(phoneE164: _e164);
      if (!mounted) return;
      final api = PasskeyApi();

      if (widget.signUpMode) {
        final data = await api.signupSmsStart(phone: _e164);
        if (!mounted) return;
        await Navigator.of(context).push<void>(
          MaterialPageRoute<void>(
            builder: (_) => LoginOtpScreen(
              phoneE164: _e164,
              smsStartResult: data,
              signUpMode: true,
            ),
          ),
        );
        if (mounted) setState(() => _busy = false);
        return;
      }

      final data = await api.mobileLoginStart(phone: _e164);
      if (!mounted) return;
      final rawDispatched = data['sms_otp_dispatched'];
      final smsDispatched = rawDispatched is bool ? rawDispatched : true;
      if (!smsDispatched) {
        setState(() => _busy = false);
        await _showSmsLoginUnavailableModal();
        return;
      }
      final apiEmail = (data['passkey_login_email'] as String?)?.trim();
      final cachedEmail = _lastEmail?.trim();
      final passkeyEmail = (apiEmail != null && apiEmail.isNotEmpty)
          ? apiEmail
          : cachedEmail;
      final flow = LoginOrchestratorResult.fromSmsStartResponse(
        data,
        phoneE164: _e164,
        passkeyEmail: passkeyEmail,
      );
      final emailForPasskey = passkeyEmail ?? '';

      final ok = await flow.pushFlow(
        context,
        phoneE164: _e164,
        smsStartResult: data,
        passkeyEmail: emailForPasskey,
      );
      if (!mounted) return;
      if (ok == true) {
        await _finishServerLoginSuccess();
      } else {
        setState(() => _busy = false);
      }
    } on PasskeyApiException catch (e) {
      if (!mounted) return;
      setState(() => _busy = false);
      await _showContinueErrorModal(
        widget.signUpMode
            ? signupSmsStartFailureUserMessage(e)
            : loginSmsStartFailureUserMessage(e),
      );
    } catch (e, st) {
      if (!mounted) return;
      setState(() => _busy = false);
      logAuthHttpFailure(
        operation: 'login_phone_continue',
        error: e,
        stackTrace: st,
      );
      await _showContinueErrorModal(
        authFlowSmsStartUnknownUserMessage(e, signUpMode: widget.signUpMode),
        onRetry: _onContinue,
      );
    }
  }

  Future<void> _openMethodSheet() async {
    _unfocusPhoneField();
    final choice = await showLoginMethodSheet(context);
    if (!mounted || choice == null) return;
    switch (choice) {
      case LoginMethodSheetChoice.email:
        final ok = await Navigator.of(context).push<bool>(
          MaterialPageRoute<bool>(
            builder: (_) => const LoginEmailFallbackScreen(),
          ),
        );
        if (ok == true && mounted) await _finishServerLoginSuccess();
      case LoginMethodSheetChoice.passkey:
        final ok = await Navigator.of(context).push<bool>(
          MaterialPageRoute<bool>(
            builder: (_) => const LoginEmailFallbackScreen(passkeyOnly: true),
          ),
        );
        if (ok == true && mounted) await _finishServerLoginSuccess();
      case LoginMethodSheetChoice.lostPhone:
        final ok = await Navigator.of(context).push<bool>(
          MaterialPageRoute<bool>(
            builder: (_) => const LoginEmailFallbackScreen(recoveryMode: true),
          ),
        );
        if (ok == true && mounted) await _finishServerLoginSuccess();
    }
  }

  @override
  Widget build(BuildContext context) {
    final returning = _lastEmail != null && _lastEmail!.isNotEmpty;
    final title = widget.signUpMode
        ? 'Créer un compte'
        : (returning ? 'Heureux de vous revoir' : 'Connectez-vous');
    final subtitle = widget.signUpMode
        ? 'Entrez votre numéro de mobile. Nous vous enverrons un code par SMS pour vérifier votre numéro.'
        : (returning
            ? 'Même démarche qu’avant : votre mobile, puis le code reçu par SMS.'
            : 'Entrez votre numéro de mobile. Nous vous enverrons un code par SMS pour vous connecter.');

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
              AppPageTitle(title),
              const SizedBox(height: AppSpacing.sm),
              Text(
                subtitle,
                style: _subtitleStyle,
              ),
              const SizedBox(height: AppSpacing.pageDescriptionToFirstField),
              Expanded(
                child: SingleChildScrollView(
                  child: AppPhoneInput(
                    label: 'Numéro de mobile',
                    countryCode: _countryIso,
                    phoneController: _phoneCtrl,
                    phoneFocusNode: _phoneFocusNode,
                    onCountryChanged: (iso) =>
                        setState(() => _countryIso = iso),
                    onPhoneChanged: (v) =>
                        setState(() => _nationalDigits = v),
                    textInputAction: TextInputAction.done,
                  ),
                ),
              ),
              AppPrimaryButton(
                label: 'Continuer',
                size: AppPrimaryButtonSize.large,
                isLoading: _busy,
                onPressed: _busy || !_phoneFormatOk ? null : _onContinue,
              ),
              if (!widget.signUpMode) ...[
                const SizedBox(height: AppSpacing.md),
                TextButton(
                  onPressed: _busy ? null : _openMethodSheet,
                  child: Text(
                    'Autres options de connexion',
                    style: _linkStyle,
                  ),
                ),
              ],
              SizedBox(height: MediaQuery.paddingOf(context).bottom),
            ],
          ),
        ),
      ),
    );
  }
}
