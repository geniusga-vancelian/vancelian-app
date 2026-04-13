import 'app_entry_ux_state.dart';

/// Destination du routeur maître après bootstrap (splash).
enum AppEntryDestination {
  login0,
  passcodeSetup,
  secureGate,
}

/// Logique pure — testable sans SecureStorage.
///
/// Session valide sans PIN : **login0** (même politique que le bootstrap cold start :
/// pas de reprise sur l’écran création PIN après redémarrage).
AppEntryDestination resolveAppEntryDestination({
  required bool hasStoredTokens,
  required bool sessionStillValid,
  required bool passcodeConfigured,
}) {
  if (!hasStoredTokens || !sessionStillValid) {
    return AppEntryDestination.login0;
  }
  if (!passcodeConfigured) {
    return AppEntryDestination.login0;
  }
  return AppEntryDestination.secureGate;
}

/// Associe l’état UX à une destination de routeur (hors [unlockingLocalAccess]).
AppEntryDestination? destinationForUxState(AppEntryUxState state) {
  return switch (state) {
    AppEntryUxState.loggedOut => AppEntryDestination.login0,
    AppEntryUxState.serverAuthenticatedButLocalSecurityNotSetup =>
      AppEntryDestination.login0,
    AppEntryUxState.serverAuthenticatedAndLocalSecurityReady =>
      AppEntryDestination.secureGate,
    AppEntryUxState.unlockingLocalAccess => null,
  };
}
