import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/features/registration/data/registration_api.dart';

void main() {
  group('ApiResult', () {
    test('isSuccess for 200', () {
      const r = ApiResult<String>(data: 'ok', statusCode: 200);
      expect(r.isSuccess, true);
      expect(r.isValidationError, false);
      expect(r.isBlocked, false);
      expect(r.isAuthError, false);
    });

    test('isSuccess for 201', () {
      const r = ApiResult<String>(data: 'ok', statusCode: 201);
      expect(r.isSuccess, true);
    });

    test('isValidationError for 422', () {
      const r = ApiResult<String>(
        statusCode: 422,
        errorMessage: 'Validation error',
        fieldErrors: {'email': 'Invalid'},
      );
      expect(r.isSuccess, false);
      expect(r.isValidationError, true);
      expect(r.fieldErrors?['email'], 'Invalid');
    });

    test('isBlocked for 409', () {
      const r = ApiResult<String>(
        statusCode: 409,
        errorMessage: 'Step is blocking',
      );
      expect(r.isBlocked, true);
      expect(r.isSuccess, false);
    });

    test('isAuthError for 401', () {
      const r = ApiResult<String>(statusCode: 401);
      expect(r.isAuthError, true);
    });

    test('isAuthError for 403', () {
      const r = ApiResult<String>(statusCode: 403);
      expect(r.isAuthError, true);
    });

    test('network error with statusCode 0', () {
      const r = ApiResult<String>(
        statusCode: 0,
        errorMessage: 'Connection error: timeout',
      );
      expect(r.isSuccess, false);
      expect(r.isValidationError, false);
      expect(r.isBlocked, false);
      expect(r.isAuthError, false);
    });
  });

  group('RegistrationApi construction', () {
    test('stores baseUrl', () {
      final api = RegistrationApi(baseUrl: 'http://localhost:8000');
      expect(api.baseUrl, 'http://localhost:8000');
    });

    test('android emulator default', () {
      final api = RegistrationApi(baseUrl: 'http://10.0.2.2:8000');
      expect(api.baseUrl, contains('10.0.2.2'));
    });
  });
}
