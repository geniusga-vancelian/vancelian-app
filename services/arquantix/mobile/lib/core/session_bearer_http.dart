import 'package:flutter/foundation.dart';

import '../features/security/passcode/data/session_service.dart';

/// Jeton attendu pour un appel [SessionBearerPolicy.required] mais absent.
class MissingBearerTokenException implements Exception {
  MissingBearerTokenException(this.debugTag);

  final String debugTag;

  @override
  String toString() =>
      'MissingBearerTokenException($debugTag): access token requis';
}

/// Politique d’en-tête pour les appels API.
///
/// - [optional] : ajoute `Authorization: Bearer` si un jeton est lisible ; sinon requête anonyme
///   (flux public / démo) — log debug `bearer=absent`.
/// - [required] : sans jeton lisible → [MissingBearerTokenException] + log `[API] ERROR`.
enum SessionBearerPolicy {
  optional,
  required,
}

typedef SessionBearerAccessTokenReader = Future<String?> Function();

/// En-têtes HTTP avec jeton de session injecté automatiquement depuis [SessionService].
///
/// Objectif : éviter les requêtes user-scoped **sans** Bearer quand un jeton est stocké,
/// et refuser explicitement les appels [SessionBearerPolicy.required] sans jeton.
class SessionBearerHttp {
  SessionBearerHttp._();

  /// Tests uniquement : remplace la lecture du jeton (réinitialiser à `null` après le test).
  @visibleForTesting
  static SessionBearerAccessTokenReader? debugAccessTokenReader;

  static Future<String?> _readAccessToken() async {
    final r = debugAccessTokenReader;
    if (r != null) return r();
    return SessionService.instance.readAccessToken();
  }

  /// En-têtes JSON : `Accept: application/json` ; `Authorization: Bearer` si jeton présent.
  ///
  /// Si [withJsonContentType] : ajoute `Content-Type: application/json` (POST/PUT corps JSON).
  static Future<Map<String, String>> jsonHeaders({
    required Uri uri,
    required String debugTag,
    SessionBearerPolicy policy = SessionBearerPolicy.optional,
    String? overrideAccessToken,
    bool withJsonContentType = false,
  }) async {
    String? token;
    if (overrideAccessToken != null && overrideAccessToken.trim().isNotEmpty) {
      token = overrideAccessToken.trim();
    } else {
      token = await _readAccessToken();
      if (token != null && token.trim().isEmpty) token = null;
    }

    final has = token != null && token.isNotEmpty;

    if (kDebugMode) {
      final path = uri.path.isEmpty ? '/' : uri.path;
      debugPrint(
        '[API] $debugTag $path bearer=${has ? 'present' : 'absent'}',
      );
    }

    if (policy == SessionBearerPolicy.required && !has) {
      debugPrint(
        '[API] ERROR request without bearer (required) $debugTag',
      );
      throw MissingBearerTokenException(debugTag);
    }

    final h = <String, String>{
      'Accept': 'application/json',
    };
    if (withJsonContentType) {
      h['Content-Type'] = 'application/json';
    }
    if (has) {
      h['Authorization'] = 'Bearer $token';
    }
    return h;
  }

  /// En-têtes pour l’app mobile (bootstrap, wallet, `/api/app/*`, `/api/mobile/flutter/*`).
  ///
  /// Avec JWT, l’API résout le client PE à partir du token. Sans session, le comportement
  /// dépend des garde-fous API (souvent 401/404 si route protégée). Dès qu’un **access token**
  /// est stocké, on impose [SessionBearerPolicy.required] pour ne pas appeler les routes
  /// applicatives sans identité.
  static Future<Map<String, String>> jsonHeadersAppScoped({
    required Uri uri,
    required String debugTag,
    String? overrideAccessToken,
    bool withJsonContentType = false,
  }) async {
    final hasSession = await SessionService.instance.hasSessionCredentials();
    return jsonHeaders(
      uri: uri,
      debugTag: debugTag,
      policy: hasSession ? SessionBearerPolicy.required : SessionBearerPolicy.optional,
      overrideAccessToken: overrideAccessToken,
      withJsonContentType: withJsonContentType,
    );
  }

  /// En-têtes pour téléchargement binaire (PDF, etc.) : `Accept` personnalisable, Bearer si session.
  static Future<Map<String, String>> downloadHeadersAppScoped({
    required Uri uri,
    required String debugTag,
    String accept = 'application/pdf',
    String? overrideAccessToken,
  }) async {
    String? token;
    if (overrideAccessToken != null && overrideAccessToken.trim().isNotEmpty) {
      token = overrideAccessToken.trim();
    } else {
      token = await _readAccessToken();
      if (token != null && token.trim().isEmpty) token = null;
    }

    final hasSession = await SessionService.instance.hasSessionCredentials();
    final policy =
        hasSession ? SessionBearerPolicy.required : SessionBearerPolicy.optional;
    final has = token != null && token.isNotEmpty;

    if (kDebugMode) {
      final path = uri.path.isEmpty ? '/' : uri.path;
      debugPrint(
        '[API] $debugTag $path bearer=${has ? 'present' : 'absent'} (binary)',
      );
    }

    if (policy == SessionBearerPolicy.required && !has) {
      debugPrint(
        '[API] ERROR request without bearer (required) $debugTag',
      );
      throw MissingBearerTokenException(debugTag);
    }

    final h = <String, String>{
      'Accept': accept,
    };
    if (has) {
      h['Authorization'] = 'Bearer $token';
    }
    return h;
  }
}
