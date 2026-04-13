import 'package:flutter_test/flutter_test.dart';

import 'package:arquantix_news/core/http_error_display.dart';

void main() {
  group('responseBodyLooksLikeNonJsonApi', () {
    test('detects Next dev error page', () {
      const body = '<pre>missing required error components, refreshing...</pre>'
          '<script>async function check() { location.reload() }</script>';
      expect(responseBodyLooksLikeNonJsonApi(body), isTrue);
    });

    test('detects HTML document', () {
      expect(responseBodyLooksLikeNonJsonApi('<html><body>x</body></html>'), isTrue);
    });

    test('JSON error payload is not flagged', () {
      expect(
        responseBodyLooksLikeNonJsonApi(
          '{"error":"Internal server error","message":"oops"}',
        ),
        isFalse,
      );
    });
  });

  group('userFacingHttpErrorMessage', () {
    test('returns safe constant for HTML body', () {
      expect(
        userFacingHttpErrorMessage(
          500,
          '<pre>missing required error components</pre>',
        ),
        kContentTemporarilyUnavailable,
      );
    });

    test('500 JSON still yields readable message', () {
      final m = userFacingHttpErrorMessage(
        500,
        '{"error":"Internal server error","message":"DB timeout"}',
      );
      expect(m, contains('DB timeout'));
      expect(m, isNot(contains('<html')));
    });
  });
}
