import 'dart:developer' as developer;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'package:arquantix_news/design_system/atoms/app_colors.dart';
import 'package:arquantix_news/design_system/atoms/app_spacing.dart';
import 'package:arquantix_news/design_system/atoms/app_typography.dart';
import '../../../../home/application/home_dashboard_preload.dart';
import '../../../../shell/presentation/screens/main_shell_screen.dart';
import 'package:arquantix_news/features/app_entry/application/post_login_local_security_flow.dart';
import 'package:arquantix_news/features/profile/application/security_preferences_coordinator.dart';
import 'package:arquantix_news/features/profile/data/mobile_profile_api.dart';
import 'package:arquantix_news/features/security/onboarding/biometric_login_onboarding_screen.dart';
import 'package:arquantix_news/core/session/session_lifecycle_state.dart';
import 'package:arquantix_news/core/session/session_state_machine.dart';
import 'package:arquantix_news/core/session_identity_context.dart';
import '../../../local_access/biometric_policy_service.dart';
import '../../data/biometric_auth_service.dart';
import '../../data/session_api.dart';
import '../../data/passcode_service.dart';
import '../../data/passcode_client_greeting_storage.dart';
import '../../data/session_service.dart';
import '../../domain/jwt_access_claims.dart';
import '../../domain/secure_access_config.dart';
import '../widgets/pin_keypad.dart';

/// Déverrouillage local : biométrie si disponible, PIN obligatoire en repli.
class PasscodeUnlockScreen extends StatefulWidget {
  const PasscodeUnlockScreen({super.key, this.popOnSuccess = false});

  /// `true` après relock « resume » : fermer l’écran au lieu de pousser le dashboard.
  final bool popOnSuccess;

  @override
  State<PasscodeUnlockScreen> createState() => _PasscodeUnlockScreenState();
}

