import 'dart:convert' show base64Url, json, utf8;

import 'package:arquantix_news/features/security/local_access/session_security_snapshot.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('fromAccessTokenClaims lit step_up_otp, dtrust, auth_str', () {
    final payload = base64Url.encode(
      utf8.encode(
        json.encode({
          'sub': 'u1',
          'step_up_otp': true,
          'dtrust': 'new_device',
          'auth_str': 'otp',
        }),
      ),
    );
    final token = 'x.$payload.y';
    final s = SessionSecuritySnapshot.fromAccessTokenClaims(token);
    expect(s.stepUpOtpRequired, isTrue);
    expect(s.trustLevel, 'new_device');
    expect(s.lastAuthStrength, 'otp');
    expect(s.isElevatedLocalRisk, isTrue);
  });
}
