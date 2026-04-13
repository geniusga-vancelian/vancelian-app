import 'package:flutter/material.dart';

import '../../../design_system/components/ds_text_confirm_modale.dart';
import '../presentation/screens/welcome_landing_screen.dart';
import '../../../core/session/session_lifecycle_state.dart';
import '../../../core/session/session_state_machine.dart';
import '../../security/passcode/data/session_service.dart';

/// Déconnexion locale : révoque la session distante si possible, efface les jetons.
///
/// Le **passcode local** (par `sub` JWT) **n’est pas** effacé ici : il reste lié au
/// compte sur cet appareil pour enchaîner sur Secure Gate au prochain login.
/// Réinitialisation PIN : écran déverrouillage « code oublié » ou effacement données app.
class AuthLogout {
  AuthLogout._();

  /// Modale de confirmation (pas snackbar / toast) puis déconnexion et retour accueil.
  static Future<void> confirmSignOutAndGoToWelcome(BuildContext context) async {
    final go = await DsTextConfirmModale.show(
      context,
      title: 'Déconnexion',
      message:
          'Vous allez être déconnecté et renvoyé à l’écran d’accueil.',
      cancelLabel: 'Annuler',
      confirmLabel: 'Déconnexion',
      useRootNavigator: true,
    );
    if (go != true || !context.mounted) return;
    await signOut();
    if (!context.mounted) return;
    Navigator.of(context, rootNavigator: true).pushAndRemoveUntil(
      MaterialPageRoute<void>(
        builder: (_) => const WelcomeLandingScreen(),
      ),
      (_) => false,
    );
  }

  static Future<void> signOut() async {
    SessionStateMachine.instance.apply(SessionLifecycleEvent.logoutStarted);
    try {
      await SessionService.instance.revokeRemoteSession();
    } catch (_) {
      await SessionService.instance.clearSession();
    }
  }
}
