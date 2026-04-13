import 'dart:convert';
import 'package:http/http.dart' as http;

/// Result wrapper for Registration API calls.
class ApiResult<T> {
  final T? data;
  final int statusCode;
  final String? errorMessage;
  final String? errorCode;
  /// Backend validation target field (e.g. `phone_number`) when `detail` is structured.
  final String? fieldSlug;
  /// Optional UX hint (e.g. FR `+330…` trunk digit) from structured 422 `message_hint`.
  final String? messageHint;
  final Map<String, String>? fieldErrors;
  /// From standardized 429 body (`detail.error.retry_after`) when present.
  final int? retryAfterSeconds;

  const ApiResult({
    this.data,
    required this.statusCode,
    this.errorMessage,
    this.errorCode,
    this.fieldSlug,
    this.messageHint,
    this.fieldErrors,
    this.retryAfterSeconds,
  });

  bool get isSuccess => statusCode >= 200 && statusCode < 300;
  bool get isValidationError => statusCode == 422;
  bool get isBlocked => statusCode == 409;
  bool get isRateLimited => statusCode == 429;
  bool get isAuthError => statusCode == 401 || statusCode == 403;
}

/// Client for the Registration Flow runtime API.
///
/// All methods return [ApiResult] with parsed JSON data or structured errors.
class RegistrationApi {
  RegistrationApi({
    required this.baseUrl,
    /// Si fourni, ajoute ``Authorization: Bearer`` pour les appels (session post-login).
    this.accessTokenResolver,
  });

  final String baseUrl;

  /// Résout le jeton d’accès (ex. [SessionService.readAccessToken]) ; peut retourner null.
  final Future<String?> Function()? accessTokenResolver;

  Future<Map<String, String>> _headers() async {
    final h = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    final resolver = accessTokenResolver;
    if (resolver != null) {
      final tok = await resolver();
      if (tok != null && tok.isNotEmpty) {
        h['Authorization'] = 'Bearer $tok';
      }
    }
    return h;
  }

  Future<ApiResult<Map<String, dynamic>>> getCurrentJurisdiction() async {
    return _get('/api/registration/runtime/current-jurisdiction');
  }

  Future<ApiResult<Map<String, dynamic>>> getActiveFlow(
      String jurisdiction) async {
    return _get('/api/registration/flows/active?jurisdiction=$jurisdiction');
  }

  Future<ApiResult<Map<String, dynamic>>> startSession({
    required String jurisdiction,
    String? flowId,
    String? personId,
    String? clientId,
  }) async {
    final body = <String, dynamic>{'jurisdiction': jurisdiction};
    if (flowId != null) body['flow_id'] = flowId;
    if (personId != null) body['person_id'] = personId;
    if (clientId != null) body['client_id'] = clientId;
    return _post('/api/registration/sessions/start', body);
  }

  Future<ApiResult<Map<String, dynamic>>> getCurrentScreen(
      String sessionId) async {
    return _get('/api/registration/sessions/$sessionId/screen');
  }

  Future<ApiResult<Map<String, dynamic>>> submitScreen(
    String sessionId,
    Map<String, dynamic> answers,
  ) async {
    return _post(
      '/api/registration/sessions/$sessionId/submit',
      {'answers': answers},
    );
  }

  Future<ApiResult<Map<String, dynamic>>> nextScreen(String sessionId) async {
    return _post('/api/registration/sessions/$sessionId/next', null);
  }

  Future<ApiResult<Map<String, dynamic>>> prevScreen(String sessionId) async {
    return _post('/api/registration/sessions/$sessionId/prev', null);
  }

  Future<ApiResult<Map<String, dynamic>>> completeSession(
      String sessionId) async {
    return _post('/api/registration/sessions/$sessionId/complete', null);
  }

  Future<ApiResult<Map<String, dynamic>>> prepareInteraction(
      String sessionId) async {
    return _post(
      '/api/registration/sessions/$sessionId/interaction/prepare',
      <String, dynamic>{},
    );
  }

  Future<ApiResult<Map<String, dynamic>>> resendInteraction(
    String sessionId, {
    required String screenId,
    required String interactionType,
  }) async {
    return _post(
      '/api/registration/sessions/$sessionId/interaction/resend',
      <String, dynamic>{
        'screen_id': screenId,
        'interaction_type': interactionType,
      },
    );
  }

