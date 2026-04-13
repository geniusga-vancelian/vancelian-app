import 'package:arquantix_news/core/session_bearer_http.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  tearDown(() {
    SessionBearerHttp.debugAccessTokenReader = null;
  });

  test('required: sans jeton → MissingBearerTokenException', () async {
    SessionBearerHttp.debugAccessTokenReader = () async => null;
    await expectLater(
      SessionBearerHttp.jsonHeaders(
        uri: Uri.parse('https://api.example.com/v1/profile'),
        debugTag: 'test.required',
        policy: SessionBearerPolicy.required,
      ),
      throwsA(isA<MissingBearerTokenException>()),
    );
  });

  test('optional: sans jeton → Accept seulement', () async {
    SessionBearerHttp.debugAccessTokenReader = () async => null;
    final h = await SessionBearerHttp.jsonHeaders(
      uri: Uri.parse('https://api.example.com/x'),
      debugTag: 'test.optional',
      policy: SessionBearerPolicy.optional,
    );
    expect(h['Authorization'], isNull);
    expect(h['Accept'], 'application/json');
  });

  test('overrideAccessToken: Authorization présent', () async {
    SessionBearerHttp.debugAccessTokenReader = () async => null;
    final h = await SessionBearerHttp.jsonHeaders(
      uri: Uri.parse('https://api.example.com/x'),
      debugTag: 'test.override',
      policy: SessionBearerPolicy.required,
      overrideAccessToken: 'jwt-here',
    );
    expect(h['Authorization'], 'Bearer jwt-here');
  });
}
