import 'dart:convert';

/// Abstraction plateforme WebAuthn — implémentations : stub, plugin natif futur.
abstract class PasskeyPlatformProvider {
  /// True si l’API Credentials / passkeys est utilisable.
  Future<bool> get isAvailable;

  /// Création de credential (navigator.credentials.create) — [optionsJson] = clé `options` du backend.
  Future<Map<String, dynamic>> createCredential(Map<String, dynamic> optionsJson);

  /// Assertion (navigator.credentials.get).
  Future<Map<String, dynamic>> getCredential(Map<String, dynamic> optionsJson);
}

/// Sérialise un Map pour envoi JSON (tests / debug).
String passkeyOptionsToJson(Map<String, dynamic> options) => jsonEncode(options);