  /// Google Places proxy (clé API uniquement côté serveur).
  Future<ApiResult<Map<String, dynamic>>> addressAutocomplete(
    String q, {
    String? region,
    List<String>? allowedCountriesIso2,
    /// ISO 3166-1 alpha-2 — restricts Places autocomplete to this country (server param `country`).
    String? countryIso2,
  }) async {
    final qp = <String, String>{'q': q};
    if (region != null && region.length == 2) {
      qp['region'] = region.toUpperCase();
    }
    if (countryIso2 != null && countryIso2.trim().length == 2) {
      qp['country'] = countryIso2.trim().toUpperCase();
    }
    if (allowedCountriesIso2 != null && allowedCountriesIso2.isNotEmpty) {
      final codes = allowedCountriesIso2
          .map((c) => c.trim().toUpperCase())
          .where((c) => c.length == 2)
          .toSet()
          .toList();
      if (codes.isNotEmpty) {
        qp['allowed_countries'] = codes.join(',');
      }
    }
    final uri = Uri.parse('$baseUrl/api/address/autocomplete')
        .replace(queryParameters: qp);
    try {
      final resp = await http.get(uri, headers: await _headers());
      return _parseResponse(resp);
    } catch (e) {
      return ApiResult(statusCode: 0, errorMessage: 'Connection error: $e');
    }
  }

  Future<ApiResult<Map<String, dynamic>>> addressDetails(
    String placeId, {
    List<String>? allowedCountriesIso2,
    /// ISO 3166-1 alpha-2 — expected residence (server param `country`, same as autocomplete).
    String? countryIso2,
  }) async {
    final qp = <String, String>{'place_id': placeId};
    if (countryIso2 != null && countryIso2.trim().length == 2) {
      qp['country'] = countryIso2.trim().toUpperCase();
    }
    if (allowedCountriesIso2 != null && allowedCountriesIso2.isNotEmpty) {
      final codes = allowedCountriesIso2
          .map((c) => c.trim().toUpperCase())
          .where((c) => c.length == 2)
          .toSet()
          .toList();
      if (codes.isNotEmpty) {
        qp['allowed_countries'] = codes.join(',');
      }
    }
    final uri =
        Uri.parse('$baseUrl/api/address/details').replace(queryParameters: qp);
    try {
      final resp = await http.get(uri, headers: await _headers());
      return _parseResponse(resp);
    } catch (e) {
      return ApiResult(statusCode: 0, errorMessage: 'Connection error: $e');
    }
  }

  Future<ApiResult<Map<String, dynamic>>> completeInteraction(
    String sessionId, {
    required String screenId,
    required String interactionType,
    required String challengeId,
    required bool verified,
  }) async {
    return _post(
      '/api/registration/sessions/$sessionId/interaction/complete',
      <String, dynamic>{
        'screen_id': screenId,
        'interaction_type': interactionType,
        'challenge_id': challengeId,
        'verified': verified,
      },
    );
  }

  // ── Internal ────────────────────────────────────────────────────────────

  Future<ApiResult<Map<String, dynamic>>> _get(String path) async {
    try {
      final resp = await http.get(
        Uri.parse('$baseUrl$path'),
        headers: await _headers(),
      );
      return _parseResponse(resp);
    } catch (e) {
      return ApiResult(statusCode: 0, errorMessage: 'Connection error: $e');
    }
  }

  Future<ApiResult<Map<String, dynamic>>> _post(
      String path, Map<String, dynamic>? body) async {
    try {
      final resp = await http.post(
        Uri.parse('$baseUrl$path'),
        headers: await _headers(),
        body: body != null ? jsonEncode(body) : null,
      );
      return _parseResponse(resp);
    } catch (e) {
      return ApiResult(statusCode: 0, errorMessage: 'Connection error: $e');
    }
  }

  /// Exposed for unit tests (429/422 parsing).
  ApiResult<Map<String, dynamic>> testOnlyParseResponse(http.Response resp) =>
      _parseResponse(resp);

  ApiResult<Map<String, dynamic>> _parseResponse(http.Response resp) {
    if (resp.statusCode >= 200 && resp.statusCode < 300) {
      final data = jsonDecode(resp.body) as Map<String, dynamic>;
      return ApiResult(data: data, statusCode: resp.statusCode);
    }

    if (resp.statusCode == 422) {
      return _parse422(resp);
    }

    if (resp.statusCode == 429) {
      return _parse429(resp);
    }

    // 409, 401, 403, 404, 5xx, etc.
    String? message;
    String? errCode;
    try {
      final data = jsonDecode(resp.body) as Map<String, dynamic>;
      final detail = data['detail'];
      if (detail is String) {
        message = detail;
      } else if (detail is Map) {
        if (detail['message'] is String) {
          message = detail['message'] as String;
        }
        if (detail['code'] is String) {
          errCode = detail['code'] as String;
        }
      }
    } catch (_) {
      message = 'Server error (${resp.statusCode})';
    }
    message = _humanizeRegistrationErrorMessage(resp.statusCode, message);
    return ApiResult(
      statusCode: resp.statusCode,
      errorMessage: message,
      errorCode: errCode,
    );
  }

