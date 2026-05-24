import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../../../core/http_error_display.dart';
import '../../../core/secure_api_config.dart';
import '../../../core/session_bearer_http.dart';
import '../../security/passcode/data/device_id_service.dart';
import 'mobile_app_profile.dart';

class ContactEmailConfirmResult {
  const ContactEmailConfirmResult({
    required this.email,
    required this.status,
    this.confirmedAt,
  });

  final String email;
  final String status;
  final String? confirmedAt;

  factory ContactEmailConfirmResult.fromJson(Map<String, dynamic> json) {
    return ContactEmailConfirmResult(
      email: (json['email'] as String? ?? '').trim(),
      status: (json['status'] as String? ?? '').trim(),
      confirmedAt: json['confirmed_at'] as String?,
    );
  }
}

class MobileContactEmailApiException implements Exception {
  MobileContactEmailApiException(this.message, {this.statusCode});
  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

/// Changement d’e-mail : FastAPI direct (comme Privy / refresh), pas le BFF Next.
class MobileContactEmailApi {
  const MobileContactEmailApi();

  static Uri _uri(String pathSuffix) {
    if (!SecureApiConfig.hasAuthBackend) {
      throw MobileContactEmailApiException(
        'API d’authentification non configurée (AUTH_API_BASE_URL).',
      );
    }
    final base = SecureApiConfig.resolvedAuthApiBaseUrl.replaceAll(RegExp(r'/$'), '');
    return Uri.parse('$base/api/mobile/flutter/profile/contact-email/$pathSuffix');
  }

  Future<Map<String, String>> _headers({
    required Uri uri,
    required String debugTag,
  }) async {
    final headers = await SessionBearerHttp.jsonHeadersAppScoped(
      uri: uri,
      debugTag: debugTag,
      withJsonContentType: true,
    );
    final deviceId = await DeviceIdService.instance.getOrCreate();
    final fp = await DeviceIdService.instance.buildFingerprintHeaderJson();
    headers['X-Device-ID'] = deviceId;
    if (fp != null) {
      headers['X-Device-Fingerprint'] = fp;
    }
    return headers;
  }

  Future<MobileAppProfile> requestChange({required String email}) async {
    final uri = _uri('request');
    final headers = await _headers(
      uri: uri,
      debugTag: 'MobileContactEmailApi.requestChange',
    );
    final res = await http
        .post(
          uri,
          headers: headers,
          body: jsonEncode({'email': email.trim()}),
        )
        .timeout(const Duration(seconds: 15));
    return _parseProfileResponse(res);
  }

  Future<ContactEmailConfirmResult> confirmChange({
    required String email,
    required String privyAccessToken,
  }) async {
    final uri = _uri('confirm');
    final headers = await _headers(
      uri: uri,
      debugTag: 'MobileContactEmailApi.confirmChange',
    );
    final res = await http
        .post(
          uri,
          headers: headers,
          body: jsonEncode({
            'email': email.trim(),
            'privy_access_token': privyAccessToken.trim(),
          }),
        )
        .timeout(const Duration(seconds: 15));

    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw MobileContactEmailApiException(
        _errorMessage(res),
        statusCode: res.statusCode,
      );
    }
    final body = res.body;
    if (responseBodyLooksLikeNonJsonApi(body)) {
      throw MobileContactEmailApiException('Réponse serveur invalide.');
    }
    final json = jsonDecode(body) as Map<String, dynamic>;
    return ContactEmailConfirmResult.fromJson(json);
  }

  MobileAppProfile _parseProfileResponse(http.Response res) {
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw MobileContactEmailApiException(
        _errorMessage(res),
        statusCode: res.statusCode,
      );
    }
    final body = res.body;
    if (responseBodyLooksLikeNonJsonApi(body)) {
      throw MobileContactEmailApiException('Réponse serveur invalide.');
    }
    try {
      final json = jsonDecode(body) as Map<String, dynamic>;
      return MobileAppProfile.fromJson(json);
    } catch (e) {
      if (kDebugMode) {
        debugPrint('[MobileContactEmailApi] parse error: $e');
      }
      throw MobileContactEmailApiException('Réponse profil illisible.');
    }
  }

  String _errorMessage(http.Response res) {
    if (responseBodyLooksLikeNonJsonApi(res.body)) {
      if (res.statusCode == 404) {
        return 'Service indisponible. Vérifiez votre connexion et réessayez.';
      }
      return userFacingHttpErrorMessage(res.statusCode, res.body);
    }
    try {
      final json = jsonDecode(res.body);
      if (json is Map<String, dynamic>) {
        final detail = json['detail'];
        if (detail is String && detail.trim().isNotEmpty) {
          return _friendlyDetail(detail.trim());
        }
        if (detail is Map) {
          final msg = detail['message'];
          if (msg is String && msg.trim().isNotEmpty) {
            return msg.trim();
          }
        }
        if (detail is List && detail.isNotEmpty) {
          final first = detail.first;
          if (first is Map && first['msg'] is String) {
            return (first['msg'] as String).trim();
          }
        }
      }
    } catch (_) {}
    return userFacingHttpErrorMessage(res.statusCode, res.body);
  }

  String _friendlyDetail(String detail) {
    if (detail.contains('Person profile not found')) {
      return 'Profil client introuvable. Contactez le support si le problème persiste.';
    }
    return detail;
  }
}
