import 'dart:async';
import 'dart:convert';
import 'dart:io' show HandshakeException, SocketException, TlsException;

import 'package:http/http.dart' as http;

import '../../../../core/auth_http_logging.dart';
import '../../../../core/secure_api_config.dart';
import '../domain/passkey_exceptions.dart';

/// Extrait un message utilisateur depuis une réponse d’erreur FastAPI (`detail` objet ou chaîne).
String? parseFastApiErrorMessage(String body) {
  try {
    final obj = jsonDecode(body);
    if (obj is! Map<String, dynamic>) return null;
    final detail = obj['detail'];
    if (detail is Map && detail['message'] is String) {
      final m = (detail['message'] as String).trim();
      if (m.isNotEmpty) return m;
    }
    if (detail is Map && detail['error'] is Map) {
      final err = detail['error'] as Map;
      if (err['message'] is String) {
        final m = (err['message'] as String).trim();
        if (m.isNotEmpty) return m;
      }
    }
    if (detail is String && detail.trim().isNotEmpty) return detail.trim();
  } catch (_) {}
  return null;
}

/// Extrait `detail.code` lorsque `detail` est un objet (ex. `security.account_locked`).
String? parseFastApiErrorCode(String body) {
  try {
    final obj = jsonDecode(body);
    if (obj is! Map<String, dynamic>) return null;
    final detail = obj['detail'];
    if (detail is Map && detail['code'] is String) {
      final c = (detail['code'] as String).trim();
      if (c.isNotEmpty) return c;
    }
  } catch (_) {}
  return null;
}

/// Sentinels transport ([PasskeyApi]) — pas exposés à l’UI.
const String _kNetOffline = '__net_offline__';
const String _kNetServerUnreachable = '__net_server_unreachable__';
const String _kNetGeneric = '__net_generic__';
const String _kInternal = '__internal__';

String _classifySocketError(SocketException e) {
  final m = '${e.message} ${e.osError?.message ?? ''}'.toLowerCase();
  if (m.contains('failed host lookup') ||
      m.contains('network is unreachable') ||
      m.contains('no address associated') ||
      m.contains('no route to host')) {
    return _kNetOffline;
  }
  if (m.contains('connection refused') ||
      m.contains('connection reset') ||
      m.contains('broken pipe')) {
    return _kNetServerUnreachable;
  }
  return _kNetGeneric;
}

String _classifyClientErrorMessage(String? message) {
  final m = (message ?? '').toLowerCase();
  if (m.contains('failed host lookup') ||
      m.contains('network is unreachable') ||
      m.contains('no address associated') ||
      m.contains('no route to host')) {
    return _kNetOffline;
  }
  return _kNetServerUnreachable;
}

String _smsLoginNetworkUserMessage(PasskeyApiException e) {
  if (e.statusCode == 408) {
    return 'Le service est temporairement indisponible';
  }
  if (e.statusCode == 0) {
    if (e.body.contains('No auth backend')) {
      return 'URL du serveur d’authentification non configurée. Vérifiez la configuration réseau de l’app.';
    }
    switch (e.body) {
      case _kNetOffline:
        return 'Vérifiez votre connexion internet';
      case _kNetServerUnreachable:
      case _kNetGeneric:
        return 'Le service est temporairement indisponible';
      case _kInternal:
        return 'Une erreur est survenue';
      default:
        if (e.body.startsWith('__net_')) {
          return 'Le service est temporairement indisponible';
        }
        return 'Vérifiez votre connexion internet';
    }
  }
  return '';
}

