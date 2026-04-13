import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/core/phone_e164.dart';

void main() {
  group('normalizePhoneFieldToE164', () {
    test('strips single leading 0 and prepends dial code', () {
      expect(
        normalizePhoneFieldToE164('0612345678', '+33'),
        '+33612345678',
      );
    });

    test('passes through full E.164 unchanged', () {
      expect(
        normalizePhoneFieldToE164('+33612345678', '+33'),
        '+33612345678',
      );
    });

    test('empty after strip yields empty', () {
      expect(normalizePhoneFieldToE164('0', '+33'), '');
    });
  });
}