class _PasscodeUnlockScreenState extends State<PasscodeUnlockScreen>
    with WidgetsBindingObserver {
  String _buffer = '';
  String? _message;
  bool _bioInFlight = false;
  String? _clientFirstName;
  bool _bioEnabledPref = false;
  bool _deviceBioOk = false;
  bool _forcePinFirst = false;
  BiometricKeypadIconKind? _bioKeypadKind;
  bool _dashboardLoading = false;
  /// Évite deux enchaînements concurrents vers le shell (ex. biométrie auto + tap quasi simultanés).
  bool _enterAppInProgress = false;
  /// Une seule tentative biométrie automatique par session d’écran (pas de boucle si échec).
  bool _biometricAutoLaunchedThisSession = false;

  static const Duration _autoBiometricPostLayoutDelay = Duration(milliseconds: 160);

  /// Logs auto-biométrie : [developer.log] + [debugPrint] (recherche Xcode/adb : `PasscodeUnlock.autoBio`).
  /// Préfixes CASE_* pour corrélation :
  /// A=showCtas false, B=forcePin, C=déjà lancé, D=sortie précoce _tryBiometric, E=authenticate,
  /// F/G=timing mounted, H=chaîne schedule absente.
  void _logAutoBio(String msg, [Map<String, Object?>? data]) {
    final line = data == null ? msg : '$msg $data';
    developer.log(line, name: 'PasscodeUnlock.autoBio');
    debugPrint('[PasscodeUnlock.autoBio] $line');
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _loadClientFirstName();
    WidgetsBinding.instance.addPostFrameCallback((_) => _prepareUnlockFlow());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    super.didChangeAppLifecycleState(state);
    if (state == AppLifecycleState.resumed) {
      _syncBiometricPromptStateWithCurrentDevice();
    }
  }

  /// Retour Settings / activation Face ID : [unavailable] → [never_seen] si le capteur est OK.
  Future<void> _syncBiometricPromptStateWithCurrentDevice() async {
    await PasscodeService.instance.init();
    final deviceOk =
        await BiometricAuthService.instance.deviceSupportsBiometrics();
    await PasscodeService.instance
        .syncBiometricOnboardingPromptStateWithDeviceCapability(deviceOk);
  }

  Future<void> _loadClientFirstName() async {
    final token = await SessionService.instance.readAccessToken();
    var n = await PasscodeClientGreetingStorage.instance.readForAccessToken(token);
    n ??= await SessionService.instance.readGreetingFirstName();
    if (n == null && token != null && token.isNotEmpty) {
      n = jwtExtractGreetingFirstName(token);
    }
    if (n != null && jwtIsLikelyOpaqueUserIdentifier(n)) {
      n = null;
    }
    var fromProfileApi = false;
    if (n == null && token != null && token.isNotEmpty) {
      final profileN = await _firstNameFromMobileProfile(token);
      if (profileN != null) {
        n = profileN;
        fromProfileApi = true;
      }
    }
    if (n != null && jwtIsLikelyOpaqueUserIdentifier(n)) {
      n = null;
      fromProfileApi = false;
    }
    if (fromProfileApi && n != null && n.trim().isNotEmpty) {
      await SessionService.instance.persistGreetingFirstNameFromProfile(n.trim());
    }
    if (mounted) {
      setState(() => _clientFirstName = n);
    }
  }

  /// `GET /api/mobile/flutter/profile` → `personal.first_name` (profil personne, pas l’ID client JWT).
  Future<String?> _firstNameFromMobileProfile(String accessToken) async {
    try {
      const api = MobileProfileApi();
      final p = await api.fetchProfile(accessToken: accessToken);
      final fn = p?.personal?.firstName?.trim();
      if (fn != null &&
          fn.isNotEmpty &&
          !jwtIsLikelyOpaqueUserIdentifier(fn)) {
        return fn;
      }
    } catch (_) {}
    return null;
  }

  /// Titre unique (HeadingSecondary) : prénom dynamique + consigne.
  String get _unlockPageTitle {
    final n = _clientFirstName?.trim();
    if (n == null || n.isEmpty) {
      return 'Bonjour, saisissez votre code d’accès.';
    }
    return 'Bonjour $n, saisissez votre code d’accès.';
  }

  /// Hauteur réservée pour **une** ligne de message (évite tout saut des bullets).
  static double get _messageSlotHeight {
    final s = AppTypography.itemSupporting;
    final fs = s.fontSize ?? 13;
    final lh = s.height ?? 1;
    return fs * lh;
  }

  /// Icône / CTA biométrie : **uniquement** préf. locale + capteur + politique PIN (jamais
  /// `securityPreferences` / onboarding serveur). Sans biométrie activée localement, pas d’auto-trigger.
  bool get _showBiometricCtas =>
      _bioEnabledPref && _deviceBioOk && SecureAccessConfig.requireUnlockWhenPasscodeSet;

  Future<void> _prepareUnlockFlow() async {
    _logAutoBio('prepareUnlockFlow enter');
    await PasscodeService.instance.init();
    final deviceOk =
        await BiometricAuthService.instance.deviceSupportsBiometrics();
    await PasscodeService.instance
        .syncBiometricOnboardingPromptStateWithDeviceCapability(deviceOk);
    final bioPref = await PasscodeService.instance.isBiometricUnlockEnabled();
    final fails = await SessionService.instance.readBiometricRecentFailCount();
    final lastFail = await SessionService.instance.readLastBiometricFailAt();
    final forcePin = await BiometricPolicyService.instance.shouldForcePinInsteadOfBiometric(
      biometricRecentFailCount: fails,
      lastBiometricFailAt: lastFail,
    );
    BiometricKeypadIconKind? keypadKind;
    if (bioPref && deviceOk) {
      keypadKind = await BiometricAuthService.instance.keypadIconKind() ??
          BiometricKeypadIconKind.fingerprint;
    }
    if (!mounted) return;
    setState(() {
      _bioEnabledPref = bioPref;
      _deviceBioOk = deviceOk;
      _forcePinFirst = forcePin;
      _bioKeypadKind = keypadKind;
    });
    _logAutoBio('after setState', {
      'bioPref': bioPref,
      'deviceOk': deviceOk,
      'forcePinFirst': forcePin,
      'showCtas': _showBiometricCtas,
      'requireUnlock': SecureAccessConfig.requireUnlockWhenPasscodeSet,
    });
    // Après le premier frame avec l’état à jour + léger délai : LocalAuthentication sur iOS
    // ignore souvent un prompt lancé trop tôt après navigation / avant layout stable.
    _scheduleAutoBiometricAfterLayoutStable();
  }

  void _scheduleAutoBiometricAfterLayoutStable() {
    _logAutoBio('CASE_H scheduleAutoBiometric chain start');
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        _logAutoBio('CASE_F postFrame skipped !mounted');
        return;
      }
      _logAutoBio('CASE_F postFrame ok, delay ${_autoBiometricPostLayoutDelay.inMilliseconds}ms');
      _runDelayedAutoBiometric();
    });
  }

  Future<void> _runDelayedAutoBiometric() async {
    await Future<void>.delayed(_autoBiometricPostLayoutDelay);
    if (!mounted) {
      _logAutoBio('CASE_G after delay !mounted — maybeAutoTrigger jamais appelé');
      return;
    }
    _logAutoBio('CASE_G after delay mounted — call maybeAutoTrigger');
    await _maybeAutoTriggerBiometricOnce();
  }

  /// Une fois par session, seulement si la biométrie est **activée** localement (icône affichée).
  /// Les états onboarding skipped / unavailable n’activent pas la biométrie → pas d’auto-trigger.
  Future<void> _maybeAutoTriggerBiometricOnce() async {
    if (!_showBiometricCtas) {
      _logAutoBio('CASE_A skip showBiometricCtas=false', {
        'bioPref': _bioEnabledPref,
        'deviceOk': _deviceBioOk,
        'requireUnlock': SecureAccessConfig.requireUnlockWhenPasscodeSet,
      });
      return;
    }
    if (_forcePinFirst) {
      _logAutoBio('CASE_B skip forcePinFirst=true');
      return;
    }
    if (_biometricAutoLaunchedThisSession) {
      _logAutoBio('CASE_C skip alreadyLaunchedThisSession');
      return;
    }
    _biometricAutoLaunchedThisSession = true;
    _logAutoBio('CASE_D invoking _tryBiometric(autoTrigger:true) — si rien après, regarder CASE_E');
    await _tryBiometric(autoTrigger: true);
  }

  Future<void> _tryBiometric({required bool autoTrigger}) async {
    if (_enterAppInProgress || _dashboardLoading) {
      if (autoTrigger) {
        _logAutoBio('CASE_D abort _tryBiometric: enterApp/dashboard in progress');
      }
      return;
    }
    if (_bioInFlight) {
      if (autoTrigger) {
        _logAutoBio('CASE_D abort _tryBiometric: bioInFlight=true');
      }
      return;
    }
    if (!_showBiometricCtas) {
      if (autoTrigger) {
        _logAutoBio('CASE_D abort _tryBiometric: showBiometricCtas=false');
      }
      return;
    }
    if (autoTrigger && _forcePinFirst) {
      _logAutoBio('CASE_D abort _tryBiometric: forcePinFirst');
      return;
    }
    if (autoTrigger) {
      _logAutoBio('CASE_E _tryBiometric reached — before setState/authenticate', {
        'showCtas': _showBiometricCtas,
        'forcePinFirst': _forcePinFirst,
      });
    }
    setState(() => _message = null);
    _bioInFlight = true;
    _logAutoBio('CASE_E calling LocalAuthentication.authenticate (auto=$autoTrigger)');
    final ok = await BiometricAuthService.instance.authenticate(
      reason: 'Déverrouiller votre espace',
    );
    _bioInFlight = false;
    if (autoTrigger) {
      if (ok) {
        _logAutoBio('CASE_E authenticate returned true — succès biométrie');
      } else {
        _logAutoBio(
          'CASE_E authenticate returned false — refus utilisateur, échec OS, ou prompt non présenté',
        );
      }
    }
    if (!mounted) return;
    if (ok) {
      await _enterApp();
      return;
    }
    await SessionService.instance.recordBiometricAuthFailure();
    if (!mounted) return;
    setState(() {
      _message = 'Impossible de valider la biométrie.';
    });
  }

  Future<void> _enterApp() async {
    if (_enterAppInProgress) {
      _logAutoBio('_enterApp skip: already in progress');
      return;
    }
    _enterAppInProgress = true;
    try {
      await _enterAppBody();
    } finally {
      _enterAppInProgress = false;
    }
  }

  Future<void> _enterAppBody() async {
    await SessionService.instance.recordLocalUnlockSuccess();
    // Ne pas appeler [SessionService.isSessionValid] ici : un refresh JWT en échec (401)
    // effaçait toute la session avant [MainShellScreen], et la Home partait sans Bearer.
    // Le rafraîchissement reste possible au cold start ([AppEntryBootstrap]) ou via les APIs.
    final tok = await SessionService.instance.readAccessToken();
    if (tok != null && tok.isNotEmpty) {
      await SessionApi().ackLocalPasscodeRegistered(accessToken: tok);
      final next = await SessionService.instance.readAccessToken();
      SessionIdentityContext.instance.syncFromAccessToken(
        (next != null && next.isNotEmpty) ? next : tok,
      );
    }
    SessionStateMachine.instance.apply(SessionLifecycleEvent.passcodeUnlocked);
    if (!mounted) return;
    if (widget.popOnSuccess) {
      Navigator.of(context).pop();
      return;
    }

    final postAckTok = await SessionService.instance.readAccessToken();
    if (postAckTok != null && postAckTok.isNotEmpty) {
      try {
        await PasscodeService.instance.init();
        final localPrompt =
            await PasscodeService.instance.getBiometricOnboardingPromptState();
        const api = MobileProfileApi();
        final profile = await api.fetchProfile(accessToken: postAckTok);
        if (SecurityPreferencesCoordinator.shouldShowBlockingBiometricOnboarding(
              profile?.securityPreferences,
              localPromptState: localPrompt,
            ) &&
            mounted) {
          await Navigator.of(context).push<void>(
            MaterialPageRoute<void>(
              fullscreenDialog: true,
              builder: (_) => const BiometricLoginOnboardingScreen(),
            ),
          );
        }
      } catch (_) {}
    }

    setState(() => _dashboardLoading = true);
    try {
      await Future.wait<void>([
        HomeDashboardPreload.runAfterPasscodeUnlock().timeout(
          const Duration(seconds: 18),
          onTimeout: () {
            if (kDebugMode) {
              debugPrint('[PasscodeUnlock] preload timeout');
            }
          },
        ),
        Future<void>.delayed(const Duration(milliseconds: 900)),
      ]);
    } catch (e) {
      if (kDebugMode) {
        debugPrint('[PasscodeUnlock] preload error: $e');
      }
    }
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(
        builder: (_) => const MainShellScreen(),
      ),
    );
  }

  Future<void> _onDigit(String d) async {
    setState(() {
      _message = null;
      if (_buffer.length < PasscodeService.pinLength) {
        _buffer += d;
      }
    });
    if (_buffer.length < PasscodeService.pinLength) return;

    final r = await PasscodeService.instance.verifyPin(_buffer);
    if (!mounted) return;
    setState(() => _buffer = '');

    switch (r) {
      case PasscodeVerifySuccess():
        await _enterApp();
      case PasscodeVerifyWrongPin():
        setState(() => _message = 'Code incorrect');
      case PasscodeVerifyLocked(:final until):
        setState(
          () => _message =
              'Trop de tentatives. Réessayez après ${until.toLocal()}',
        );
      case PasscodeVerifyHardReset():
        setState(() {
          _message =
              'Accès réinitialisé pour sécurité. Reconnectez-vous depuis le début.';
        });
        SessionStateMachine.instance.apply(SessionLifecycleEvent.hardResetSecurity);
        // clearSession volontaire (sécurité) — pas sur le chemin succès PIN → Home.
        await SessionService.instance.clearSession();
      case PasscodeVerifyInvalidFormat():
      case PasscodeVerifyNotConfigured():
        setState(() => _message = 'Configuration invalide');
    }
  }

  void _onBackspace() {
    setState(() {
      _message = null;
      if (_buffer.isNotEmpty) {
        _buffer = _buffer.substring(0, _buffer.length - 1);
      }
    });
  }

  Future<void> _onForgotPasscode() async {
    final go = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(
          'Réinitialiser le code ?',
          style: GoogleFonts.inter(fontWeight: FontWeight.w600),
        ),
        content: Text(
          'Vous devrez vous reconnecter. La session locale sera effacée.',
          style: GoogleFonts.inter(fontSize: 14, color: AppColors.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text(
              'Annuler',
              style: GoogleFonts.inter(
                fontWeight: FontWeight.w600,
                color: AppColors.textSecondary,
              ),
            ),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(
              'Réinitialiser',
              style: GoogleFonts.inter(
                fontWeight: FontWeight.w600,
                color: AppColors.indigo,
              ),
            ),
          ),
        ],
      ),
    );
    if (go != true || !mounted) return;
    await PasscodeService.instance.clearPasscodeAndLockState();
    SessionStateMachine.instance.apply(SessionLifecycleEvent.logoutStarted);
    // clearSession volontaire (choix utilisateur « code oublié ») — pas sur succès déverrouillage.
    await SessionService.instance.clearSession();
    if (!mounted) return;
    PostLoginLocalSecurityFlow.navigateToLogin0ReplacingStack(context);
  }

  @override
  Widget build(BuildContext context) {
    final errorStyle = AppTypography.itemSupporting.copyWith(
      color: AppColors.semanticNegative,
    );

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppBar(
        backgroundColor: AppColors.pageBackground,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        automaticallyImplyLeading: false,
        title: const SizedBox.shrink(),
      ),
      body: SafeArea(
        top: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(
                      AppSpacing.pageEdge,
                      AppSpacing.sm,
                      AppSpacing.pageEdge,
                      AppSpacing.sm,
                    ),
                    child: Text(
                      _unlockPageTitle,
                      textAlign: TextAlign.center,
                      style: AppTypography.headerSecondary.copyWith(
                        color: AppColors.textPrimary,
                      ),
                    ),
                  ),
                  Expanded(
                    child: Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          _dashboardLoading
                              ? const PinDotsWaveLoadingRow()
                              : PinDotsRow(filled: _buffer.length),
                          const SizedBox(height: AppSpacing.md),
                          SizedBox(
                            height: _messageSlotHeight,
                            width: double.infinity,
                            child: Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: AppSpacing.lg,
                              ),
                              child: Center(
                                child: _message != null && _message!.isNotEmpty
                                    ? Text(
                                        _message!,
                                        textAlign: TextAlign.center,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: errorStyle,
                                      )
                                    : const SizedBox.shrink(),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.md),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  NumericPinKeypad(
                    onDigit: _onDigit,
                    onBackspace: _onBackspace,
                    enabled: !_dashboardLoading,
                    onBiometric: _showBiometricCtas
                        ? () => _tryBiometric(autoTrigger: false)
                        : null,
                    biometricIconKind: _showBiometricCtas
                        ? (_bioKeypadKind ??
                            BiometricKeypadIconKind.fingerprint)
                        : null,
                    biometricEnabled: !_bioInFlight && !_dashboardLoading,
                  ),
                  const SizedBox(height: AppSpacing.s8),
                  Center(
                    child: TextButton(
                      onPressed: _onForgotPasscode,
                      style: TextButton.styleFrom(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.lg,
                          vertical: AppSpacing.sm,
                        ),
                      ),
                      child: Text(
                        'Code d’accès oublié ?',
                        style: GoogleFonts.inter(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: AppColors.indigo,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
