import 'dart:convert';
import 'dart:io' show Platform;
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../../../core/app_info_service.dart';
import '../domain/passcode_storage_keys.dart';

/// Identifiant d’appareil **stable** pour le binding API (Phase 2 / PR B).
///
/// **Discipline** : une seule valeur par installation, lue depuis le stockage sécurisé
/// ([FlutterSecureStorage]). Elle **ne doit pas** être régénérée au redémarrage de l’app ni après
/// reboot OS : tant que la clé [SessionStorageKeys.deviceId] existe, [getOrCreate] la retourne.
/// Un nouvel UUID n’est créé qu’à la **première** utilisation ou après perte des données
/// (désinstallation, effacement données app, réinitialisation Keychain/Keystore selon plateforme).
///
/// Toujours envoyer cette valeur en en-tête `X-Device-ID` sur login, refresh, revoke et routes auth.
///
/// Phase 3.1 : empreinte enrichie JSON dans `X-Device-Fingerprint`.
class DeviceIdService {
  DeviceIdService._();
  static final DeviceIdService instance = DeviceIdService._();

  final FlutterSecureStorage _storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
  );

  static String generateNewId() {
    final r = Random.secure();
    final b = List<int>.generate(16, (_) => r.nextInt(256));
    b[6] = (b[6] & 0x0f) | 0x40;
    b[8] = (b[8] & 0x3f) | 0x80;
    final hex = b.map((e) => e.toRadixString(16).padLeft(2, '0')).join();
    return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
  }

  /// Retourne l’identifiant persisté ou en génère un **une seule fois** puis le persiste.
  ///
  /// Idempotent entre processus : redémarrage cold, reboot appareil — même valeur tant que le
  /// stockage secure n’est pas effacé.
  Future<String> getOrCreate() async {
    final existing = await _storage.read(key: SessionStorageKeys.deviceId);
    if (existing != null && existing.isNotEmpty) {
      return existing;
    }
    final id = generateNewId();
    await _storage.write(key: SessionStorageKeys.deviceId, value: id);
    return id;
  }

  Future<String> getOrCreateInstallId() async {
    final existing = await _storage.read(key: SessionStorageKeys.installId);
    if (existing != null && existing.isNotEmpty) {
      return existing;
    }
    final id = generateNewId();
    await _storage.write(key: SessionStorageKeys.installId, value: id);
    return id;
  }

  /// JSON UTF-8 pour l’en-tête `X-Device-Fingerprint` ; `null` sur web (hors scope mobile natif).
  Future<String?> buildFingerprintHeaderJson() async {
    if (kIsWeb) {
      return null;
    }
    final deviceId = await getOrCreate();
    final installId = await getOrCreateInstallId();
    var platform = 'other';
    if (Platform.isIOS) {
      platform = 'ios';
    } else if (Platform.isAndroid) {
      platform = 'android';
    }
    final osv = Platform.operatingSystemVersion;
    final map = <String, dynamic>{
      'device_id': deviceId,
      'install_id': installId,
      'platform': platform,
      'os_version': osv.length > 64 ? osv.substring(0, 64) : osv,
      'app_version': AppInfoService.fullVersion,
    };
    return jsonEncode(map);
  }
}