  /// Messages FR pour l’UX ; évite d’afficher brut « Internal Server Error ».
  static String _humanizeRegistrationErrorMessage(int status, String? raw) {
    final r = (raw ?? '').trim();
    final lower = r.toLowerCase();
    if (status == 404) {
      if (lower.contains('no current jurisdiction')) {
        return 'Aucune juridiction courante n’est configurée sur le serveur. '
            'Définissez-la dans l’admin (registration runtime).';
      }
      return r.isEmpty ? 'Ressource introuvable (404).' : r;
    }
    if (status >= 500) {
      if (r.isEmpty ||
          lower == 'internal server error' ||
          r.startsWith('Server error (')) {
        return 'Le serveur d’inscription a rencontré une erreur. '
            'Vérifiez que l’API FastAPI tourne (souvent le port 8000) et les logs '
            '(/tmp/arquantix-api.log). Sur un téléphone physique, l’URL doit '
            'pointer vers l’IP de votre machine (pas localhost).';
      }
    }
    if (status == 503) {
      return r.isEmpty
          ? 'Service temporairement indisponible. Réessayez dans un instant.'
          : r;
    }
    return r.isEmpty ? 'Erreur serveur ($status).' : r;
  }

  ApiResult<Map<String, dynamic>> _parse429(http.Response resp) {
    try {
      final data = jsonDecode(resp.body) as Map<String, dynamic>;
      final detail = data['detail'];
      if (detail is Map) {
        final err = detail['error'];
        if (err is Map) {
          final msg = err['message'] as String? ??
              'Too many address lookups. Please wait a moment.';
          final code = err['code'] as String?;
          final ra = err['retry_after'];
          int? retry;
          if (ra is int) {
            retry = ra;
          } else if (ra != null) {
            retry = int.tryParse(ra.toString());
          }
          return ApiResult(
            statusCode: 429,
            errorMessage: msg,
            errorCode: code,
            retryAfterSeconds: retry,
          );
        }
      }
    } catch (_) {
      /* fall through */
    }
    return const ApiResult(
      statusCode: 429,
      errorMessage:
          'Too many address lookups. Please wait a moment and try again.',
      errorCode: 'rate_limited',
    );
  }

  ApiResult<Map<String, dynamic>> _parse422(http.Response resp) {
    try {
      final data = jsonDecode(resp.body) as Map<String, dynamic>;
      final detail = data['detail'];

      if (detail is Map) {
        final m = Map<String, dynamic>.from(detail);
        if (m.containsKey('code') || m.containsKey('message')) {
          final f = m['field'];
          final hint = m['message_hint'];
          return ApiResult(
            statusCode: 422,
            errorMessage: m['message'] as String? ?? 'Validation error',
            errorCode: m['code'] as String?,
            fieldSlug: f is String ? f : null,
            messageHint: hint is String ? hint : null,
          );
        }
        final nested = m['error'];
        if (nested is Map && nested['code'] is String) {
          return ApiResult(
            statusCode: 422,
            errorMessage: nested['message'] as String? ?? 'Validation error',
            errorCode: nested['code'] as String?,
          );
        }
      }

      if (detail is String) {
        // Backend validation: "Validation failed: email: Invalid email format"
        final fieldErrors = <String, String>{};
        final parts = detail.split('; ');
        for (final part in parts) {
          if (part.startsWith('Validation failed: ')) {
            final rest = part.substring('Validation failed: '.length);
            for (final fieldErr in rest.split('; ')) {
              final idx = fieldErr.indexOf(': ');
              if (idx > 0) {
                fieldErrors[fieldErr.substring(0, idx)] =
                    fieldErr.substring(idx + 2);
              }
            }
          }
        }
        return ApiResult(
          statusCode: 422,
          errorMessage: detail,
          fieldErrors: fieldErrors.isNotEmpty ? fieldErrors : null,
        );
      }

      if (detail is List) {
        // Pydantic validation errors
        final fieldErrors = <String, String>{};
        for (final e in detail) {
          if (e is Map<String, dynamic>) {
            final loc = e['loc'] as List<dynamic>?;
            final msg = e['msg'] as String? ?? 'Invalid';
            if (loc != null && loc.isNotEmpty) {
              fieldErrors[loc.last.toString()] = msg;
            }
          }
        }
        return ApiResult(
          statusCode: 422,
          errorMessage: 'Validation error',
          fieldErrors: fieldErrors,
        );
      }

      return ApiResult(statusCode: 422, errorMessage: 'Validation error');
    } catch (_) {
      return ApiResult(statusCode: 422, errorMessage: 'Validation error');
    }
  }
}
