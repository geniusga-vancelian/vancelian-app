import 'dart:convert';

import 'package:http/http.dart' as http;

import '../features/security/passcode/data/device_id_service.dart';
import '../features/security/passcode/data/session_service.dart';
import 'config.dart';
import 'secure_api_config.dart';
import 'session_identity_context.dart';

class PersonCryptoWalletRow {
  PersonCryptoWalletRow({
    required this.id,
    required this.address,
    required this.chainType,
    this.chainId,
    required this.walletType,
    required this.provider,
    required this.isPrimary,
  });

  final String id;
  final String address;
  final String chainType;
  final int? chainId;
  final String walletType;
  final String provider;
  final bool isPrimary;

  static PersonCryptoWalletRow? parse(Map<String, dynamic>? j) {
    if (j == null) return null;
    final id = j['id'] as String?;
    final address = j['address'] as String?;
    final chainType = j['chain_type'] as String?;
    final walletType = j['wallet_type'] as String?;
    final provider = j['provider'] as String?;
    if (id == null ||
        address == null ||
        chainType == null ||
        walletType == null ||
        provider == null) {
      return null;
    }
    final cidRaw = j['chain_id'];
    int? cid;
    if (cidRaw is int) cid = cidRaw;
    final isPri = j['is_primary'];

    return PersonCryptoWalletRow(
      id: id,
      address: address.trim(),
      chainType: chainType.trim(),
      chainId: cid,
      walletType: walletType.trim(),
      provider: provider.trim(),
      isPrimary: isPri == true,
    );
  }
}

/// Réponse parsée de `POST /auth/privy/exchange`.
class PrivyExchangeResult {
  PrivyExchangeResult({
    required this.accessToken,
    this.refreshToken,
    required this.personId,
    required this.peClientId,
    required this.wallets,
  });

  final String accessToken;
  final String? refreshToken;
  final String personId;
  final String peClientId;
  final List<Map<String, dynamic>> wallets;
}

/// Réponse `POST /auth/privy/dev-link` ou `POST /auth/privy/link` (même forme `{ ok, idempotent }`).
class PrivyDevLinkResult {
  PrivyDevLinkResult({required this.ok, this.idempotent = false});

  final bool ok;
  final bool idempotent;
}

/// Réponse `GET /auth/privy/dev-current-person`.
class PrivyDevCurrentPersonResult {
  PrivyDevCurrentPersonResult({
    required this.personId,
    this.peClientId,
    required this.jwtSubject,
  });

  final String personId;
  final String? peClientId;
  final String jwtSubject;
}

/// Erreur API stable (`detail.code` FastAPI ou `error.code` JSON).
class PrivyExchangeException implements Exception {
  PrivyExchangeException(this.statusCode, this.code, this.message);

  final int statusCode;
  final String code;
  final String message;

  @override
  String toString() => 'PrivyExchangeException($statusCode, $code, $message)';
}

/// Couche **Privy → session Vancelian** (HTTP vers `/auth/privy/*` sur [SecureApiConfig]).
class PrivyIdentityBridgeService {
  PrivyIdentityBridgeService._();
  static final PrivyIdentityBridgeService instance = PrivyIdentityBridgeService._();

  static const Duration _httpTimeout = Duration(seconds: 12);

  static String get _baseAuth {
    return SecureApiConfig.resolvedAuthApiBaseUrl.replaceAll(RegExp(r'/$'), '');
  }

  /// URL `POST /auth/privy/exchange`.
  static String get privyExchangeUrl => '$_baseAuth/auth/privy/exchange';

  /// URL `POST /auth/signup/privy/exchange` (création compte).
  static String get privySignupExchangeUrl => '$_baseAuth/auth/signup/privy/exchange';

  static String get privyDevLinkUrl => '$_baseAuth/auth/privy/dev-link';

  static String get privyDevCurrentPersonUrl => '$_baseAuth/auth/privy/dev-current-person';

  /// `POST /auth/privy/link` — liaison Privy sous **JWT Vancelian** (claim `person_id`).
  static String get privyAuthenticatedLinkUrl => '$_baseAuth/auth/privy/link';

  /// `GET /auth/privy/person-wallets` — wallets non custodial actifs pour le JWT courant.
  static String get privyPersonWalletsUrl => '$_baseAuth/auth/privy/person-wallets';

  /// URL catalogue côté BFF (profil, home) — inchangée ; rappel pour orchestrations futures.
  static String get mobileBootstrapPath => '${Config.apiBaseUrl}/api/mobile/flutter/bootstrap';

