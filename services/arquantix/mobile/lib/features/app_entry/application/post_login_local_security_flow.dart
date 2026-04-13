import 'dart:developer' as developer;

import 'package:flutter/material.dart';

import 'package:arquantix_news/features/registration/screens/registration_flow_screen.dart';

import '../../../core/app_nav_routes.dart';
import '../../profile/application/security_preferences_coordinator.dart';
import '../../security/onboarding/push_notifications_onboarding_screen.dart';
import '../../security/passcode/data/passcode_service.dart';
import '../../security/passcode/data/session_service.dart';
import '../domain/post_auth_sensitive_flow_policy.dart';
import 'app_entry_bootstrap.dart';

/// Après auth serveur réussie (OTP, passkey, e-mail OTP) : sécurité locale puis shell.
///
/// Ne stocke pas les tokens — doit être appelé **après** [SessionService.storeTokens].
///
/// **Continuité sûre (même exécution)** : enchaînement login → setup PIN ou Secure Gate ici ;
/// au **cold start**, une session sans PIN ne reprend pas ce flux (voir
/// [PostAuthSensitiveFlowPolicy], [AppEntryBootstrap.resolveInitialRootWidget]).
class PostLoginLocalSecurityFlow {
  PostLoginLocalSecurityFlow._();

  /// Après stockage des jetons (OTP, passkey) : si le JWT n’est pas **ACTIVE** (PARTIAL / ``sec_inc``),
  /// enchaîner le flux **inscription / reprise** après création du PIN (même drapeau que l’inscription mobile).
  static Future<void> flagRegistrationResumeIfAccountNotActive() async {
    if (!await SessionService.instance.isLastStoredAccessAccountActive()) {
      await SessionService.instance.setPendingEuRegistrationAfterPasscode(true);
    }
  }

  /// Remplace toute la pile login par configuration PIN ou déverrouillage direct (sans écran login intermédiaire).
  static Future<void> navigateReplacingLoginStack(BuildContext context) async {
    await PasscodeService.instance.init();
    if (!context.mounted) return;

    await _maybeShowRegistrationPushOnboardingAfterAuth(context);
    if (!context.mounted) return;

    if (!PasscodeService.instance.isPasscodeConfigured) {
      _logRegistrationFlow('next_step', {'target': 'passcode_setup'});
      await Navigator.of(context).pushNamedAndRemoveUntil<void>(
        AppNavRoutes.passcodeSetupBootstrap,
        (_) => false,
      );
      return;
    }

    // PIN déjà présent sur l’appareil : on ne repasse pas par [PasscodeSetupScreen],
    // donc il faut consommer ici le même flag que après création du PIN (inscription EU).
    final pendingEuRegistration =
        await SessionService.instance.consumePendingEuRegistrationAfterPasscode();
    if (!context.mounted) return;
    if (pendingEuRegistration) {
      _logRegistrationFlow('next_step', {'target': 'registration_flow_kyc'});
      await Navigator.of(context).pushAndRemoveUntil<void>(
        MaterialPageRoute<void>(
          builder: (_) => const RegistrationFlowScreen(
            jurisdiction: 'EU',
            rootPresentation: true,
          ),
        ),
        (_) => false,
      );
      return;
    }

    _logRegistrationFlow('next_step', {'target': 'main_shell'});
    await AppEntryBootstrap.pushRootReplacingAll(
      context,
      forcePostAuthUnlock: true,
    );
  }

  /// Gate unique post-auth : onboarding notifications **avant** création PIN / KYC ([PushNotificationOnboardingPromptState.neverSeen]).
  static Future<void> _maybeShowRegistrationPushOnboardingAfterAuth(
    BuildContext context,
  ) async {
    await PasscodeService.instance.init();
    if (!context.mounted) return;
    final local = await PasscodeService.instance.getPushOnboardingPromptState();
    if (!context.mounted) return;
    final lastAt =
        await PasscodeService.instance.getLastAutomaticPushOnboardingPromptAt();
    if (!context.mounted) return;
    if (!SecurityPreferencesCoordinator.shouldOfferRegistrationPushOnboarding(
      local,
      lastAutomaticPromptAt: lastAt,
    )) {
      _logRegistrationFlow('notifications_gate', {'outcome': 'skipped'});
      return;
    }
    _logRegistrationFlow('notifications_gate', {'outcome': 'shown'});
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        fullscreenDialog: true,
        builder: (_) => const PushNotificationsOnboardingScreen(
          kind: PushNotificationsOnboardingKind.registration,
        ),
      ),
    );
  }

  static void _logRegistrationFlow(
    String event, [
    Map<String, Object?>? data,
  ]) {
    developer.log(
      data == null ? event : '$event ${data.toString()}',
      name: 'RegistrationFlow',
    );
  }

  /// Après « code oublié » ou reset local : retour Login0.
  static void navigateToLogin0ReplacingStack(BuildContext context) {
    Navigator.of(context).pushNamedAndRemoveUntil<void>(
      AppNavRoutes.welcome,
      (_) => false,
    );
  }
}
