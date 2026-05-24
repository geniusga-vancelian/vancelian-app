import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../core/post_auth_flow_security_events.dart';
import '../../../../design_system/atoms/app_colors.dart';
import '../../../../design_system/atoms/app_spacing.dart';
import '../../../../design_system/components/app_page_title.dart';
import '../../../../design_system/components/app_primary_button.dart';
import '../../../../design_system/components/app_text_input.dart';
import '../../../../design_system/components/app_top_nav_bar.dart';
import '../../../wallet/privy/privy_dart_defines.dart';
import '../../passcode/data/device_id_service.dart';
import '../../passcode/data/session_service.dart';
import '../../passkeys/application/passkey_service.dart';
import '../../passkeys/data/passkey_api.dart';
import '../../passkeys/data/passkey_platform_provider_factory.dart';
import '../../../app_entry/application/post_login_local_security_flow.dart';
import '../application/auth_flow_lifecycle_guard.dart';
import '../../passkeys/presentation/passkey_login_coordinator.dart';
import 'login_email_otp_screen.dart';
import 'login_phone_screen.dart';

String _maskPhoneBanner(String e164) {
  final t = e164.trim();
  if (t.length < 6) return t;
  final tail = t.substring(t.length - 2);
  final head = t.substring(0, 4);
  return '$head •• •• •• $tail';
}

/// Connexion / récupération par e-mail (OTP Privy) ou passkey seule ([passkeyOnly]).
class LoginEmailFallbackScreen extends StatefulWidget {
  const LoginEmailFallbackScreen({
    super.key,
    this.phoneE164,
    this.recoveryMode = false,
    this.passkeyOnly = false,
    this.signUpMode = false,
  });

  final String? phoneE164;
  final bool recoveryMode;

  /// `true` depuis la feuille « Continuer avec une passkey » (sans bouton OTP e-mail).
  final bool passkeyOnly;

  /// Inscription (création de compte) plutôt que connexion.
  final bool signUpMode;

  @override
  State<LoginEmailFallbackScreen> createState() =>
      _LoginEmailFallbackScreenState();
}

class _LoginEmailFallbackScreenState extends State<LoginEmailFallbackScreen> {
  final _emailCtrl = TextEditingController();
  late final AuthFlowLifecycleObserver _lifecycleObserver =
      AuthFlowLifecycleObserver(
    onStaleAfterBackground: ({required DateTime pausedAt}) {
      _onAuthFlowStaleAfterBackground(pausedAt: pausedAt);
    },
  );
  bool _busy = false;
  String? _inline;

  late final PasskeyApi _passkeyApi = PasskeyApi();
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

  String get _email => _emailCtrl.text.trim();

  bool get _emailOk {
    final e = _email;
    return e.contains('@') &&
        e.split('@').length == 2 &&
        e.split('@').last.isNotEmpty;
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(_lifecycleObserver);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(_lifecycleObserver);
    _emailCtrl.dispose();
    super.dispose();
  }

