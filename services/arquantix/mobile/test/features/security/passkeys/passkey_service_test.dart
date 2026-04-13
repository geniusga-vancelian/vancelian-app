import 'dart:convert';

import 'package:arquantix_news/features/security/passkeys/application/passkey_service.dart';
import 'package:arquantix_news/features/security/passkeys/data/passkey_api.dart';
import 'package:arquantix_news/features/security/passkeys/data/passkey_provider.dart';
import 'package:arquantix_news/features/security/passkeys/data/passkey_provider_stub.dart';
import 'package:arquantix_news/features/security/passkeys/domain/passkey_exceptions.dart';
import 'package:arquantix_news/features/security/passkeys/presentation/passkey_login_coordinator.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

class _CancelOnGetProvider implements PasskeyPlatformProvider {
  @override
  Future<bool> get isAvailable async => true;

  @override
  Future<Map<String, dynamic>> createCredential(Map<String, dynamic> optionsJson) async =>
      throw UnimplementedError();

  @override
  Future<Map<String, dynamic>> getCredential(Map<String, dynamic> optionsJson) async {
    throw PasskeyUserCancelledException();
  }
}

class _FakeOkProvider implements PasskeyPlatformProvider {
  @override
  Future<bool> get isAvailable async => true;

  @override
  Future<Map<String, dynamic>> createCredential(Map<String, dynamic> optionsJson) async => {
        'id': 'YQ',
        'rawId': 'YQ',
        'type': 'public-key',
        'response': <String, dynamic>{},
      };

  @override
  Future<Map<String, dynamic>> getCredential(Map<String, dynamic> optionsJson) async => {
        'id': 'YQ',
        'rawId': 'YQ',
        'type': 'public-key',
        'response': <String, dynamic>{
          'clientDataJSON': 'e30',
          'authenticatorData': 'Eg',
          'signature': 'c2ln',
        },
      };
}

void main() {
  test('stub provider makes enroll unavailable', () async {
    final api = PasskeyApi(debugBaseUrl: 'http://localhost', httpClient: MockClient((_) async => http.Response('', 500)));
    final svc = PasskeyService(
      api: api,
      provider: PasskeyProviderStub(),
      getDeviceId: () async => 'dev',
      getFingerprintHeader: () async => null,
    );
    expect(
      () => svc.enrollPasskey(accessToken: 't'),
      throwsA(isA<PasskeyUnavailableException>()),
    );
  });

  test('enroll start then finish when provider returns credential', () async {
    final client = MockClient((req) async {
      if (req.url.path.endsWith('/auth/passkeys/register/start')) {
        return http.Response(
          jsonEncode({
            'options': {'challenge': 'Y2g', 'rp': {'id': 'localhost'}},
            'challenge_token': '550e8400-e29b-41d4-a716-446655440000',
          }),
          200,
        );
      }
      if (req.url.path.endsWith('/auth/passkeys/register/finish')) {
        return http.Response(jsonEncode({'credential_id': 'x', 'status': 'ok'}), 200);
      }
      return http.Response('nf', 404);
    });
    final api = PasskeyApi(debugBaseUrl: 'http://localhost', httpClient: client);
    final svc = PasskeyService(
      api: api,
      provider: _FakeOkProvider(),
      getDeviceId: () async => 'dev',
      getFingerprintHeader: () async => null,
    );
    await svc.enrollPasskey(accessToken: 'bearer-token');
  });

  test('login finish stores tokens path — mock HTTP', () async {
    final client = MockClient((req) async {
      if (req.url.path.endsWith('/auth/passkeys/login/start')) {
        return http.Response(
          jsonEncode({
            'options': {
              'challenge': 'Y2g',
              'rpId': 'localhost',
              'timeout': 120000,
            },
            'challenge_token': '660e8400-e29b-41d4-a716-446655440001',
          }),
          200,
        );
      }
      if (req.url.path.endsWith('/auth/passkeys/login/finish')) {
        return http.Response(
          jsonEncode({
            'access_token': 'at',
            'token_type': 'bearer',
            'refresh_token': 'rt',
          }),
          200,
        );
      }
      return http.Response('nf', 404);
    });
    final api = PasskeyApi(debugBaseUrl: 'http://localhost', httpClient: client);
    final svc = PasskeyService(
      api: api,
      provider: _FakeOkProvider(),
      getDeviceId: () async => 'dev',
      getFingerprintHeader: () async => null,
    );
    final tokens = await svc.loginWithPasskey('u@example.com');
    expect(tokens['access_token'], 'at');
    expect(tokens['refresh_token'], 'rt');
  });

  test('coordinator invokes fallback on unavailable passkey', () async {
    var fallback = false;
    final api = PasskeyApi(
      debugBaseUrl: 'http://localhost',
      httpClient: MockClient((req) async {
        if (req.url.path.endsWith('/auth/passkeys/prompt')) {
          return http.Response('', 204);
        }
        return http.Response('', 500);
      }),
    );
    final svc = PasskeyService(
      api: api,
      provider: PasskeyProviderStub(),
      getDeviceId: () async => 'd',
      getFingerprintHeader: () async => null,
    );
    final coord = PasskeyLoginCoordinator(passkeyService: svc, api: api);
    await coord.signInWithPasskey(
      email: 'a@b.com',
      onFallback: () => fallback = true,
      onSuccess: () async {},
    );
    expect(fallback, isTrue);
  });

  test('coordinator fallback when user cancels passkey prompt', () async {
    var fallback = false;
    final client = MockClient((req) async {
      if (req.url.path.endsWith('/auth/passkeys/prompt')) {
        return http.Response('', 204);
      }
      if (req.url.path.endsWith('/auth/passkeys/login/start')) {
        return http.Response(
          jsonEncode({
            'options': {
              'challenge': 'Y2g',
              'rpId': 'localhost',
              'timeout': 120000,
            },
            'challenge_token': '660e8400-e29b-41d4-a716-446655440099',
          }),
          200,
        );
      }
      return http.Response('nf', 404);
    });
    final api = PasskeyApi(debugBaseUrl: 'http://localhost', httpClient: client);
    final svc = PasskeyService(
      api: api,
      provider: _CancelOnGetProvider(),
      getDeviceId: () async => 'd',
      getFingerprintHeader: () async => null,
    );
    final coord = PasskeyLoginCoordinator(passkeyService: svc, api: api);
    await coord.signInWithPasskey(
      email: 'a@b.com',
      onFallback: () => fallback = true,
      onSuccess: () async {},
    );
    expect(fallback, isTrue);
  });
}
