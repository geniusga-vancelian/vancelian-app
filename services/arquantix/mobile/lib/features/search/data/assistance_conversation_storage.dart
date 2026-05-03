import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Persistance locale de **l'ID de la conversation courante** d'assistance
/// (MVP D.1.3). Le cycle de vie suit l'utilisateur : la conversation est
/// reprise au prochain lancement de l'app tant qu'il ne déclenche pas
/// « Nouvelle conversation ».
///
/// Utilise [FlutterSecureStorage] (déjà disponible dans le projet) plutôt que
/// `shared_preferences` pour éviter d'introduire une nouvelle dépendance — le
/// stockage est sécurisé par le Keychain (iOS) / EncryptedSharedPreferences
/// (Android) ce qui n'est pas un problème pour cette donnée non-sensible.
class AssistanceConversationStorage {
  AssistanceConversationStorage._();
  static final AssistanceConversationStorage instance =
      AssistanceConversationStorage._();

  static const String _kCurrentConversationId =
      'assistance.current_conversation_id';

  final FlutterSecureStorage _storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
  );

  Future<String?> read() async {
    final v = await _storage.read(key: _kCurrentConversationId);
    if (v == null || v.trim().isEmpty) return null;
    return v;
  }

  Future<void> write(String conversationId) async {
    await _storage.write(
      key: _kCurrentConversationId,
      value: conversationId,
    );
  }

  Future<void> clear() async {
    await _storage.delete(key: _kCurrentConversationId);
  }
}
