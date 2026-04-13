import 'package:flutter_test/flutter_test.dart';

import 'package:arquantix_news/features/security/passcode/data/session_service.dart';
import 'package:arquantix_news/features/security/passcode/domain/passcode_user_keys.dart';

void main() {
  group('SessionService.extractJwtSubject', () {
    test('extrait sub depuis un JWT trois segments', () {
      const token =
          'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyLTEiLCJuYW1lIjoiVGVzdCJ9.xxx';
      expect(SessionService.extractJwtSubject(token), 'user-1');
    });

    test('token opaque (pas 3 segments) → null', () {
      expect(SessionService.extractJwtSubject('opaque-token-value'), isNull);
    });
  });

  group('PasscodeUserKeys.forBinding', () {
    test('deux utilisateurs → clés hash différentes', () {
      final a = PasscodeUserKeys.forBinding('user-a');
      final b = PasscodeUserKeys.forBinding('user-b');
      expect(a.passcodeHashB64, isNot(b.passcodeHashB64));
      expect(a.deviceSaltB64, isNot(b.deviceSaltB64));
    });

    test('binding null → clés legacy inchangées', () {
      final legacy = PasscodeUserKeys.forBinding(null);
      expect(legacy.passcodeHashB64, 'arqx.sec.passcode_hash_b64');
    });

    test('passcodeBindingKeySuffix stable', () {
      expect(passcodeBindingKeySuffix('same'), passcodeBindingKeySuffix('same'));
      expect(
        passcodeBindingKeySuffix('a'),
        isNot(passcodeBindingKeySuffix('b')),
      );
    });
  });
}