/// Repli selon le code HTTP lorsque le corps ne contient pas de message exploitable.
String _httpStatusUserMessage(int status, {required bool isVerify}) {
  switch (status) {
    case 400:
      return isVerify
          ? 'La requête est invalide. Vérifiez le code saisi.'
          : 'La requête est invalide. Vérifiez le numéro de mobile.';
    case 401:
      return isVerify
          ? 'Code incorrect ou expiré.'
          : 'Authentification refusée. Utilisez les autres options de connexion si le problème persiste.';
    case 403:
      return isVerify
          ? 'Accès refusé pour ce compte. Réessayez plus tard ou utilisez d’autres options de connexion.'
          : 'Accès refusé. Utilisez les autres options de connexion.';
    case 404:
      return 'Service d’authentification introuvable. Vérifiez la configuration ou contactez le support.';
    case 405:
    case 406:
      return 'Le serveur ne peut pas traiter cette demande. Mettez l’application à jour ou réessayez plus tard.';
    case 408:
      return 'Le service est temporairement indisponible';
    case 409:
      return 'Conflit avec une opération en cours. Fermez l’app et réessayez dans un instant.';
    case 413:
      return 'Données trop volumineuses. Réessayez avec un code à 6 chiffres uniquement.';
    case 422:
      return isVerify
          ? 'Saisie invalide. Entrez le code à 6 chiffres reçu par SMS.'
          : 'Numéro de mobile invalide ou incomplet.';
    case 423:
      return 'Cette ressource est verrouillée. Réessayez plus tard.';
    case 425:
      return 'Opération encore en cours côté serveur. Patientez quelques secondes.';
    case 429:
      return isVerify
          ? 'Trop de tentatives. Patientez quelques instants avant de réessayer.'
          : 'Merci de patienter avant de redemander un code.';
    case 500:
    case 501:
    case 502:
    case 503:
    case 504:
      return 'Le service est temporairement indisponible';
    default:
      if (status >= 400 && status < 500) {
        return isVerify
            ? 'La vérification a échoué. Vérifiez le code ou demandez un nouveau SMS.'
            : 'L’envoi du code a échoué. Vérifiez le numéro ou réessayez plus tard.';
      }
      if (status >= 500) {
        return 'Le service est temporairement indisponible';
      }
      return isVerify
          ? 'Une erreur est survenue'
          : 'Une erreur est survenue';
  }
}

/// Erreur inattendue (parse, plugin) — même texte que le fallback API.
String authFlowSmsStartUnknownUserMessage(Object error, {required bool signUpMode}) {
  if (error is PasskeyApiException) {
    return signUpMode
        ? signupSmsStartFailureUserMessage(error)
        : loginSmsStartFailureUserMessage(error);
  }
  return 'Une erreur est survenue';
}

/// Message utilisateur pour un échec de ``POST /auth/login/sms/start`` (écran téléphone ou OTP).
String loginSmsStartFailureUserMessage(PasskeyApiException e) {
  const verify = false;
  final code = parseFastApiErrorCode(e.body);
  final parsed = parseFastApiErrorMessage(e.body);

  switch (code) {
    case 'resend_rate_limited':
      return 'Merci de patienter avant de redemander un code.';
    case 'sms_unavailable':
      return 'Envoi du SMS impossible pour le moment. Réessayez plus tard ou utilisez une autre méthode de connexion.';
    case 'feature_disabled':
      return 'La connexion par SMS est désactivée sur ce serveur. Utilisez les autres options.';
    case 'phone_required':
      return 'Indiquez un numéro de mobile valide.';
    default:
      break;
  }

  if (parsed != null && parsed.isNotEmpty) return parsed;

  final net = _smsLoginNetworkUserMessage(e);
  if (net.isNotEmpty) return net;

  return _httpStatusUserMessage(e.statusCode, isVerify: verify);
}

/// Message utilisateur pour un échec de ``POST /auth/signup/sms/start``.
String signupSmsStartFailureUserMessage(PasskeyApiException e) {
  final code = parseFastApiErrorCode(e.body);
  final parsed = parseFastApiErrorMessage(e.body);
  if (code == 'signup_phone_unavailable') {
    return parsed ??
        'Impossible de poursuivre cette inscription pour ce numéro. '
            'Utilisez « Me connecter » ou un autre numéro.';
  }
  return loginSmsStartFailureUserMessage(e);
}

