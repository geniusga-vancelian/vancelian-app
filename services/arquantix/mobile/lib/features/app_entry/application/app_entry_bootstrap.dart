import 'dart:async';

import 'package:flutter/material.dart';

import '../../../core/post_auth_flow_security_events.dart';
import '../../../core/session/session_lifecycle_reconcile.dart';
import '../../../core/session/session_lifecycle_state.dart';
import '../../../core/session/session_state_machine.dart';
import '../../auth/presentation/screens/welcome_landing_screen.dart';
import '../../security/passcode/data/passcode_service.dart';
import '../../security/passcode/data/session_service.dart';
import '../../security/passcode/domain/secure_access_config.dart';
import '../../security/passcode/presentation/screens/passcode_unlock_screen.dart';
import '../../shell/presentation/screens/main_shell_screen.dart';
import 'post_auth_navigation_flags.dart';

/// Résout le widget racine après les mêmes règles que l’ancien enchaînement
/// AppEntryRouter → SecureGate (évite les écrans intermédiaires à indicateur seul).
class AppEntryBootstrap {
  AppEntryBootstrap._();

  /// Après un **redémarrage** de l’app : jetons présents mais aucun passcode local
  /// ne doit pas rouvrir l’écran de création PIN (risque si crash avant fin du flux).
  /// On force une déconnexion complète ; le flux « juste après login » passe par
  /// [AppNavRoutes.passcodeSetupBootstrap], pas par ce resolver.
  static Future<void> _logoutIfSessionWithoutPasscode() async {
    PostAuthFlowSecurityEvents.interruptedSensitiveFlowRevoked(
      reason: 'session_without_passcode_cold_start',
    );
    await SessionService.instance.revokeRemoteSession();
  }

  /// [skipPasscodeUnlock] : cas inscription EU terminée juste après création du PIN
  /// (même session) — évite une 3ᵉ saisie du code. Ne pas utiliser au cold start.
  static Future<Widget> resolveInitialRootWidget({
    bool forcePostAuthUnlock = false,
    bool skipPasscodeUnlock = false,
  }) async {
    await reconcileSessionLifecycleOnColdStart();
    final hasServer = await SessionService.instance.hasSessionCredentials();
    if (!hasServer) {
      unawaited(PasscodeService.instance.init());
      return const WelcomeLandingScreen();
    }
    await PasscodeService.instance.init();
    // Filet de sécurité : si le réseau ou le backend reste silencieux, ne jamais
    // bloquer l’affichage du welcome au-delà de quelques secondes.
    // (Un timeout trop long fige Login0 : pas d’anim logo / pas de boutons tant que
    // [AppLaunchRoot] garde bootstrapPending — ressenti « 10 s de rien » sur device.)
    final valid = await SessionService.instance
        .isSessionValid()
        .timeout(const Duration(seconds: 4), onTimeout: () => false);
    if (!valid) {
      return const WelcomeLandingScreen();
    }
    if (!PasscodeService.instance.isPasscodeConfigured) {
      await _logoutIfSessionWithoutPasscode();
      return const WelcomeLandingScreen();
    }
    if (skipPasscodeUnlock) {
      SessionStateMachine.instance.apply(SessionLifecycleEvent.passcodeUnlocked);
      return const MainShellScreen();
    }
    final needUnlock = SecureAccessConfig.requireUnlockWhenPasscodeSet ||
        forcePostAuthUnlock;
    if (!needUnlock) {
      SessionStateMachine.instance.apply(SessionLifecycleEvent.passcodeUnlocked);
      return const MainShellScreen();
    }
    return const PasscodeUnlockScreen();
  }

  /// Remplace toute la pile par [resolveInitialRootWidget] (une transition).
  ///
  /// [suppressNextMainShellPushReloginPrompt] : inscription fraîche vers le shell
  /// (souvent avec [skipPasscodeUnlock]) — évite le re-prompt notifications sur la même montée.
  static Future<void> pushRootReplacingAll(
    BuildContext context, {
    bool forcePostAuthUnlock = false,
    bool skipPasscodeUnlock = false,
    bool suppressNextMainShellPushReloginPrompt = false,
  }) async {
    if (suppressNextMainShellPushReloginPrompt) {
      PostAuthNavigationFlags.suppressNextMainShellPushReloginPrompt = true;
    }
    final next = await resolveInitialRootWidget(
      forcePostAuthUnlock: forcePostAuthUnlock,
      skipPasscodeUnlock: skipPasscodeUnlock,
    );
    if (!context.mounted) return;
    Navigator.of(context).pushAndRemoveUntil<void>(
      MaterialPageRoute<void>(builder: (_) => next),
      (_) => false,
    );
  }
}
