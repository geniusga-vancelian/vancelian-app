import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';

/// Dérivation PBKDF2-HMAC-SHA256 — jamais de log du PIN ni du hash.
class PasscodeCrypto {
  PasscodeCrypto._();

  static const int _saltLength = 16;
  static const int _iterations = 120000;
  static const int _bits = 256;

  static final Pbkdf2 _pbkdf2 = Pbkdf2(
    macAlgorithm: Hmac.sha256(),
    iterations: _iterations,
    bits: _bits,
  );

  static Uint8List generateSalt() {
    final rnd = Random.secure();
    final b = Uint8List(_saltLength);
    for (var i = 0; i < _saltLength; i++) {
      b[i] = rnd.nextInt(256);
    }
    return b;
  }

  static Future<String> hashPasscode(String pin, Uint8List salt) async {
    final secretKey = await _pbkdf2.deriveKeyFromPassword(
      password: pin,
      nonce: salt,
    );
    final bytes = await secretKey.extractBytes();
    return base64Encode(Uint8List.fromList(bytes));
  }

  /// Comparaison en temps constant sur les octets décodés.
  static bool hashesEqualB64(String aB64, String bB64) {
    try {
      final a = base64Decode(aB64);
      final b = base64Decode(bB64);
      if (a.length != b.length) return false;
      var x = 0;
      for (var i = 0; i < a.length; i++) {
        x |= a[i] ^ b[i];
      }
      return x == 0;
    } catch (_) {
      return false;
    }
  }
}
