import 'dart:convert';

import 'package:cryptography/cryptography.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../passcode/domain/passcode_storage_keys.dart';

/// PR D2 — identité crypto device (ECDSA P-256 / SHA-256), alignée backend
/// `services/auth/device_request_signature.py`.
///
/// Activer les en-têtes refresh : `--dart-define=PR_D2_DEVICE_SIGNING=true`
/// **et** politique serveur (`DEVICE_SECURITY_LEVEL`, credential enregistré).
class DeviceSigningService {
  DeviceSigningService._();
  static final DeviceSigningService instance = DeviceSigningService._();

  /// Signature refresh optionnelle (rétrocompat si `false`).
  static const bool enabled = bool.fromEnvironment(
    'PR_D2_DEVICE_SIGNING',
    defaultValue: false,
  );

  final Ecdsa _algo = Ecdsa.p256(Sha256());
  final FlutterSecureStorage _storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
  );

  /// Clé privée ECDSA P-256 persistée comme scalar `d` (32 octets, base64),
  /// compatible avec [Ecdsa.newKeyPairFromSeed].
  Future<EcKeyPair> _loadOrCreateKeyPair() async {
    final existing = await _storage.read(
      key: SessionStorageKeys.deviceSigningEcdsaSecretB64,
    );
    if (existing != null && existing.isNotEmpty) {
      return _algo.newKeyPairFromSeed(base64Decode(existing));
    }
    final kp = await _algo.newKeyPair();
    final data = await kp.extract();
    await _storage.write(
      key: SessionStorageKeys.deviceSigningEcdsaSecretB64,
      value: base64Encode(data.d),
    );
    return kp;
  }

  /// SPKI DER (base64) pour `POST /auth/device/register-key` (`public_key_spki_b64`).
  Future<String> getPublicKeySpkiB64() async {
    final kp = await _loadOrCreateKeyPair();
    final pub = await kp.extractPublicKey();
    final der = pub.toDer();
    return base64Encode(der);
  }

  /// Payload canonique UTF-8 (identique au backend).
  Future<String> canonicalRefreshSignPayload(int unixTs, String refreshToken) async {
    final hash = await Sha256().hash(utf8.encode(refreshToken));
    final hex = hash.bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    return 'ARQXD2|v1|$unixTs|$hex';
  }

  /// En-têtes à fusionner avec `/auth/refresh` lorsque [enabled] est vrai.
  Future<Map<String, String>> buildRefreshSignatureHeaders(String refreshToken) async {
    final kp = await _loadOrCreateKeyPair();
    final ts = DateTime.now().toUtc().millisecondsSinceEpoch ~/ 1000;
    final payload = await canonicalRefreshSignPayload(ts, refreshToken);
    final sig = await _algo.sign(
      utf8.encode(payload),
      keyPair: kp,
    );
    return <String, String>{
      'X-Device-Signature': base64Encode(sig.bytes),
      'X-Device-Signature-Timestamp': '$ts',
    };
  }
}
