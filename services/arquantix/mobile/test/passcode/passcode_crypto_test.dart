import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/features/security/passcode/data/passcode_crypto.dart';

void main() {
  test('same PIN + salt yields same hash', () async {
    final salt = Uint8List.fromList(List<int>.filled(16, 3));
    final a = await PasscodeCrypto.hashPasscode('123456', salt);
    final b = await PasscodeCrypto.hashPasscode('123456', salt);
    expect(a, b);
  });

  test('different PIN yields different hash', () async {
    final salt = PasscodeCrypto.generateSalt();
    final a = await PasscodeCrypto.hashPasscode('111111', salt);
    final b = await PasscodeCrypto.hashPasscode('222222', salt);
    expect(a, isNot(b));
  });

  test('hashesEqualB64 constant time basics', () {
    expect(PasscodeCrypto.hashesEqualB64('YWI=', 'YWI='), isTrue);
    expect(PasscodeCrypto.hashesEqualB64('YWI=', 'YWJ='), isFalse);
  });
}
