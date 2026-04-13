import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/features/registration/registration_phone_format_validation.dart';

void main() {
  group('isRegistrationPhoneFormatValid', () {
    test('FR mobile valide (0 puis 9 chiffres)', () {
      expect(isRegistrationPhoneFormatValid('0612345678', 'FR'), isTrue);
      expect(isRegistrationPhoneFormatValid('07 12 34 56 78', 'FR'), isTrue);
    });

    test('FR invalide — trop court (ex. capture écran)', () {
      expect(isRegistrationPhoneFormatValid('06521474', 'FR'), isFalse);
    });

    test('FR invalide — fixe (01…)', () {
      expect(isRegistrationPhoneFormatValid('0123456789', 'FR'), isFalse);
    });

    test('US 10 chiffres nationaux', () {
      expect(isRegistrationPhoneFormatValid('5551234567', 'US'), isTrue);
    });

    test('vide ou blanc', () {
      expect(isRegistrationPhoneFormatValid('', 'FR'), isFalse);
      expect(isRegistrationPhoneFormatValid('   ', 'FR'), isFalse);
    });
  });
}
