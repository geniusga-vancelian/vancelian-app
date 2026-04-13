import 'package:flutter/foundation.dart';

/// Lecture `security_preferences` — modèle V1 structuré + champs legacy plats (API).
@immutable
class MobileSecurityPreferences {
  const MobileSecurityPreferences({
    this.securityModelVersion = 0,
    this.biometric,
    this.pushNotifications,
    this.biometricUnlockEnabled = false,
    this.biometricLoginOnboardingCompleted = false,
    this.pushNotificationsEnabled = false,
    this.pushNotificationsOnboardingCompleted = false,
  });

  final int securityModelVersion;
  final BiometricSecurityState? biometric;
  final PushNotificationsSecurityState? pushNotifications;

  /// Projection serveur (dérivée) — compat clients ; préférer [biometric] quand présent.
  final bool biometricUnlockEnabled;
  final bool biometricLoginOnboardingCompleted;
  final bool pushNotificationsEnabled;
  final bool pushNotificationsOnboardingCompleted;

  /// Gate onboarding bloquant biométrie : backend = source de vérité produit.
  bool get isBiometricOnboardingCompleted {
    final b = biometric;
    if (b != null) {
      return b.onboardingStatus == 'completed';
    }
    return biometricLoginOnboardingCompleted;
  }

  /// Gate onboarding push.
  bool get isPushOnboardingCompleted {
    final p = pushNotifications;
    if (p != null) {
      return p.onboardingStatus == 'completed';
    }
    return pushNotificationsOnboardingCompleted;
  }

  /// Réinstallation / nouvel appareil : compte a complété mais pas de config locale (hors gate bloquant).
  bool needsLocalBiometricReconfiguration({
    required bool localBiometricUnlockConfigured,
  }) {
    return isBiometricOnboardingCompleted &&
        biometric?.preferenceEnabled == true &&
        !localBiometricUnlockConfigured;
  }

  factory MobileSecurityPreferences.fromJson(Map<String, dynamic> json) {
    BiometricSecurityState? bio;
    PushNotificationsSecurityState? push;
    try {
      final rawB = json['biometric'];
      if (rawB is Map<String, dynamic>) {
        bio = BiometricSecurityState.fromJson(rawB);
      }
      final rawP = json['push_notifications'];
      if (rawP is Map<String, dynamic>) {
        push = PushNotificationsSecurityState.fromJson(rawP);
      }
    } catch (e, st) {
      if (kDebugMode) {
        debugPrint('[MobileSecurityPreferences] parse partial: $e $st');
      }
    }
    return MobileSecurityPreferences(
      securityModelVersion: (json['security_model_version'] as num?)?.toInt() ?? 0,
      biometric: bio,
      pushNotifications: push,
      biometricUnlockEnabled: json['biometric_unlock_enabled'] == true,
      biometricLoginOnboardingCompleted:
          json['biometric_login_onboarding_completed'] == true,
      pushNotificationsEnabled: json['push_notifications_enabled'] == true,
      pushNotificationsOnboardingCompleted:
          json['push_notifications_onboarding_completed'] == true,
    );
  }
}

@immutable
class BiometricSecurityState {
  const BiometricSecurityState({
    this.preferenceEnabled,
    this.preferenceUpdatedAt,
    this.onboardingStatus = 'not_started',
    this.onboardingOutcome = 'unknown',
    this.onboardingCompletedAt,
    this.lastClientReportedAt,
    this.onboardingSource = 'unknown',
    this.deviceCapabilityLastKnown = 'unknown',
  });

  final bool? preferenceEnabled;
  final String? preferenceUpdatedAt;
  final String onboardingStatus;
  final String onboardingOutcome;
  final String? onboardingCompletedAt;
  final String? lastClientReportedAt;
  final String onboardingSource;
  final String deviceCapabilityLastKnown;

  factory BiometricSecurityState.fromJson(Map<String, dynamic> json) {
    return BiometricSecurityState(
      preferenceEnabled: json['preference_enabled'] == null
          ? null
          : json['preference_enabled'] == true,
      preferenceUpdatedAt: _s(json['preference_updated_at']),
      onboardingStatus: _s(json['onboarding_status']) ?? 'not_started',
      onboardingOutcome: _s(json['onboarding_outcome']) ?? 'unknown',
      onboardingCompletedAt: _s(json['onboarding_completed_at']),
      lastClientReportedAt: _s(json['last_client_reported_at']),
      onboardingSource: _s(json['onboarding_source']) ?? 'unknown',
      deviceCapabilityLastKnown:
          _s(json['device_capability_last_known']) ?? 'unknown',
    );
  }
}

@immutable
class PushNotificationsSecurityState {
  const PushNotificationsSecurityState({
    this.preferenceEnabled,
    this.preferenceUpdatedAt,
    this.onboardingStatus = 'not_started',
    this.onboardingOutcome = 'unknown',
    this.onboardingCompletedAt,
    this.lastClientReportedAt,
    this.onboardingSource = 'unknown',
    this.osPermissionLastKnown = 'unknown',
  });

  final bool? preferenceEnabled;
  final String? preferenceUpdatedAt;
  final String onboardingStatus;
  final String onboardingOutcome;
  final String? onboardingCompletedAt;
  final String? lastClientReportedAt;
  final String onboardingSource;
  final String osPermissionLastKnown;

  factory PushNotificationsSecurityState.fromJson(Map<String, dynamic> json) {
    return PushNotificationsSecurityState(
      preferenceEnabled: json['preference_enabled'] == null
          ? null
          : json['preference_enabled'] == true,
      preferenceUpdatedAt: _s(json['preference_updated_at']),
      onboardingStatus: _s(json['onboarding_status']) ?? 'not_started',
      onboardingOutcome: _s(json['onboarding_outcome']) ?? 'unknown',
      onboardingCompletedAt: _s(json['onboarding_completed_at']),
      lastClientReportedAt: _s(json['last_client_reported_at']),
      onboardingSource: _s(json['onboarding_source']) ?? 'unknown',
      osPermissionLastKnown: _s(json['os_permission_last_known']) ?? 'unknown',
    );
  }
}

String? _s(Object? v) {
  if (v == null) return null;
  final t = v.toString().trim();
  return t.isEmpty ? null : t;
}