/// Message utilisateur pour un échec de ``POST /auth/login/sms/verify``.
String loginSmsVerifyFailureUserMessage(PasskeyApiException e) {
  const verify = true;
  final apiCode = parseFastApiErrorCode(e.body);
  final parsed = parseFastApiErrorMessage(e.body);

  switch (apiCode) {
    case 'security.account_locked':
      return 'Compte temporairement verrouillé pour raison de sécurité. Réessayez plus tard ou utilisez d’autres options de connexion.';
    case 'invalid_or_expired_code':
      return 'Code incorrect ou expiré.';
    case 'too_many_attempts':
      return 'Trop de tentatives avec ce code. Demandez un nouveau SMS puis saisissez le nouveau code.';
    case 'resend_rate_limited':
      return 'Merci de patienter avant de redemander un code.';
    case 'feature_disabled':
      return 'La connexion par SMS est désactivée sur ce serveur.';
    case 'sms_unavailable':
      return 'Le service SMS est indisponible. Réessayez plus tard ou utilisez une autre méthode de connexion.';
    case 'phone_required':
      return 'Numéro de mobile manquant ou invalide.';
    default:
      break;
  }

  if (parsed != null && parsed.isNotEmpty) return parsed;

  final net = _smsLoginNetworkUserMessage(e);
  if (net.isNotEmpty) return net;

  return _httpStatusUserMessage(e.statusCode, isVerify: verify);
}

/// Message utilisateur pour un échec de ``POST /auth/login/email-otp/start``.
String loginEmailOtpStartFailureUserMessage(PasskeyApiException e) {
  final code = parseFastApiErrorCode(e.body);
  final parsed = parseFastApiErrorMessage(e.body);

  switch (code) {
    case 'resend_rate_limited':
      return 'Merci de patienter avant de redemander un code.';
    case 'feature_disabled':
      return 'La connexion par e-mail est désactivée sur ce serveur. Utilisez les autres options.';
    default:
      break;
  }

  if (parsed != null && parsed.isNotEmpty) return parsed;

  final net = _smsLoginNetworkUserMessage(e);
  if (net.isNotEmpty) return net;

  switch (e.statusCode) {
    case 503:
      return 'Connexion par e-mail indisponible sur ce serveur. Réessayez plus tard.';
    case 422:
      return 'Adresse e-mail invalide ou refusée par le serveur.';
    case 403:
      return 'Connexion refusée pour ce contexte (politique de sécurité). Réessayez plus tard.';
    case 408:
      return 'Le service est temporairement indisponible';
    default:
      if (e.statusCode >= 400 && e.statusCode < 500) {
        return 'L’envoi du code a échoué. Vérifiez l’adresse e-mail ou réessayez plus tard.';
      }
      if (e.statusCode >= 500) {
        return 'Le service est temporairement indisponible';
      }
      return 'Une erreur est survenue';
  }
}

/// Message utilisateur pour un échec de ``POST /auth/login/email-otp/verify``.
String loginEmailOtpVerifyFailureUserMessage(PasskeyApiException e) {
  const verify = true;
  final apiCode = parseFastApiErrorCode(e.body);
  final parsed = parseFastApiErrorMessage(e.body);

  switch (apiCode) {
    case 'security.account_locked':
      return 'Compte temporairement verrouillé pour raison de sécurité. Réessayez plus tard ou utilisez d’autres options de connexion.';
    case 'invalid_or_expired_code':
      return 'Code incorrect ou expiré.';
    case 'too_many_attempts':
      return 'Trop de tentatives avec ce code. Demandez un nouveau code par e-mail puis saisissez-le.';
    case 'resend_rate_limited':
      return 'Merci de patienter avant de redemander un code.';
    case 'feature_disabled':
      return 'La connexion par e-mail est désactivée sur ce serveur.';
    default:
      break;
  }

  if (parsed != null && parsed.isNotEmpty) return parsed;

  final net = _smsLoginNetworkUserMessage(e);
  if (net.isNotEmpty) return net;

  if (e.statusCode == 422) {
    return 'Saisie invalide. Entrez le code à 6 chiffres reçu par e-mail.';
  }

  return _httpStatusUserMessage(e.statusCode, isVerify: verify);
}

