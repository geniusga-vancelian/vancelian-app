import 'dart:convert';

import 'package:flutter/foundation.dart';

/// En-tête `X-Device-Attestation` (JSON ou base64url JSON) pour `/auth/login` et `/auth/refresh`.
///
/// Tier 1 : points d’extension iOS (App Attest) et Android (Play Integrity).
/// Brancher les packages natifs (`app_attest`, `play_integrity` ou équivalent) dans
/// [IosAppAttestProvider] / [AndroidPlayIntegrityProvider].
abstract class DeviceAttestationProvider {
  /// Retourne le corps JSON attendu par le backend (clés `format`, `nonce`, etc.).
  Future<Map<String, dynamic>?> buildAttestationPayload({required String serverNonce});
}

/// Stub par défaut (aucun en-tête).
class NoOpDeviceAttestationProvider implements DeviceAttestationProvider {
  @override
  Future<Map<String, dynamic>?> buildAttestationPayload({required String serverNonce}) async => null;
}

/// iOS — à connecter à DCAppAttest / DeviceCheck (voir rapport Tier 1).
class IosAppAttestProvider implements DeviceAttestationProvider {
  @override
  Future<Map<String, dynamic>?> buildAttestationPayload({required String serverNonce}) async {
    debugPrint('IosAppAttestProvider: intégrer App Attest + assertion signée (nonce=$serverNonce)');
    return null;
  }
}

/// Android — à connecter à Play Integrity API (voir rapport Tier 1).
class AndroidPlayIntegrityProvider implements DeviceAttestationProvider {
  @override
  Future<Map<String, dynamic>?> buildAttestationPayload({required String serverNonce}) async {
    debugPrint('AndroidPlayIntegrityProvider: intégrer Play Integrity (nonce=$serverNonce)');
    return null;
  }
}

class DeviceAttestationService {
  DeviceAttestationService._();

  static final DeviceAttestationService instance = DeviceAttestationService._();

  DeviceAttestationProvider provider = NoOpDeviceAttestationProvider();

  /// Sérialise pour l’en-tête HTTP (JSON UTF-8 ; le backend accepte aussi la forme base64url).
  Future<String?> buildHeaderValue({required String serverNonce}) async {
    final payload = await provider.buildAttestationPayload(serverNonce: serverNonce);
    if (payload == null) return null;
    return jsonEncode(payload);
  }
}
