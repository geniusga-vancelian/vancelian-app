import 'dart:convert';

import 'package:arquantix_news/features/security/passcode/domain/jwt_access_claims.dart';
import 'package:flutter_test/flutter_test.dart';

/// JWT factices (signature ignorée par les extracteurs).
String _fakeJwt(Map<String, dynamic> payload) {
  final b64 = base64Url.encode(utf8.encode(jsonEncode(payload)));
  return 'x.$b64.y';
}

void main() {
  group('isAccessTokenAccountActiveForApp', () {
    test('ACTIVE sans sec_inc → true', () {
      final t = _fakeJwt({'acct_st': 'ACTIVE', 'exp': 9999999999});
      expect(isAccessTokenAccountActiveForApp(t), isTrue);
    });

    test('PARTIAL → false', () {
      final t = _fakeJwt({'acct_st': 'PARTIAL', 'sec_inc': true, 'exp': 9999999999});
      expect(isAccessTokenAccountActiveForApp(t), isFalse);
    });

    test('sec_inc seul → false', () {
      final t = _fakeJwt({'sec_inc': true, 'exp': 9999999999});
      expect(isAccessTokenAccountActiveForApp(t), isFalse);
    });

    test('legacy sans acct_st ni sec_inc → true', () {
      final t = _fakeJwt({'sub': 'u@example.com', 'exp': 9999999999});
      expect(isAccessTokenAccountActiveForApp(t), isTrue);
    });
  });
}