/// Client REST `/auth/passkeys/*` (FastAPI).
class PasskeyApi {
  PasskeyApi({http.Client? httpClient, String? debugBaseUrl})
      : _client = httpClient ?? http.Client(),
        _base = (debugBaseUrl != null && debugBaseUrl.trim().isNotEmpty)
            ? debugBaseUrl.trim()
            : SecureApiConfig.resolvedAuthApiBaseUrl.trim();

  final http.Client _client;
  final String _base;

  static const Duration _defaultTimeout = Duration(seconds: 22);

  bool get _hasBase => _base.isNotEmpty;

  Uri _u(String path) {
    final base = _base.replaceAll(RegExp(r'/$'), '');
    return Uri.parse('$base$path');
  }

  Map<String, String> _jsonHeaders(String? bearer) => {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        if (bearer != null && bearer.isNotEmpty) 'Authorization': 'Bearer $bearer',
      };

  String? _payloadForLog(Object? body) {
    if (body == null) return null;
    final s = body is String ? body : body.toString();
    if (s.length > 500) return '${s.substring(0, 500)}…';
    return s;
  }

  void _requireHttpSuccess(
    Uri uri,
    http.Response res, {
    String method = 'POST',
  }) {
    if (res.statusCode >= 200 && res.statusCode < 300) return;
    logAuthHttpFailure(
      operation: 'http_error',
      uri: uri,
      method: method,
      statusCode: res.statusCode,
      responseBody: res.body,
    );
    throw PasskeyApiException(res.statusCode, res.body);
  }

  Map<String, dynamic> _decodeJsonMap(http.Response res, Uri uri) {
    try {
      final decoded = jsonDecode(res.body);
      if (decoded is Map<String, dynamic>) return decoded;
    } catch (e, st) {
      logAuthHttpFailure(
        operation: 'json_decode',
        uri: uri,
        statusCode: res.statusCode,
        responseBody: res.body,
        error: e,
        stackTrace: st,
      );
      throw PasskeyApiException(502, res.body);
    }
    logAuthHttpFailure(
      operation: 'json_not_object',
      uri: uri,
      statusCode: res.statusCode,
      responseBody: res.body,
    );
    throw PasskeyApiException(502, res.body);
  }

  List<Map<String, dynamic>> _decodeJsonMapList(http.Response res, Uri uri) {
    try {
      final decoded = jsonDecode(res.body);
      if (decoded is List) {
        return decoded.cast<Map<String, dynamic>>();
      }
    } catch (e, st) {
      logAuthHttpFailure(
        operation: 'json_decode_list',
        uri: uri,
        statusCode: res.statusCode,
        responseBody: res.body,
        error: e,
        stackTrace: st,
      );
      throw PasskeyApiException(502, res.body);
    }
    logAuthHttpFailure(
      operation: 'json_not_list',
      uri: uri,
      statusCode: res.statusCode,
      responseBody: res.body,
    );
    throw PasskeyApiException(502, res.body);
  }

  Never _mapTransportError(
    Object e,
    StackTrace st,
    Uri url,
    String method,
    String? payload,
  ) {
    if (e is TimeoutException) {
      logAuthHttpFailure(
        operation: 'timeout',
        uri: url,
        method: method,
        requestPayload: payload,
        error: e,
        stackTrace: st,
      );
      throw PasskeyApiException(408, 'timeout');
    }
    if (e is SocketException) {
      logAuthHttpFailure(
        operation: 'socket',
        uri: url,
        method: method,
        requestPayload: payload,
        error: e,
        stackTrace: st,
      );
      throw PasskeyApiException(0, _classifySocketError(e));
    }
    if (e is HandshakeException) {
      logAuthHttpFailure(
        operation: 'tls_handshake',
        uri: url,
        method: method,
        requestPayload: payload,
        error: e,
        stackTrace: st,
      );
      throw PasskeyApiException(0, _kNetServerUnreachable);
    }
    if (e is TlsException) {
      logAuthHttpFailure(
        operation: 'tls',
        uri: url,
        method: method,
        requestPayload: payload,
        error: e,
        stackTrace: st,
      );
      throw PasskeyApiException(0, _kNetServerUnreachable);
    }
    if (e is http.ClientException) {
      logAuthHttpFailure(
        operation: 'client',
        uri: url,
        method: method,
        requestPayload: payload,
        error: e,
        stackTrace: st,
      );
      throw PasskeyApiException(0, _classifyClientErrorMessage(e.message));
    }
    logAuthHttpFailure(
      operation: 'unexpected',
      uri: url,
      method: method,
      requestPayload: payload,
      error: e,
      stackTrace: st,
    );
    throw PasskeyApiException(0, _kInternal);
  }

