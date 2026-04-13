import 'config.dart';

/// URLs pour l’auth FastAPI (distinct du BFF Next.js [Config.apiBaseUrl]).
class SecureApiConfig {
  SecureApiConfig._();

  /// Défini au build : `--dart-define=AUTH_API_BASE_URL=http://hôte:8000` (sans slash final).
  /// En prod ou si l’auth n’est pas sur le port 8000 du même hôte que le BFF, ce define est obligatoire.
  static const String authApiBaseUrl = String.fromEnvironment(
    'AUTH_API_BASE_URL',
    defaultValue: '',
  );

  /// URL de base FastAPI pour passkeys, refresh, login SMS.
  /// Si [authApiBaseUrl] est vide : même hôte que [Config.apiBaseUrl], port **8000** (dev local typique).
  static String get resolvedAuthApiBaseUrl {
    final explicit = authApiBaseUrl.trim();
    if (explicit.isNotEmpty) {
      return explicit.replaceAll(RegExp(r'/$'), '');
    }
    try {
      final u = Uri.parse(Config.apiBaseUrl);
      return u.replace(port: 8000).toString().replaceAll(RegExp(r'/$'), '');
    } catch (_) {
      return '';
    }
  }

  static bool get hasAuthBackend => resolvedAuthApiBaseUrl.isNotEmpty;
}
