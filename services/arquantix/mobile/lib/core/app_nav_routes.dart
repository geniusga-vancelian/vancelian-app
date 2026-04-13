/// Routes nommées globales — évitent les imports circulaires (setup PIN ↔ secure gate).
abstract final class AppNavRoutes {
  static const welcome = '/app/welcome';

  /// Configuration PIN après login ou cold start sans PIN (pile remplacée ensuite par secure gate).
  static const passcodeSetupBootstrap = '/app/passcode-setup-bootstrap';

  /// Cold start : session + PIN OK.
  static const secureGate = '/app/secure-gate';

  /// Juste après auth serveur ou fin de setup PIN : forcer le passage biométrie / PIN.
  static const secureGatePostAuth = '/app/secure-gate-post-auth';
}