  Future<http.Response> _post(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
    Duration? timeout,
  }) async {
    final d = timeout ?? _defaultTimeout;
    final payload = _payloadForLog(body);
    Future<http.Response> once() =>
        _client.post(url, headers: headers, body: body).timeout(d);
    try {
      return await once();
    } catch (e, st) {
      if (e is TimeoutException) {
        logAuthHttpFailure(
          operation: 'timeout_retry',
          uri: url,
          method: 'POST',
          requestPayload: payload,
          error: e,
          stackTrace: st,
        );
        try {
          await Future<void>.delayed(const Duration(milliseconds: 400));
          return await once();
        } catch (e2, st2) {
          _mapTransportError(e2, st2, url, 'POST', payload);
        }
      }
      _mapTransportError(e, st, url, 'POST', payload);
    }
  }

  Future<http.Response> _get(
    Uri url, {
    Map<String, String>? headers,
    Duration? timeout,
  }) async {
    final d = timeout ?? _defaultTimeout;
    Future<http.Response> once() => _client.get(url, headers: headers).timeout(d);
    try {
      return await once();
    } catch (e, st) {
      if (e is TimeoutException) {
        logAuthHttpFailure(
          operation: 'timeout_retry',
          uri: url,
          method: 'GET',
          error: e,
          stackTrace: st,
        );
        try {
          await Future<void>.delayed(const Duration(milliseconds: 400));
          return await once();
        } catch (e2, st2) {
          _mapTransportError(e2, st2, url, 'GET', null);
        }
      }
      _mapTransportError(e, st, url, 'GET', null);
    }
  }

  Future<Map<String, dynamic>> registerStart({
    required String accessToken,
    String? deviceLabel,
  }) async {
    if (!_hasBase) {
      throw PasskeyApiException(0, 'No auth backend');
    }
    final body = <String, dynamic>{};
    if (deviceLabel != null && deviceLabel.isNotEmpty) {
      body['device_label'] = deviceLabel;
    }
    final uri = _u('/auth/passkeys/register/start');
    final res = await _post(
      uri,
      headers: _jsonHeaders(accessToken),
      body: jsonEncode(body),
    );
    _requireHttpSuccess(uri, res);
    return _decodeJsonMap(res, uri);
  }

  Future<Map<String, dynamic>> registerFinish({
    required String accessToken,
    required String challengeToken,
    required Map<String, dynamic> credential,
    String? deviceLabel,
  }) async {
    if (!_hasBase) {
      throw PasskeyApiException(0, 'No auth backend');
    }
    final uri = _u('/auth/passkeys/register/finish');
    final res = await _post(
      uri,
      headers: _jsonHeaders(accessToken),
      body: jsonEncode({
        'challenge_token': challengeToken,
        'credential': credential,
        if (deviceLabel != null) 'device_label': deviceLabel,
      }),
    );
    _requireHttpSuccess(uri, res);
    return _decodeJsonMap(res, uri);
  }

  Future<Map<String, dynamic>> loginStart({required String email}) async {
    if (!_hasBase) {
      throw PasskeyApiException(0, 'No auth backend');
    }
    final uri = _u('/auth/passkeys/login/start');
    final res = await _post(
      uri,
      headers: _jsonHeaders(null),
      body: jsonEncode({'email': email}),
    );
    _requireHttpSuccess(uri, res);
    return _decodeJsonMap(res, uri);
  }

  Future<Map<String, dynamic>> loginFinish({
    required String challengeToken,
    required Map<String, dynamic> credential,
    required String deviceId,
    String? fingerprintHeader,
  }) async {
    if (!_hasBase) {
      throw PasskeyApiException(0, 'No auth backend');
    }
    final headers = _jsonHeaders(null);
    headers['X-Device-ID'] = deviceId;
    if (fingerprintHeader != null && fingerprintHeader.isNotEmpty) {
      headers['X-Device-Fingerprint'] = fingerprintHeader;
    }
    final uri = _u('/auth/passkeys/login/finish');
    final res = await _post(
      uri,
      headers: headers,
      body: jsonEncode({
        'challenge_token': challengeToken,
        'credential': credential,
      }),
    );
    _requireHttpSuccess(uri, res);
    return _decodeJsonMap(res, uri);
  }

  /// Connexion admin par code e-mail (même base que passkeys) — requiert ``AUTH_ADMIN_EMAIL_OTP_ENABLED``.
  /// En dev, le JSON peut contenir ``dev_code`` (si le serveur l’expose).
  Future<Map<String, dynamic>> adminEmailOtpStart({required String email}) async {
    if (!_hasBase) {
      throw PasskeyApiException(0, 'No auth backend');
    }
    final uri = _u('/auth/login/email-otp/start');
    final res = await _post(
      uri,
      headers: _jsonHeaders(null),
      body: jsonEncode({'email': email}),
    );
    _requireHttpSuccess(uri, res);
    return _decodeJsonMap(res, uri);
  }

  Future<Map<String, dynamic>> adminEmailOtpVerify({
    required String email,
    required String code,
    required String deviceId,
    String? fingerprintHeader,
  }) async {
    if (!_hasBase) {
      throw PasskeyApiException(0, 'No auth backend');
    }
    final headers = _jsonHeaders(null);
    headers['X-Device-ID'] = deviceId;
    if (fingerprintHeader != null && fingerprintHeader.isNotEmpty) {
      headers['X-Device-Fingerprint'] = fingerprintHeader;
    }
    final uri = _u('/auth/login/email-otp/verify');
    final res = await _post(
      uri,
      headers: headers,
      body: jsonEncode({'email': email, 'code': code.trim()}),
    );
    _requireHttpSuccess(uri, res);
    return _decodeJsonMap(res, uri);
  }

  /// Pré-décision Adaptive Auth — ``POST /auth/login/orchestrate``.
  Future<Map<String, dynamic>> adaptiveLoginOrchestrate({
    required String identifier,
    required String identifierType,
    String? deviceId,
    String? fingerprintHeader,
  }) async {
    if (!_hasBase) {
      throw PasskeyApiException(0, 'No auth backend');
    }
    final headers = _jsonHeaders(null);
    if (deviceId != null && deviceId.isNotEmpty) {
      headers['X-Device-ID'] = deviceId;
    }
    if (fingerprintHeader != null && fingerprintHeader.isNotEmpty) {
      headers['X-Device-Fingerprint'] = fingerprintHeader;
    }
    final uri = _u('/auth/login/orchestrate');
    final res = await _post(
      uri,
      headers: headers,
      body: jsonEncode({
        'identifier': identifier.trim(),
        'identifier_type': identifierType,
      }),
    );
    _requireHttpSuccess(uri, res);
    return _decodeJsonMap(res, uri);
  }

  /// OTP SMS connexion mobile — ``POST /auth/login/sms/start`` (alias : ``/auth/login/start``).
  Future<Map<String, dynamic>> mobileLoginStart({required String phone}) async {
    if (!_hasBase) {
      throw PasskeyApiException(0, 'No auth backend');
    }
    final uri = _u('/auth/login/sms/start');
    final res = await _post(
      uri,
      headers: _jsonHeaders(null),
      body: jsonEncode({'phone': phone.trim()}),
    );
    _requireHttpSuccess(uri, res);
    return _decodeJsonMap(res, uri);
  }

  Future<Map<String, dynamic>> mobileLoginVerify({
    required String phone,
    required String code,
    required String deviceId,
    String? fingerprintHeader,
  }) async {
    if (!_hasBase) {
      throw PasskeyApiException(0, 'No auth backend');
    }
    final headers = _jsonHeaders(null);
    headers['X-Device-ID'] = deviceId;
    if (fingerprintHeader != null && fingerprintHeader.isNotEmpty) {
      headers['X-Device-Fingerprint'] = fingerprintHeader;
    }
    final uri = _u('/auth/login/sms/verify');
    final res = await _post(
      uri,
      headers: headers,
      body: jsonEncode({'phone': phone.trim(), 'code': code.trim()}),
    );
    _requireHttpSuccess(uri, res);
    return _decodeJsonMap(res, uri);
  }

  /// Inscription mobile — ``POST /auth/signup/sms/start`` (numéro libre, sinon 403).
  Future<Map<String, dynamic>> signupSmsStart({required String phone}) async {
    if (!_hasBase) {
      throw PasskeyApiException(0, 'No auth backend');
    }
    final uri = _u('/auth/signup/sms/start');
    final res = await _post(
      uri,
      headers: _jsonHeaders(null),
      body: jsonEncode({'phone': phone.trim()}),
    );
    _requireHttpSuccess(uri, res);
    return _decodeJsonMap(res, uri);
  }

  Future<Map<String, dynamic>> signupSmsVerify({
    required String phone,
    required String code,
    required String deviceId,
    String? fingerprintHeader,
  }) async {
    if (!_hasBase) {
      throw PasskeyApiException(0, 'No auth backend');
    }
    final headers = _jsonHeaders(null);
    headers['X-Device-ID'] = deviceId;
    if (fingerprintHeader != null && fingerprintHeader.isNotEmpty) {
      headers['X-Device-Fingerprint'] = fingerprintHeader;
    }
    final uri = _u('/auth/signup/sms/verify');
    final res = await _post(
      uri,
      headers: headers,
      body: jsonEncode({'phone': phone.trim(), 'code': code.trim()}),
    );
    _requireHttpSuccess(uri, res);
    return _decodeJsonMap(res, uri);
  }

  Future<List<Map<String, dynamic>>> listPasskeys({required String accessToken}) async {
    if (!_hasBase) {
      throw PasskeyApiException(0, 'No auth backend');
    }
    final uri = _u('/auth/passkeys');
    final res = await _get(
      uri,
      headers: _jsonHeaders(accessToken),
    );
    _requireHttpSuccess(uri, res, method: 'GET');
    return _decodeJsonMapList(res, uri);
  }

  /// Télémétrie UX (prompt ouvert / annulé / échec) — best-effort, sans exception vers l’UI.
  Future<void> reportPrompt({
    required String event,
    String? email,
    String? detail,
  }) async {
    if (!_hasBase) return;
    try {
      String? domain;
      if (email != null && email.contains('@')) {
        domain = email.split('@').last.trim();
        if (domain.isEmpty) domain = null;
      }
      await _post(
        _u('/auth/passkeys/prompt'),
        headers: _jsonHeaders(null),
        body: jsonEncode({
          'event': event,
          if (domain != null) 'identifier_domain': domain,
          if (detail != null && detail.isNotEmpty) 'detail': detail.length > 200 ? detail.substring(0, 200) : detail,
        }),
        timeout: const Duration(seconds: 8),
      );
    } catch (_) {
      // Ne jamais bloquer le flux auth
    }
  }

  Future<void> revokePasskey({
    required String accessToken,
    required String credentialId,
  }) async {
    if (!_hasBase) {
      throw PasskeyApiException(0, 'No auth backend');
    }
    final uri = _u('/auth/passkeys/revoke');
    final res = await _post(
      uri,
      headers: _jsonHeaders(accessToken),
      body: jsonEncode({'credential_id': credentialId}),
    );
    if (res.statusCode == 204 || (res.statusCode >= 200 && res.statusCode < 300)) {
      return;
    }
    logAuthHttpFailure(
      operation: 'http_error',
      uri: uri,
      method: 'POST',
      statusCode: res.statusCode,
      responseBody: res.body,
    );
    throw PasskeyApiException(res.statusCode, res.body);
  }

  void close() => _client.close();
}