  void _onAuthFlowStaleAfterBackground({required DateTime pausedAt}) {
    if (!mounted) return;
    final bgSec = DateTime.now().difference(pausedAt).inSeconds.clamp(0, 86400);
    PostAuthFlowSecurityEvents.passkeyFlowInvalidatedOnResume(
      backgroundSeconds: bgSec,
    );
    setState(() => _busy = false);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'Authentification interrompue, utilisez une autre méthode',
        ),
      ),
    );
  }

  Future<void> _passkeyLogin() async {
    setState(() {
      _busy = true;
      _inline = null;
    });
    if (!_emailOk) {
      setState(() {
        _busy = false;
        _inline = 'Saisissez une adresse e-mail valide.';
      });
      return;
    }
    await _coordinator.signInWithPasskey(
      email: _email,
      onFallback: () {
        if (mounted) {
          setState(() => _busy = false);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Passkey indisponible. Réessayez ou utilisez l’e-mail.'),
            ),
          );
        }
      },
      onSuccess: () async {
        if (!mounted) return;
        setState(() => _busy = false);
        await SessionService.instance.rememberLoginIdentifiers(
          email: _email,
          phoneE164: widget.phoneE164,
        );
        if (mounted) {
          await PostLoginLocalSecurityFlow.navigateReplacingLoginStack(context);
        }
      },
    );
    if (mounted && _busy) {
      setState(() => _busy = false);
    }
  }

  Future<void> _openEmailOtp() async {
    setState(() => _inline = null);
    if (!_emailOk) {
      setState(() => _inline = 'Saisissez une adresse e-mail valide.');
      return;
    }
    if (!PrivyDartDefines.isConfigured) {
      setState(() {
        _inline =
            'Connexion par e-mail indisponible (Privy non configuré dans cette build).';
      });
      return;
    }
    await SessionService.instance.rememberLoginIdentifiers(email: _email);
    if (!mounted) return;
    final ok = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => LoginEmailOtpScreen(
          email: _email,
          phoneE164: widget.phoneE164,
          signUpMode: widget.signUpMode,
        ),
      ),
    );
    if (ok == true && mounted) {
      Navigator.of(context).pop(true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final last = _emailCtrl.text.trim();
    final returning = last.isNotEmpty && _emailOk;
    final passkeyOnly = widget.passkeyOnly;

    final signUp = widget.signUpMode;
    final title = widget.recoveryMode
        ? 'Récupération du compte'
        : passkeyOnly
            ? 'Continuer avec une passkey'
            : signUp
                ? 'Créer votre compte'
                : (returning ? 'Heureux de vous revoir' : 'Continuer avec l’e-mail');

    final subtitle = widget.recoveryMode
        ? 'Indiquez l’e-mail associé à votre compte. Nous vous enverrons un code de vérification à six chiffres.'
        : passkeyOnly
            ? 'Indiquez l’e-mail de votre compte, puis validez avec votre passkey.'
            : signUp
                ? 'Indiquez votre e-mail. Un code à six chiffres vous sera envoyé pour créer votre compte.'
                : (returning
                    ? 'Recevez un code à six chiffres par e-mail pour vous connecter.'
                    : 'Indiquez l’e-mail de votre compte. Un code à six chiffres vous sera envoyé pour vous connecter.');

    final bottomSafe = MediaQuery.paddingOf(context).bottom;

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      resizeToAvoidBottomInset: true,
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
                style: GoogleFonts.inter(
                  fontSize: 15,
                  fontWeight: FontWeight.w400,
                  height: 22 / 15,
                  color: AppColors.textSecondary,
                ),
              ),
              if (widget.phoneE164 != null &&
                  widget.phoneE164!.trim().isNotEmpty) ...[
                const SizedBox(height: AppSpacing.md),
                Container(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                      color: AppColors.indigo.withValues(alpha: 0.2),
                    ),
                  ),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.smartphone_outlined,
                        color: AppColors.indigo,
                      ),
                      const SizedBox(width: AppSpacing.sm),
                      Expanded(
                        child: Text(
                          'Mobile saisi : ${_maskPhoneBanner(widget.phoneE164!)}',
                          style: GoogleFonts.inter(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                            color: AppColors.textPrimary,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: AppSpacing.pageDescriptionToFirstField),
              Expanded(
                child: SingleChildScrollView(
                  keyboardDismissBehavior:
                      ScrollViewKeyboardDismissBehavior.onDrag,
                  child: AppTextInput(
                    label: 'E-mail',
                    variant: AppTextInputVariant.placeholder,
                    controller: _emailCtrl,
                    showEmailIcon: false,
                    keyboardType: TextInputType.emailAddress,
                    textInputAction: TextInputAction.done,
                    onChanged: (_) => setState(() {}),
                    error: _inline,
                  ),
                ),
              ),
              if (passkeyOnly)
                AppPrimaryButton(
                  label: 'Utiliser une passkey',
                  size: AppPrimaryButtonSize.large,
                  isLoading: _busy,
                  onPressed: _busy || !_emailOk ? null : _passkeyLogin,
                )
              else
                AppPrimaryButton(
                  label: 'Recevoir un code par e-mail',
                  size: AppPrimaryButtonSize.large,
                  isLoading: _busy,
                  onPressed: _busy || !_emailOk ? null : _openEmailOtp,
                ),
              if (!signUp && !passkeyOnly && !widget.recoveryMode) ...[
                const SizedBox(height: AppSpacing.md),
                AppPrimaryButton(
                  label: 'Utiliser mon numéro de mobile',
                  variant: AppPrimaryButtonVariant.secondary,
                  size: AppPrimaryButtonSize.large,
                  onPressed: _busy
                      ? null
                      : () {
                          Navigator.of(context).push<void>(
                            MaterialPageRoute<void>(
                              builder: (_) => const LoginPhoneScreen(),
                            ),
                          );
                        },
                ),
              ],
              SizedBox(height: bottomSafe > 0 ? bottomSafe : AppSpacing.md),
            ],
          ),
        ),
      ),
    );
  }
}
