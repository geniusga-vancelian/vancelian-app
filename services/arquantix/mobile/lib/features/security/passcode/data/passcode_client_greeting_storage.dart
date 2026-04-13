import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../domain/jwt_access_claims.dart';
import '../domain/passcode_user_keys.dart';

/// Prénom d’accueil SecureStorage — **mêmes options** que [PasscodeService] (Keychain / Keystore).
///
/// Stocké **par `sub` JWT** comme le hash PIN, pour rester disponible sur l’écran déverrouillage
/// même si la clé « session » éphémère a été nettoyée entre-temps.
class PasscodeClientGreetingStorage {
  PasscodeClientGreetingStorage._();
  static final PasscodeClientGreetingStorage instance =
      PasscodeClientGreetingStorage._();

  final FlutterSecureStorage _storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
  );

  /// À appeler après chaque [SessionService.storeTokens] avec le prénom effectivement
  /// persisté côté session (ou `null` pour effacer).
  Future<void> writeForAccessToken(
    String accessToken,
    String? greetingFirstName,
  ) async {
    final sub = jwtExtractSubject(accessToken);
    final keys = PasscodeUserKeys.forBinding(sub);
    if (greetingFirstName == null || greetingFirstName.trim().isEmpty) {
      await _storage.delete(key: keys.clientGreetingFirstName);
      return;
    }
    await _storage.write(
      key: keys.clientGreetingFirstName,
      value: greetingFirstName.trim(),
    );
  }

  Future<String?> readForAccessToken(String? accessToken) async {
    if (accessToken == null || accessToken.isEmpty) return null;
    final sub = jwtExtractSubject(accessToken);
    final keys = PasscodeUserKeys.forBinding(sub);
    final v = await _storage.read(key: keys.clientGreetingFirstName);
    if (v != null && v.trim().isNotEmpty) return v.trim();
    return null;
  }
}