  Future<void> applyVancelianTokens({
    required String accessToken,
    String? refreshToken,
  }) async {
    await SessionService.instance.storeTokens(
      accessToken: accessToken,
      refreshToken: refreshToken,
    );
  }

  void hydrateContextFromAccessToken(String accessToken) {
    SessionIdentityContext.instance.syncFromAccessToken(accessToken);
  }

  Future<Map<String, String>> _deviceHeaders({String? bearer}) async {
    final deviceId = await DeviceIdService.instance.getOrCreate();
    final fp = await DeviceIdService.instance.buildFingerprintHeaderJson();
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-Device-ID': deviceId,
    };
    if (fp != null) {
      headers['X-Device-Fingerprint'] = fp;
    }
    final b = bearer?.trim();
    if (b != null && b.isNotEmpty) {
      headers['Authorization'] = 'Bearer $b';
    }
    return headers;
  }

  /// [dev] Lie `privy_user_id` à une `person_id` existante (sans SQL manuel).
  Future<PrivyDevLinkResult> devLinkPrivyToPerson({
    required String personId,
    required String privyUserId,
    String? email,
  }) async {
    if (!SecureApiConfig.hasAuthBackend) {
      throw PrivyExchangeException(
        0,
        'privy.exchange.no_auth_backend',
        'AUTH_API_BASE_URL / resolvedAuthApiBaseUrl vide.',
      );
    }
    final headers = await _deviceHeaders();
    final uri = Uri.parse(privyDevLinkUrl);
    final body = <String, dynamic>{
      'person_id': personId.trim(),
      'privy_user_id': privyUserId.trim(),
      if (email != null && email.trim().isNotEmpty) 'email': email.trim(),
    };
    http.Response res;
    try {
      res = await http
          .post(uri, headers: headers, body: jsonEncode(body))
          .timeout(_httpTimeout);
    } catch (e) {
      throw PrivyExchangeException(
        0,
        'privy.dev_link.network_error',
        e.toString(),
      );
    }
    if (res.statusCode < 200 || res.statusCode >= 300) {
      final code = parseErrorCode(res.body) ?? 'privy.dev_link.http_error';
      final message = parseErrorMessage(res.body) ?? res.body;
      throw PrivyExchangeException(res.statusCode, code, message);
    }
    final map = jsonDecode(res.body) as Map<String, dynamic>;
    return PrivyDevLinkResult(
      ok: map['ok'] == true,
      idempotent: map['idempotent'] == true,
    );
  }

  /// Lie `privy_user_id` au `person_id` dérivé du **JWT stocké** (Bearer + headers device).
  Future<PrivyDevLinkResult> linkPrivyForAuthenticatedSession({
    required String privyUserId,
    String? email,
  }) async {
    if (!SecureApiConfig.hasAuthBackend) {
      throw PrivyExchangeException(
        0,
        'privy.exchange.no_auth_backend',
        'AUTH_API_BASE_URL / resolvedAuthApiBaseUrl vide.',
      );
    }
    final jwt = await SessionService.instance.readAccessToken();
    if (jwt == null || jwt.isEmpty) {
      throw PrivyExchangeException(
        401,
        'privy.link_requires_session',
        'Aucun JWT Vancelian — se connecter au préalable.',
      );
    }
    final headers = await _deviceHeaders(bearer: jwt);
    final uri = Uri.parse(privyAuthenticatedLinkUrl);
    final body = <String, dynamic>{
      'privy_user_id': privyUserId.trim(),
      if (email != null && email.trim().isNotEmpty) 'email': email.trim(),
    };
    http.Response res;
    try {
      res = await http
          .post(uri, headers: headers, body: jsonEncode(body))
          .timeout(_httpTimeout);
    } catch (e) {
      throw PrivyExchangeException(
        0,
        'privy.link.network_error',
        e.toString(),
      );
    }
    if (res.statusCode < 200 || res.statusCode >= 300) {
      final code = parseErrorCode(res.body) ?? 'privy.link.http_error';
      final message = parseErrorMessage(res.body) ?? res.body;
      throw PrivyExchangeException(res.statusCode, code, message);
    }
    final map = jsonDecode(res.body) as Map<String, dynamic>;
    return PrivyDevLinkResult(
      ok: map['ok'] == true,
      idempotent: map['idempotent'] == true,
    );
  }

  /// [dev] `person_id` / `pe_client_id` depuis le JWT Vancelian courant (Bearer requis).
  Future<PrivyDevCurrentPersonResult> devCurrentPerson() async {
    if (!SecureApiConfig.hasAuthBackend) {
      throw PrivyExchangeException(
        0,
        'privy.exchange.no_auth_backend',
        'AUTH_API_BASE_URL / resolvedAuthApiBaseUrl vide.',
      );
    }
    final jwt = await SessionService.instance.readAccessToken();
    if (jwt == null || jwt.isEmpty) {
      throw PrivyExchangeException(
        401,
        'privy.dev_current_person_requires_session',
        'Aucun JWT Vancelian stocké — se connecter au préalable ou coller person_id.',
      );
    }
    final headers = await _deviceHeaders(bearer: jwt);
    final uri = Uri.parse(privyDevCurrentPersonUrl);
    http.Response res;
    try {
      res = await http.get(uri, headers: headers).timeout(_httpTimeout);
    } catch (e) {
      throw PrivyExchangeException(
        0,
        'privy.dev_current_person.network_error',
        e.toString(),
      );
    }
    if (res.statusCode < 200 || res.statusCode >= 300) {
      final code = parseErrorCode(res.body) ?? 'privy.dev_current_person.http_error';
      final message = parseErrorMessage(res.body) ?? res.body;
      throw PrivyExchangeException(res.statusCode, code, message);
    }
    final map = jsonDecode(res.body) as Map<String, dynamic>;
    return PrivyDevCurrentPersonResult(
      personId: map['person_id'] as String? ?? '',
      peClientId: map['pe_client_id'] as String?,
      jwtSubject: map['jwt_subject'] as String? ?? '',
    );
  }

  /// Wallets `person_crypto_wallets` actifs (Bearer + device headers).
  Future<List<PersonCryptoWalletRow>> fetchAuthenticatedPersonCryptoWallets() async {
    if (!SecureApiConfig.hasAuthBackend) {
      throw PrivyExchangeException(
        0,
        'privy.exchange.no_auth_backend',
        'AUTH_API_BASE_URL / resolvedAuthApiBaseUrl vide.',
      );
    }
    final jwt = await SessionService.instance.readAccessToken();
    if (jwt == null || jwt.isEmpty) {
      throw PrivyExchangeException(
        401,
        'privy.person_wallets_requires_session',
        'Aucun JWT Vancelian — se connecter au préalable.',
      );
    }
    final headers = await _deviceHeaders(bearer: jwt);
    final uri = Uri.parse(privyPersonWalletsUrl);
    http.Response res;
    try {
      res = await http.get(uri, headers: headers).timeout(_httpTimeout);
    } catch (e) {
      throw PrivyExchangeException(
        0,
        'privy.person_wallets.network_error',
        e.toString(),
      );
    }
    if (res.statusCode < 200 || res.statusCode >= 300) {
      final code = parseErrorCode(res.body) ?? 'privy.person_wallets.http_error';
      String message = parseErrorMessage(res.body) ?? res.body;
      if (res.statusCode == 404) {
        final norm = message.trim().toLowerCase();
        final looksLikeMissingRoute = norm == 'not found' ||
            (code == 'privy.person_wallets.http_error' && norm.length <= 40);
        if (looksLikeMissingRoute) {
          message =
              'Route introuvable sur ${privyPersonWalletsUrl.split('/auth').first} — '
              'AUTH_API_BASE_URL doit pointer vers FastAPI (:8000), pas le serveur '
              'Next.js/BFF uniquement (:3000), et le conteneur API doit contenir '
              'le code avec GET /auth/privy/person-wallets (rebuild après git pull).';
        }
      }
      throw PrivyExchangeException(res.statusCode, code, message);
    }
    final map = jsonDecode(res.body) as Map<String, dynamic>;
    final raw = map['wallets'];
    final out = <PersonCryptoWalletRow>[];
    if (raw is List) {
      for (final w in raw) {
        if (w is Map<String, dynamic>) {
          final row = PersonCryptoWalletRow.parse(w);
          if (row != null) out.add(row);
        }
      }
    }
    return out;
  }

  /// Inscription : échange Privy → nouveau compte + session JWT (`acct_st=PARTIAL`).
  Future<PrivyExchangeResult> exchangeSignupPrivyToken({
    required String privyAccessToken,
    String? emailForStubDev,
    List<Map<String, dynamic>>? wallets,
  }) async {
    if (!SecureApiConfig.hasAuthBackend) {
      throw PrivyExchangeException(
        0,
        'privy.signup.no_auth_backend',
        'AUTH_API_BASE_URL / resolvedAuthApiBaseUrl vide.',
      );
    }
    final headers = await _deviceHeaders();
    final body = <String, dynamic>{
      'privy_access_token': privyAccessToken,
    };
    final stubEmail = emailForStubDev?.trim();
    if (stubEmail != null && stubEmail.isNotEmpty) {
      body['email'] = stubEmail;
    }
    if (wallets != null && wallets.isNotEmpty) {
      body['wallets'] = wallets;
    }
    final uri = Uri.parse(privySignupExchangeUrl);
    http.Response res;
    try {
      res = await http
          .post(uri, headers: headers, body: jsonEncode(body))
          .timeout(_httpTimeout);
    } catch (e) {
      throw PrivyExchangeException(
        0,
        'privy.signup.network_error',
        e.toString(),
      );
    }
    if (res.statusCode < 200 || res.statusCode >= 300) {
      final code = parseErrorCode(res.body) ?? 'privy.signup.http_error';
      final message = parseErrorMessage(res.body) ?? res.body;
      throw PrivyExchangeException(res.statusCode, code, message);
    }
    return _parseExchangeResponse(res);
  }

  /// Échange le jeton Privy contre une session JWT Vancelian (`sub=au:…`).
  Future<PrivyExchangeResult> exchangePrivyToken({
    required String privyAccessToken,
    String? emailForStubDev,
    List<Map<String, dynamic>>? wallets,
  }) async {
    if (!SecureApiConfig.hasAuthBackend) {
      throw PrivyExchangeException(
        0,
        'privy.exchange.no_auth_backend',
        'AUTH_API_BASE_URL / resolvedAuthApiBaseUrl vide.',
      );
    }
    final headers = await _deviceHeaders();
    final body = <String, dynamic>{
      'privy_access_token': privyAccessToken,
    };
    final stubEmail = emailForStubDev?.trim();
    if (stubEmail != null && stubEmail.isNotEmpty) {
      body['email'] = stubEmail;
    }
    if (wallets != null && wallets.isNotEmpty) {
      body['wallets'] = wallets;
    }
    final uri = Uri.parse(privyExchangeUrl);
    http.Response res;
    try {
      res = await http
          .post(uri, headers: headers, body: jsonEncode(body))
          .timeout(_httpTimeout);
    } catch (e) {
      throw PrivyExchangeException(
        0,
        'privy.exchange.network_error',
        e.toString(),
      );
    }
    if (res.statusCode < 200 || res.statusCode >= 300) {
      final code = parseErrorCode(res.body) ?? 'privy.exchange.http_error';
      final message = parseErrorMessage(res.body) ?? res.body;
      throw PrivyExchangeException(res.statusCode, code, message);
    }
    return _parseExchangeResponse(res);
  }

  Future<PrivyExchangeResult> _parseExchangeResponse(http.Response res) async {
    Map<String, dynamic> map;
    try {
      map = jsonDecode(res.body) as Map<String, dynamic>;
    } catch (e) {
      throw PrivyExchangeException(
        res.statusCode,
        'privy.exchange.invalid_json',
        e.toString(),
      );
    }
    final access = map['access_token'] as String?;
    if (access == null || access.isEmpty) {
      throw PrivyExchangeException(
        res.statusCode,
        'privy.exchange.missing_access_token',
        'Réponse sans access_token.',
      );
    }
    final refresh = map['refresh_token'] as String?;
    final personId = map['person_id'] as String? ?? '';
    final peClientId = map['pe_client_id'] as String? ?? '';
    final wl = map['wallets'];
    final walletsOut = <Map<String, dynamic>>[];
    if (wl is List) {
      for (final w in wl) {
        if (w is Map<String, dynamic>) {
          walletsOut.add(w);
        }
      }
    }
    await SessionService.instance.storeTokens(
      accessToken: access,
      refreshToken: refresh,
    );
    return PrivyExchangeResult(
      accessToken: access,
      refreshToken: refresh,
      personId: personId,
      peClientId: peClientId,
      wallets: walletsOut,
    );
  }

  static String? parseErrorCode(String body) {
    try {
      final dynamic root = jsonDecode(body);
      if (root is! Map<String, dynamic>) return null;
      final d = root['detail'];
      if (d is Map<String, dynamic> && d['code'] is String) {
        return d['code'] as String;
      }
      final err = root['error'];
      if (err is Map<String, dynamic> && err['code'] is String) {
        return err['code'] as String;
      }
    } catch (_) {}
    return null;
  }

  static String? parseErrorMessage(String body) {
    try {
      final dynamic root = jsonDecode(body);
      if (root is! Map<String, dynamic>) return null;
      final d = root['detail'];
      if (d is Map<String, dynamic> && d['message'] is String) {
        return d['message'] as String;
      }
      if (d is String) {
        return d;
      }
      final err = root['error'];
      if (err is Map<String, dynamic> && err['message'] is String) {
        return err['message'] as String;
      }
    } catch (_) {}
    return null;
  }
}
