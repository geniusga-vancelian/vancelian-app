import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/features/profile/data/patch_security_preferences_result.dart';

void main() {
  group('patchSecurityPreferencesResultFromHttp', () {
    test('200 → success', () {
      final r = patchSecurityPreferencesResultFromHttp(statusCode: 200, body: '{}');
      expect(r, isA<PatchSecurityPreferencesSuccess>());
    });

    test('401 → unauthorized', () {
      final r = patchSecurityPreferencesResultFromHttp(statusCode: 401, body: '');
      expect(r, isA<PatchSecurityPreferencesFailure>());
      final f = r as PatchSecurityPreferencesFailure;
      expect(f.kind, PatchSecurityPreferencesFailureKind.unauthorized);
    });

    test('404 → endpointNotFound', () {
      final r = patchSecurityPreferencesResultFromHttp(statusCode: 404, body: '');
      final f = r as PatchSecurityPreferencesFailure;
      expect(f.kind, PatchSecurityPreferencesFailureKind.endpointNotFound);
      expect(f.detail, 'http_404');
    });

    test('422 → validation422 avec detail JSON', () {
      final r = patchSecurityPreferencesResultFromHttp(
        statusCode: 422,
        body: '{"detail":"invalid combo"}',
      );
      final f = r as PatchSecurityPreferencesFailure;
      expect(f.kind, PatchSecurityPreferencesFailureKind.validation422);
      expect(f.detail, 'invalid combo');
    });

    test('503 → network', () {
      final r = patchSecurityPreferencesResultFromHttp(statusCode: 503, body: '');
      final f = r as PatchSecurityPreferencesFailure;
      expect(f.kind, PatchSecurityPreferencesFailureKind.network);
    });

    test('418 → clientError', () {
      final r = patchSecurityPreferencesResultFromHttp(statusCode: 418, body: '');
      final f = r as PatchSecurityPreferencesFailure;
      expect(f.kind, PatchSecurityPreferencesFailureKind.clientError);
      expect(f.detail, 'http_418');
    });
  });
}
