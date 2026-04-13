import 'dart:convert';

import 'package:http/http.dart' as http;

/// Canal 2FA aligné sur l’API backend.
enum TwoFactorChannel { sms, email, totp }

/// Réponse standardisée pour start / verify.
class TwoFactorApiResult<T> {
  const TwoFactorApiResult({
    this.data,
    required this.statusCode,
    this.errorCode,
    this.errorMessage,
  });

  final T? data;
  final int statusCode;
  final String? errorCode;
  final String? errorMessage;

  bool get isSuccess => statusCode >= 200 && statusCode < 300;
}

/// Messages FR alignés sur les `detail.code` renvoyés par l’API (contrat stable).
String twoFactorUserMessage({
  required int statusCode,
  String? errorCode,
  String? serverMessage,
}) {
  if (statusCode == 0) {
    return 'Connexion impossible. Vérifiez le réseau et réessayez.';
  }
  switch (errorCode) {
    case 'invalid_code':
      return serverMessage ?? 'Code incorrect.';
    case 'challenge_expired':
      return serverMessage ?? 'Ce code a expiré. Demandez-en un nouveau.';
    case 'too_many_attempts':
    case 'challenge_not_verifiable':
      return serverMessage ?? 'Trop de tentatives. Demandez un nouveau code.';
    case 'verify_rate_limited':
      return serverMessage ?? 'Trop de tentatives. Réessayez plus tard.';
    case 'resend_rate_limited':
    case 'start_quota_exceeded':
    case 'target_rate_limited':
    case 'ip_rate_limited':
      return serverMessage ?? 'Veuillez patienter avant une nouvelle demande.';
    case 'provider_unavailable':
    case 'channel_not_available':
      return serverMessage ?? 'L’envoi du code est temporairement indisponible.';
    case 'challenge_superseded':
      return serverMessage ?? 'Ce code a été remplacé. Utilisez le dernier SMS ou renvoyez un code.';
    case 'challenge_not_found':
      return serverMessage ?? 'Cette vérification n’est plus valide.';
    case 'unauthorized_2fa_request':
      return serverMessage ?? 'Impossible de poursuivre cette vérification.';
    case 'purpose_not_allowed':
    case 'invalid_purpose':
      return serverMessage ?? 'Type de vérification non pris en charge.';
    default:
      if (serverMessage != null && serverMessage.isNotEmpty) {
        return serverMessage;
      }
      return 'Une erreur est survenue (${statusCode}).';
  }
}

/// Données renvoyées par `POST /api/2fa/start`.
class TwoFactorStartData {
  TwoFactorStartData({
    required this.challengeId,
    required this.expiresAt,
    required this.maskedTarget,
    required this.channel,
    required this.purpose,
    required this.resendAfterSeconds,
    this.otpauthUrl,
  });

  final String challengeId;
  final String expiresAt;
  final String? maskedTarget;
  final String channel;
  final String purpose;
  final int resendAfterSeconds;
  final String? otpauthUrl;

  factory TwoFactorStartData.fromJson(Map<String, dynamic> j) {
    return TwoFactorStartData(
      challengeId: j['challenge_id'] as String,
      expiresAt: j['expires_at'] as String,
      maskedTarget: j['masked_target'] as String?,
      channel: j['channel'] as String,
      purpose: j['purpose'] as String,
      resendAfterSeconds: (j['resend_after_seconds'] as num?)?.toInt() ?? 30,
      otpauthUrl: j['otpauth_url'] as String?,
    );
  }
}

/// Client HTTP pour `/api/2fa/*` (Bearer JWT).
class TwoFactorApi {
  TwoFactorApi({
    required this.startUrl,
    required this.verifyUrl,
    this.accessToken,
  });

  final String startUrl;
  final String verifyUrl;
  final String? accessToken;

  Map<String, String> _headers() {
    final h = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    final t = accessToken;
    if (t != null && t.isNotEmpty) {
      h['Authorization'] = t.startsWith('Bearer ') ? t : 'Bearer $t';
    }
    return h;
  }

  /// `personId` : uniquement si le backend a `TWO_FACTOR_REQUIRE_AUTH=false` (dev/tests).
  Future<TwoFactorApiResult<TwoFactorStartData>> start({
    required TwoFactorChannel channel,
    required String purpose,
    String? target,
    String? personId,
  }) async {
    final body = <String, dynamic>{
      'channel': channel.name,
      'purpose': purpose,
    };
    if (target != null && target.isNotEmpty) body['target'] = target;
    if (personId != null && personId.isNotEmpty) {
      body['person_id'] = personId;
    }
    try {
      final resp = await http.post(
        Uri.parse(startUrl),
        headers: _headers(),
        body: jsonEncode(body),
      );
      return _parseStart(resp);
    } catch (e) {
      return TwoFactorApiResult(
        statusCode: 0,
        errorCode: 'network',
        errorMessage: '$e',
      );
    }
  }

  Future<TwoFactorApiResult<void>> verify({
    required String challengeId,
    required String code,
    String? personId,
  }) async {
    final body = <String, dynamic>{
      'challenge_id': challengeId,
      'code': code,
    };
    if (personId != null && personId.isNotEmpty) {
      body['person_id'] = personId;
    }
    try {
      final resp = await http.post(
        Uri.parse(verifyUrl),
        headers: _headers(),
        body: jsonEncode(body),
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return const TwoFactorApiResult(statusCode: 200, data: null);
      }
      final err = _parseError(resp);
      return TwoFactorApiResult(
        statusCode: resp.statusCode,
        errorCode: err.$1,
        errorMessage: err.$2,
      );
    } catch (e) {
      return TwoFactorApiResult(
        statusCode: 0,
        errorCode: 'network',
        errorMessage: '$e',
      );
    }
  }

  TwoFactorApiResult<TwoFactorStartData> _parseStart(http.Response resp) {
    if (resp.statusCode >= 200 && resp.statusCode < 300) {
      final j = jsonDecode(resp.body) as Map<String, dynamic>;
      return TwoFactorApiResult(
        statusCode: resp.statusCode,
        data: TwoFactorStartData.fromJson(j),
      );
    }
    final err = _parseError(resp);
    return TwoFactorApiResult(
      statusCode: resp.statusCode,
      errorCode: err.$1,
      errorMessage: err.$2,
    );
  }

  /// Extrait `(code, message)` depuis le corps FastAPI (`detail` string ou map).
  (String?, String) _parseError(http.Response resp) {
    try {
      final data = jsonDecode(resp.body) as Map<String, dynamic>;
      final detail = data['detail'];
      if (detail is Map<String, dynamic>) {
        final c = detail['code'] as String?;
        final m = detail['message'] as String? ?? 'Request failed';
        return (c, m);
      }
      if (detail is String) {
        return (null, detail);
      }
    } catch (_) {}
    return (null, 'Server error (${resp.statusCode})');
  }
}
