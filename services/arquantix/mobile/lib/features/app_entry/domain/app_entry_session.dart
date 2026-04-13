import '../../../core/post_auth_flow_security_events.dart';
import '../../security/passcode/data/passcode_service.dart';
import '../../security/passcode/data/session_service.dart';
import 'app_entry_destination.dart';
import 'app_entry_ux_state.dart';

/// Helpers centralisés pour l’orchestration d’entrée (sans dupliquer le stockage session).
class AppEntrySession {
  AppEntrySession._();

  /// Au moins un access token présent localement (validité serveur non vérifiée).
  static Future<bool> hasStoredTokens() =>
      SessionService.instance.hasSessionCredentials();

  /// Jetons présents et session utilisable (refresh si besoin ; peut effacer la session).
  static Future<bool> hasValidServerSession() async {
    if (!await hasStoredTokens()) return false;
    return SessionService.instance.isSessionValid();
  }

  static Future<bool> hasPasscodeConfigured() async {
    await PasscodeService.instance.init();
    return PasscodeService.instance.isPasscodeConfigured;
  }

  /// Session serveur OK + PIN local configuré → écran type Secure Gate pertinent.
  static Future<bool> shouldOpenSecureGate() async {
    if (!await hasValidServerSession()) return false;
    return hasPasscodeConfigured();
  }

  /// Résout l’état UX courant (pour logs, tests d’intégration, analytics).
  static Future<AppEntryUxState> resolveUxState() async {
    await PasscodeService.instance.init();
    if (!await hasStoredTokens()) {
      return AppEntryUxState.loggedOut;
    }
    final valid = await SessionService.instance.isSessionValid();
    if (!valid) {
      return AppEntryUxState.loggedOut;
    }
    if (!PasscodeService.instance.isPasscodeConfigured) {
      return AppEntryUxState.serverAuthenticatedButLocalSecurityNotSetup;
    }
    return AppEntryUxState.serverAuthenticatedAndLocalSecurityReady;
  }

  /// Destination pour [AppEntryRouter] après splash.
  ///
  /// Jetons valides sans passcode local : déconnexion (révoque / efface) puis [login0].
  static Future<AppEntryDestination> resolveDestination() async {
    await PasscodeService.instance.init();
    if (!await hasStoredTokens()) {
      return AppEntryDestination.login0;
    }
    final valid = await SessionService.instance.isSessionValid();
    if (!valid) {
      return AppEntryDestination.login0;
    }
    if (!PasscodeService.instance.isPasscodeConfigured) {
      PostAuthFlowSecurityEvents.interruptedSensitiveFlowRevoked(
        reason: 'session_without_passcode_resolve_destination',
      );
      await SessionService.instance.revokeRemoteSession();
      return AppEntryDestination.login0;
    }
    return AppEntryDestination.secureGate;
  }
}
