import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/features/registration/registration_phone_user_errors.dart';

void main() {
  group('RegistrationPhoneUserErrors', () {
    test('titleForCode maps known codes', () {
      expect(
        RegistrationPhoneUserErrors.titleForCode('invalid_phone_number'),
        'Invalid phone number',
      );
      expect(
        RegistrationPhoneUserErrors.titleForCode('phone_number_not_mobile'),
        'Unsupported number',
      );
      expect(
        RegistrationPhoneUserErrors.titleForCode('unsupported_phone_country'),
        'Unsupported phone number',
      );
      expect(
        RegistrationPhoneUserErrors.titleForCode('phone_country_mismatch'),
        'Country code mismatch',
      );
    });

    test('messageForCode matches backend-oriented copy', () {
      expect(
        RegistrationPhoneUserErrors.messageForCode('unsupported_phone_country'),
        contains('not supported for your jurisdiction'),
      );
      expect(
        RegistrationPhoneUserErrors.messageForCode('phone_country_mismatch'),
        contains('does not match the selected country'),
      );
    });
  });
}
