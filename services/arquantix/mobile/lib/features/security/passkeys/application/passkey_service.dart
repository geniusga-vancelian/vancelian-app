import '../data/passkey_api.dart';
import '../data/passkey_provider.dart';
import '../domain/passkey_exceptions.dart';

/// Orchestration enrôlement / login passkey (backend Phase 3.2 + provider natif injectable).
class PasskeyService {
  PasskeyService({
    required PasskeyApi api,
    required PasskeyPlatformProvider provider,
    required Future<String> Function() getDeviceId,
    required Future<String?> Function() getFingerprintHeader,
  })  : _api = api,
        _provider = provider,
        _getDeviceId = getDeviceId,
        _getFingerprintHeader = getFingerprintHeader;

  final PasskeyApi _api;
  final PasskeyPlatformProvider _provider;
  final Future<String> Function() _getDeviceId;
  final Future<String?> Function() _getFingerprintHeader;

  /// Utilisateur déjà connecté (Bearer) — enrôle une passkey.
  Future<void> enrollPasskey({
    required String accessToken,
    String? deviceLabel,
  }) async {
    if (!await _provider.isAvailable) {
      throw PasskeyUnavailableException();
    }
    final start = await _api.registerStart(
      accessToken: accessToken,
      deviceLabel: deviceLabel,
    );
    final options = Map<String, dynamic>.from(start['options'] as Map<dynamic, dynamic>);
    final cred = await _provider.createCredential(options);
    await _api.registerFinish(
      accessToken: accessToken,
      challengeToken: start['challenge_token'] as String,
      credential: cred,
      deviceLabel: deviceLabel,
    );
  }

  /// Login sans mot de passe — retourne le JSON token FastAPI (access + refresh).
  Future<Map<String, dynamic>> loginWithPasskey(String email) async {
    if (!await _provider.isAvailable) {
      throw PasskeyUnavailableException();
    }
    final start = await _api.loginStart(email: email);
    final options = Map<String, dynamic>.from(start['options'] as Map<dynamic, dynamic>);
    final cred = await _provider.getCredential(options);
    final deviceId = await _getDeviceId();
    final fp = await _getFingerprintHeader();
    return _api.loginFinish(
      challengeToken: start['challenge_token'] as String,
      credential: cred,
      deviceId: deviceId,
      fingerprintHeader: fp,
    );
  }

  Future<List<Map<String, dynamic>>> listPasskeys(String accessToken) =>
      _api.listPasskeys(accessToken: accessToken);

  Future<void> revokePasskey({
    required String accessToken,
    required String credentialId,
  }) =>
      _api.revokePasskey(accessToken: accessToken, credentialId: credentialId);
}
