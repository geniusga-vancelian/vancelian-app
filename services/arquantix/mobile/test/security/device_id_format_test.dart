import 'package:arquantix_news/features/security/passcode/data/device_id_service.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('generateNewId looks like UUID v4', () {
    final id = DeviceIdService.generateNewId();
    expect(
      RegExp(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
      ).hasMatch(id),
      isTrue,
    );
  });
}
