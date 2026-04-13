import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';

import 'package:arquantix_news/features/security/local_access/session_security_snapshot.dart';

void main() {
  test('JWT payload parse strust lstup relock bio_req', () {
    // Minimal fake JWT: header.payload.sig (payload only decoded by fromAccessTokenClaims)
    const payload = {
      'sub': 'a@b.c',
      'dtrust': 'HIGH',
      'auth_str': 'passkey',
      'strust': 'HIGH',
      'lstup': 1700000000,
      'relock': true,
      'bio_req': true,
    };
    final b64 = base64Url.encode(utf8.encode(jsonEncode(payload)));
    final token = 'x.$b64.y';
    final s = SessionSecuritySnapshot.fromAccessTokenClaims(token);
    expect(s.sessionTrustLevel, 'HIGH');
    expect(s.lastStepUpAtEpochSec, 1700000000);
    expect(s.jwtRelockRequired, true);
    expect(s.jwtBiometricHint, true);
    final enc = jsonEncode(s.toPersistedClaimsJson());
    final s2 = SessionSecuritySnapshot.fromPersistedClaimsJson(enc);
    expect(s2.sessionTrustLevel, 'HIGH');
    expect(s2.lastStepUpAtEpochSec, 1700000000);
  });
}
