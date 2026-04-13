import 'passkey_provider.dart';
import '../domain/passkey_exceptions.dart';

/// Implémentation par défaut : aucune intégration native (fallback OTP / mot de passe).
class PasskeyProviderStub implements PasskeyPlatformProvider {
  @override
  Future<bool> get isAvailable async => false;

  @override
  Future<Map<String, dynamic>> createCredential(Map<String, dynamic> optionsJson) async {
    throw PasskeyUnavailableException('createCredential not implemented (stub)');
  }

  @override
  Future<Map<String, dynamic>> getCredential(Map<String, dynamic> optionsJson) async {
    throw PasskeyUnavailableException('getCredential not implemented (stub)');
  }
}
