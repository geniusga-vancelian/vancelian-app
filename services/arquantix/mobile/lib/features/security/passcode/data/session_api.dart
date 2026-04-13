import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../../core/secure_api_config.dart';
import '../../device_attestation/data/device_attestation_service.dart';
import '../../device_signing/data/device_signing_service.dart';
import 'device_id_service.dart';
import 'session_service.dart';

class SessionRefreshResult {
  SessionRefreshResult({
    required this.ok,
    this.accessToken,
    this.refreshToken,
    this.statusCode,
  });

  final bool ok;
  final String? accessToken;
  final String? refreshToken;
  final int? statusCode;
}

/// Client minimal pour `/auth/refresh` et `/auth/revoke` (FastAPI).
class SessionApi {
  /// Plafond explicite : sans cela, un backend injoignable peut bloquer le client HTTP
  /// pendant des dizaines de secondes (cold start / bootstrap perçu comme figé).
  static const Duration _httpTimeout = Duration(seconds: 8);

  Uri _uri(String path) {
    final base = SecureApiConfig.resolvedAuthApiBaseUrl.replaceAll(RegExp(r'/$'), '');
    return Uri.parse('$base$path');
  }

  /// [attestationServerNonce] : nonce renvoyé par `POST /auth/attestation/challenge` si attestation activée.
  Future<SessionRefreshResult> refresh({
    required String refreshToken,
    String? attestationServerNonce,
  }) async {
    if (!SecureApiConfig.hasAuthBackend) {
      return SessionRefreshResult(ok: false);
    }
    try {
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
      if (attestationServerNonce != null && attestationServerNonce.isNotEmpty) {
        final attest = await DeviceAttestationService.instance
            .buildHeaderValue(serverNonce: attestationServerNonce);
        if (attest != null && attest.isNotEmpty) {
          headers['X-Device-Attestation'] = attest;
        }
      }
      if (DeviceSigningService.enabled) {
        final sig = await DeviceSigningService.instance
            .buildRefreshSignatureHeaders(refreshToken);
        headers.addAll(sig);
      }
      final res = await http
          .post(
            _uri('/auth/refresh'),
            headers: headers,
            body: jsonEncode({'refresh_token': refreshToken}),
          )
          .timeout(_httpTimeout);
      if (res.statusCode < 200 || res.statusCode >= 300) {
        return SessionRefreshResult(ok: false, statusCode: res.statusCode);
      }
      final map = jsonDecode(res.body) as Map<String, dynamic>;
      final at = map['access_token'] as String?;
      final rt = map['refresh_token'] as String?;
      return SessionRefreshResult(
        ok: at != null && at.isNotEmpty,
        accessToken: at,
        refreshToken: rt,
        statusCode: res.statusCode,
      );
    } catch (_) {
      return SessionRefreshResult(ok: false);
    }
  }

  Future<void> revoke({required String refreshToken}) async {
    if (!SecureApiConfig.hasAuthBackend) return;
    try {
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
      await http
          .post(
            _uri('/auth/revoke'),
            headers: headers,
            body: jsonEncode({'refresh_token': refreshToken}),
          )
          .timeout(_httpTimeout);
    } catch (_) {
      /* idempotent côté UX */
    }
  }

  /// ACK serveur après configuration réussie du PIN local ([PasscodeSetupScreen]).
  ///
  /// Sans corps ; idempotent côté backend. Jusqu’à **3** tentatives (immédiat + 2 pauses courtes)
  /// en cas d’échec transitoire ; pas de retry si 401/403. Aucune erreur ne remonte — le flux PIN
  /// continue dans tous les cas.
  static const int _ackPasscodeMaxAttempts = 3;
  static const Duration _ackPasscodeAttemptTimeout = Duration(seconds: 8);
  static const List<int> _ackPasscodeBackoffMsBeforeRetry = [350, 700];

  Future<void> ackLocalPasscodeRegistered({required String accessToken}) async {
    if (!SecureApiConfig.hasAuthBackend) return;
    if (accessToken.isEmpty) return;

    Map<String, String>? headers;
    try {
      final deviceId = await DeviceIdService.instance.getOrCreate();
      final fp = await DeviceIdService.instance.buildFingerprintHeaderJson();
      headers = <String, String>{
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Bearer $accessToken',
        'X-Device-ID': deviceId,
      };
      if (fp != null) {
        headers['X-Device-Fingerprint'] = fp;
      }
    } catch (_) {
      return;
    }

    for (var attempt = 0; attempt < _ackPasscodeMaxAttempts; attempt++) {
      if (attempt > 0) {
        await Future<void>.delayed(
          Duration(milliseconds: _ackPasscodeBackoffMsBeforeRetry[attempt - 1]),
        );
      }
      try {
        final res = await http
            .post(
              _uri('/auth/security/local-passcode-ack'),
              headers: headers,
            )
            .timeout(_ackPasscodeAttemptTimeout);
        final code = res.statusCode;
        if (code >= 200 && code < 300) {
          try {
            final map = jsonDecode(res.body) as Map<String, dynamic>;
            final at = map['access_token'] as String?;
            final rt = map['refresh_token'] as String?;
            if (at != null && at.isNotEmpty) {
              await SessionService.instance.storeTokens(
                accessToken: at,
                refreshToken: rt,
              );
            }
          } catch (_) {
            /* JSON ou stockage — ACK déjà accepté côté serveur */
          }
          return;
        }
        if (code == 401 || code == 403) {
          return;
        }
      } catch (_) {
        /* tentative suivante ou abandon silencieux */
      }
    }
  }
}
