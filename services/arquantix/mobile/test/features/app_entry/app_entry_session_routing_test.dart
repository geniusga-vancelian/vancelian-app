import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:arquantix_news/features/app_entry/domain/app_entry_destination.dart';
import 'package:arquantix_news/features/app_entry/domain/app_entry_session.dart';
import 'package:arquantix_news/features/security/passcode/data/passcode_service.dart';
import 'package:arquantix_news/features/security/passcode/data/session_service.dart';
import 'package:arquantix_news/features/security/passcode/domain/passcode_storage_keys.dart';
import 'package:arquantix_news/features/security/passcode/domain/passcode_user_keys.dart';

/// JWT minimal (signature ignorée par [SessionService.extractJwtSubject]).
String _unsignedJwt({required String sub}) {
  final header =
      base64Url.encode(utf8.encode(jsonEncode({'alg': 'none', 'typ': 'JWT'})));
  final exp = DateTime.now()
          .add(const Duration(days: 365))
          .millisecondsSinceEpoch ~/
      1000;
  final payload = base64Url.encode(
    utf8.encode(jsonEncode({'sub': sub, 'exp': exp})),
  );
  return '$header.$payload.sig';
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('SessionService.clearSession identifiants login mémorisés', () {
    test('clearSession supprime login_last_email et login_last_phone_e164', () async {
      FlutterSecureStorage.setMockInitialValues({
        SessionStorageKeys.loginLastEmail: 'a@example.com',
        SessionStorageKeys.loginLastPhoneE164: '+33600000000',
      });
      await SessionService.instance.clearSession();
      const storage = FlutterSecureStorage();
      expect(await storage.read(key: SessionStorageKeys.loginLastEmail), isNull);
      expect(await storage.read(key: SessionStorageKeys.loginLastPhoneE164), isNull);
    });
  });

  group('SessionService.clearSession volatile security keys', () {
    test('clearSession supprime aussi claims sécurité et horodatages session', () async {
      const sub = 'u@example.com';
      final jwt = _unsignedJwt(sub: sub);
      FlutterSecureStorage.setMockInitialValues({
        SessionStorageKeys.accessToken: jwt,
        SessionStorageKeys.refreshToken: 'rt',
        SessionStorageKeys.securityClaimsJson: '{"step_up_otp":false}',
        SessionStorageKeys.lastLocalUnlockAtMs: '1',
        SessionStorageKeys.lastSensitiveActionAtMs: '2',
        SessionStorageKeys.biometricRecentFailCount: '1',
        SessionStorageKeys.lastBiometricFailAtMs: '3',
      });
      await SessionService.instance.clearSession();
      const storage = FlutterSecureStorage();
      expect(await storage.read(key: SessionStorageKeys.securityClaimsJson), isNull);
      expect(await storage.read(key: SessionStorageKeys.lastLocalUnlockAtMs), isNull);
      expect(await storage.read(key: SessionStorageKeys.lastSensitiveActionAtMs), isNull);
    });
  });

  group('SessionService.storeTokens user switch', () {
    test('change de sub invalide l’état sécurité volatile avant nouveau jeton', () async {
      final jwtA = _unsignedJwt(sub: 'a@example.com');
      final jwtB = _unsignedJwt(sub: 'b@example.com');
      FlutterSecureStorage.setMockInitialValues({
        SessionStorageKeys.accessToken: jwtA,
        SessionStorageKeys.securityClaimsJson: '{"x":1}',
        SessionStorageKeys.lastLocalUnlockAtMs: '99',
        SessionStorageKeys.loginLastEmail: 'ghost@example.com',
        SessionStorageKeys.loginLastPhoneE164: '+33611111111',
      });
      await SessionService.instance.storeTokens(accessToken: jwtB);
      const storage = FlutterSecureStorage();
      expect(await storage.read(key: SessionStorageKeys.accessToken), jwtB);
      expect(await storage.read(key: SessionStorageKeys.lastLocalUnlockAtMs), isNull);
      expect(await storage.read(key: SessionStorageKeys.loginLastEmail), isNull);
      expect(await storage.read(key: SessionStorageKeys.loginLastPhoneE164), isNull);
    });
  });

  group('SessionService.clearSession vs passcode par sub', () {
    test('clearSession supprime jetons mais pas le hash PIN lié au sub', () async {
      const sub = 'alice@example.com';
      final jwt = _unsignedJwt(sub: sub);
      final sfx = passcodeBindingKeySuffix(sub);
      final hashKey = 'arqx.sec.passcode_hash_b64.u.$sfx';

      FlutterSecureStorage.setMockInitialValues({
        SessionStorageKeys.accessToken: jwt,
        SessionStorageKeys.refreshToken: 'rt',
        SessionStorageKeys.accessExpiresAtMs:
            '${DateTime.now().add(const Duration(days: 1)).millisecondsSinceEpoch}',
        SessionStorageKeys.clientGreetingFirstName: 'Alice',
        hashKey: 'local_hash_only',
      });

      await SessionService.instance.clearSession();

      const storage = FlutterSecureStorage();
      expect(await storage.read(key: SessionStorageKeys.accessToken), isNull);
      expect(await storage.read(key: hashKey), 'local_hash_only');
    });
  });

  group('AppEntrySession.resolveDestination', () {
    Future<void> resetPasscodeBinding() async {
      FlutterSecureStorage.setMockInitialValues({});
      await PasscodeService.instance.init();
    }

    setUp(() async {
      await resetPasscodeBinding();
    });

    test('sans jeton → login0', () async {
      FlutterSecureStorage.setMockInitialValues({});
      await PasscodeService.instance.init();
      final d = await AppEntrySession.resolveDestination();
      expect(d, AppEntryDestination.login0);
    });

    test('jeton valide (exp lointaine) + PIN présent pour ce sub → secureGate', () async {
      const sub = 'user-a@example.com';
      final jwt = _unsignedJwt(sub: sub);
      final keys = PasscodeUserKeys.forBinding(sub);

      FlutterSecureStorage.setMockInitialValues({
        SessionStorageKeys.accessToken: jwt,
        SessionStorageKeys.accessExpiresAtMs:
            '${DateTime.now().add(const Duration(days: 1)).millisecondsSinceEpoch}',
        keys.passcodeHashB64: 'h',
        keys.deviceSaltB64: 'c2FsdA==',
      });
      await PasscodeService.instance.init();

      final d = await AppEntrySession.resolveDestination();
      expect(d, AppEntryDestination.secureGate);
    });

    test('jeton valide + aucun PIN pour ce sub → login0 et session effacée', () async {
      const sub = 'user-b@example.com';
      final jwt = _unsignedJwt(sub: sub);

      FlutterSecureStorage.setMockInitialValues({
        SessionStorageKeys.accessToken: jwt,
        SessionStorageKeys.accessExpiresAtMs:
            '${DateTime.now().add(const Duration(days: 1)).millisecondsSinceEpoch}',
      });
      await PasscodeService.instance.init();

      final d = await AppEntrySession.resolveDestination();
      expect(d, AppEntryDestination.login0);
      const storage = FlutterSecureStorage();
      expect(await storage.read(key: SessionStorageKeys.accessToken), isNull);
    });

    test('multi-compte : PIN user A en stockage, session user B → login0 et jetons effacés', () async {
      const subA = 'user-a@example.com';
      const subB = 'user-b@example.com';
      final jwtB = _unsignedJwt(sub: subB);
      final keysA = PasscodeUserKeys.forBinding(subA);

      FlutterSecureStorage.setMockInitialValues({
        SessionStorageKeys.accessToken: jwtB,
        SessionStorageKeys.accessExpiresAtMs:
            '${DateTime.now().add(const Duration(days: 1)).millisecondsSinceEpoch}',
        keysA.passcodeHashB64: 'hash_for_a_only',
        keysA.deviceSaltB64: 'c2FsdA==',
      });
      await PasscodeService.instance.init();

      final d = await AppEntrySession.resolveDestination();
      expect(d, AppEntryDestination.login0);
      const storage = FlutterSecureStorage();
      expect(await storage.read(key: SessionStorageKeys.accessToken), isNull);
    });
  });
}
