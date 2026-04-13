import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:arquantix_news/features/registration/data/registration_api.dart';

void main() {
  group('address proxy error parsing', () {
    test('429 extracts retry_after and message', () {
      final api = RegistrationApi(baseUrl: 'http://localhost:8000');
      final body = jsonEncode({
        'detail': {
          'error': {
            'code': 'rate_limited',
            'message': 'Too many address lookup requests.',
            'retry_after': 61,
          },
        },
      });
      final r = api.testOnlyParseResponse(http.Response(body, 429));
      expect(r.isRateLimited, true);
      expect(r.errorCode, 'rate_limited');
      expect(r.retryAfterSeconds, 61);
      expect(r.errorMessage, contains('Too many'));
    });

    test('422 address_country_mismatch', () {
      final api = RegistrationApi(baseUrl: 'http://localhost:8000');
      final body = jsonEncode({
        'detail': {
          'code': 'address_country_mismatch',
          'message': 'Outside allowed countries.',
          'field': 'country_of_residence',
        },
      });
      final r = api.testOnlyParseResponse(http.Response(body, 422));
      expect(r.isValidationError, true);
      expect(r.errorCode, 'address_country_mismatch');
      expect(r.fieldSlug, 'country_of_residence');
    });
  });
}
