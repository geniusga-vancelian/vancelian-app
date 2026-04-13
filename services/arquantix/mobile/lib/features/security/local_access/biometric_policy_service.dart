import '../passcode/data/biometric_auth_service.dart';
import '../passcode/data/passcode_service.dart';
import '../passcode/domain/secure_access_config.dart';
import '../session/session_intelligence_manager.dart';
import 'local_relock_engine.dart';
import 'session_security_snapshot.dart';

/// Politique biométrique + relock : orchestration async, décisions testables via paramètres.
class BiometricPolicyService {
  BiometricPolicyService._();
  static final BiometricPolicyService instance = BiometricPolicyService._();

  /// Matériel + capteurs disponibles (indépendamment du réglage utilisateur).
  Future<bool> isBiometricAvailable() async {
    return BiometricAuthService.instance.deviceSupportsBiometrics();
  }

  /// Biométrie utilisable par défaut si l’utilisateur l’a activée dans les réglages PIN.
  Future<bool> shouldUseBiometricByDefault() async {
    await PasscodeService.instance.init();
    if (!await PasscodeService.instance.isBiometricUnlockEnabled()) {
      return false;
    }
    return isBiometricAvailable();
  }

  /// Décision de relock au resume (à appeler depuis [WidgetsBindingObserver]).
  ///
  /// [lastActiveAt] : moment du dernier `paused` si [appLifecycleContext.backgroundDuration]
  /// n’est pas déjà renseignée.
  Future<bool> shouldRelockNow({
    required DateTime? lastActiveAt,
    required SessionSecuritySnapshot riskContext,
    required AppLifecycleSecurityContext appLifecycleContext,
    DateTime? now,
  }) async {
    final clock = now ?? DateTime.now();
    if (!appLifecycleContext.isReturningFromBackground) return false;
    final bg = appLifecycleContext.backgroundDuration ??
        (lastActiveAt != null ? clock.difference(lastActiveAt) : null);
    if (bg == null) return false;
    final ctx = AppLifecycleSecurityContext(
      isReturningFromBackground: true,
      backgroundDuration: bg,
    );
    const config = RelockEngineConfig(
      relockThresholdNormal: SecureAccessConfig.resumeRelockAfter,
      relockThresholdHighRisk: SecureAccessConfig.resumeRelockAfterHighRisk,
      maxGracePeriod: SecureAccessConfig.relockMaxGracePeriod,
      debounceAfterLocalUnlock: SecureAccessConfig.relockDebounceAfterLocalUnlock,
    );
    final intelThreshold = await SessionIntelligenceManager.effectiveRelockThreshold(
      config: config,
      now: clock,
    );
    return LocalRelockEngine.shouldRelockNow(
      appLifecycleContext: ctx,
      riskContext: riskContext,
      now: clock,
      config: config,
      effectiveThresholdOverride: intelThreshold,
    );
  }

  /// Supprime le prompt biométrique **automatique** (tap manuel inchangé ailleurs).
  ///
  /// Uniquement pour échecs biométriques locaux répétés dans une fenêtre courte — pas pour
  /// `step_up_otp` JWT : le step-up serveur ne doit pas désactiver Face ID auto au
  /// déverrouillage local (OTP / flux sensibles restent côté API).
  Future<bool> shouldForcePinInsteadOfBiometric({
    required int biometricRecentFailCount,
    DateTime? lastBiometricFailAt,
    DateTime? now,
  }) async {
    final clock = now ?? DateTime.now();
    if (biometricRecentFailCount >=
        SecureAccessConfig.biometricFailuresBeforePinFirst) {
      final last = lastBiometricFailAt;
      if (last != null &&
          clock.difference(last) <=
              SecureAccessConfig.biometricFailureRecentWindow) {
        return true;
      }
    }
    return false;
  }
}
