import '../../../features/security/passcode/data/session_service.dart';
import 'session_lifecycle_state.dart';
import 'session_state_machine.dart';

/// Aligne la machine d’état sur le stockage au **cold start** (avant login / unlock).
///
/// Évite un décalage `anonymous` alors que des jetons sont déjà présents.
Future<void> reconcileSessionLifecycleOnColdStart() async {
  final has = await SessionService.instance.hasSessionCredentials();
  final machine = SessionStateMachine.instance;
  if (!has) {
    machine.replaceState(SessionLifecycleState.anonymous, reason: 'reconcile_no_token');
    return;
  }
  if (machine.state == SessionLifecycleState.anonymous) {
    machine.apply(SessionLifecycleEvent.coldStartTokensPresent);
  }
}
