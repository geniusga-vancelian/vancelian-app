import 'package:flutter/foundation.dart';

import '../../security/passcode/data/session_service.dart';
import 'mobile_profile_api.dart';

/// États de sync outbound (decision memo) — par domaine.
enum SecurityDomainSyncState {
  idle,
  pendingSync,
  synced,
  syncFailed,
}

/// Retry léger après échec PATCH (pas de rollback local).
class SecurityPreferencesSyncService {
  SecurityPreferencesSyncService._();
  static final SecurityPreferencesSyncService instance =
      SecurityPreferencesSyncService._();

  SecurityDomainSyncState biometricState = SecurityDomainSyncState.idle;
  SecurityDomainSyncState pushState = SecurityDomainSyncState.idle;

  Map<String, dynamic>? _pendingBiometric;
  Map<String, dynamic>? _pendingPush;

  void rememberPendingBiometric(Map<String, dynamic> payload) {
    _pendingBiometric = Map<String, dynamic>.from(payload);
    biometricState = SecurityDomainSyncState.pendingSync;
  }

  void rememberPendingPush(Map<String, dynamic> payload) {
    _pendingPush = Map<String, dynamic>.from(payload);
    pushState = SecurityDomainSyncState.pendingSync;
  }

  /// Appelé depuis resume / après écran ; une tentative de rattrapage.
  Future<void> flushPendingRetries() async {
    final tok = await SessionService.instance.readAccessToken();
    if (tok == null || tok.isEmpty) return;

    const api = MobileProfileApi();
    if (_pendingBiometric != null) {
      final r = await api.patchSecurityPreferencesV1(
        accessToken: tok,
        biometric: _pendingBiometric,
      );
      if (r.isSuccess) {
        _pendingBiometric = null;
        biometricState = SecurityDomainSyncState.synced;
      } else {
        biometricState = SecurityDomainSyncState.syncFailed;
      }
    }
    if (_pendingPush != null) {
      final r = await api.patchSecurityPreferencesV1(
        accessToken: tok,
        pushNotifications: _pendingPush,
      );
      if (r.isSuccess) {
        _pendingPush = null;
        pushState = SecurityDomainSyncState.synced;
      } else {
        pushState = SecurityDomainSyncState.syncFailed;
      }
    }
  }

  /// File d’attente + retry différé unique (sans bloquer l’UI).
  Future<void> scheduleBiometricRetry(Map<String, dynamic> biometric) async {
    rememberPendingBiometric(biometric);
    await Future<void>.delayed(const Duration(seconds: 5));
    if (kDebugMode) {
      debugPrint('[SecurityPreferencesSync] retry biometric flush');
    }
    await flushPendingRetries();
  }

  Future<void> schedulePushRetry(Map<String, dynamic> push) async {
    rememberPendingPush(push);
    await Future<void>.delayed(const Duration(seconds: 5));
    await flushPendingRetries();
  }
}
