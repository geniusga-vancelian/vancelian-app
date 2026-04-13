import 'dart:convert';

import 'passcode_storage_keys.dart';

/// Suffixe stable pour les clés SecureStorage (évite caractères problématiques dans `sub`).
String passcodeBindingKeySuffix(String jwtSub) {
  return base64Url.encode(utf8.encode(jwtSub)).replaceAll('=', '');
}

/// Ensemble de clés stockage pour un passcode : soit **legacy** (sans JWT `sub`),
/// soit **par utilisateur** (`sub` du access token).
final class PasscodeUserKeys {
  const PasscodeUserKeys._({
    required this.passcodeHashB64,
    required this.deviceSaltB64,
    required this.failedAttempts,
    required this.lockUntilMs,
    required this.lockoutTier,
    required this.lockoutEvents,
    required this.biometricEnabled,
    required this.biometricOnboardingPromptState,
    required this.biometricOnboardingHandledLegacy,
    required this.pushOnboardingPromptState,
    required this.pushNotificationsPreferenceEnabled,
    required this.lastPushOnboardingPromptAtMs,
    required this.clientGreetingFirstName,
  });

  final String passcodeHashB64;
  final String deviceSaltB64;
  final String failedAttempts;
  final String lockUntilMs;
  final String lockoutTier;
  final String lockoutEvents;
  final String biometricEnabled;
  final String biometricOnboardingPromptState;
  final String biometricOnboardingHandledLegacy;
  final String pushOnboardingPromptState;
  final String pushNotificationsPreferenceEnabled;
  final String lastPushOnboardingPromptAtMs;

  /// Prénom d’accueil (SecureStorage, même coffre que le passcode pour ce `sub`).
  final String clientGreetingFirstName;

  /// `jwtSub` : claim `sub` du JWT ; `null` → clés globales historiques (un seul pool).
  factory PasscodeUserKeys.forBinding(String? jwtSub) {
    if (jwtSub == null || jwtSub.isEmpty) {
      return const PasscodeUserKeys._(
        passcodeHashB64: PasscodeStorageKeys.passcodeHashB64,
        deviceSaltB64: PasscodeStorageKeys.deviceSaltB64,
        failedAttempts: PasscodeStorageKeys.failedAttempts,
        lockUntilMs: PasscodeStorageKeys.lockUntilMs,
        lockoutTier: PasscodeStorageKeys.lockoutTier,
        lockoutEvents: PasscodeStorageKeys.lockoutEvents,
        biometricEnabled: PasscodeStorageKeys.biometricEnabled,
        biometricOnboardingPromptState:
            PasscodeStorageKeys.biometricOnboardingPromptState,
        biometricOnboardingHandledLegacy:
            PasscodeStorageKeys.biometricOnboardingHandledLegacy,
        pushOnboardingPromptState: PasscodeStorageKeys.pushOnboardingPromptState,
        pushNotificationsPreferenceEnabled:
            PasscodeStorageKeys.pushNotificationsPreferenceEnabled,
        lastPushOnboardingPromptAtMs:
            PasscodeStorageKeys.lastPushOnboardingPromptAtMs,
        clientGreetingFirstName: PasscodeStorageKeys.clientGreetingFirstNameLegacy,
      );
    }
    final sfx = passcodeBindingKeySuffix(jwtSub);
    return PasscodeUserKeys._(
      passcodeHashB64: 'arqx.sec.passcode_hash_b64.u.$sfx',
      deviceSaltB64: 'arqx.sec.device_salt_b64.u.$sfx',
      failedAttempts: 'arqx.sec.failed_attempts.u.$sfx',
      lockUntilMs: 'arqx.sec.lock_until_ms.u.$sfx',
      lockoutTier: 'arqx.sec.lockout_tier.u.$sfx',
      lockoutEvents: 'arqx.sec.lockout_events.u.$sfx',
      biometricEnabled: 'arqx.sec.biometric_enabled.u.$sfx',
      biometricOnboardingPromptState:
          'arqx.sec.biometric_onboarding_prompt_state.u.$sfx',
      biometricOnboardingHandledLegacy:
          'arqx.sec.biometric_onboarding_handled.u.$sfx',
      pushOnboardingPromptState:
          'arqx.sec.push_onboarding_prompt_state.u.$sfx',
      pushNotificationsPreferenceEnabled:
          'arqx.sec.push_notifications_pref_enabled.u.$sfx',
      lastPushOnboardingPromptAtMs:
          'arqx.sec.last_push_onboarding_prompt_at_ms.u.$sfx',
      clientGreetingFirstName: 'arqx.sec.client_greeting_first_name.u.$sfx',
    );
  }
}
