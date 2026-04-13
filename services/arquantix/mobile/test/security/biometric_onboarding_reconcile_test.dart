import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/features/profile/application/security_preferences_coordinator.dart';
import 'package:arquantix_news/features/profile/domain/security_preferences_models.dart';
import 'package:arquantix_news/features/security/passcode/domain/biometric_onboarding_prompt_state.dart';

void main() {
  group('reconcileBiometricOnboardingPromptStateForDevice', () {
    test('unavailable + capteur OK → never_seen (réouvre le gate onboarding)', () {
      expect(
        reconcileBiometricOnboardingPromptStateForDevice(
          stored: BiometricOnboardingPromptState.unavailable,
          deviceSupportsBiometric: true,
        ),
        BiometricOnboardingPromptState.neverSeen,
      );
    });

    test('unavailable + capteur non OK → inchangé', () {
      expect(
        reconcileBiometricOnboardingPromptStateForDevice(
          stored: BiometricOnboardingPromptState.unavailable,
          deviceSupportsBiometric: false,
        ),
        BiometricOnboardingPromptState.unavailable,
      );
    });

    test('skipped / enabled / neverSeen → inchangés (même si capteur OK)', () {
      for (final s in [
        BiometricOnboardingPromptState.skipped,
        BiometricOnboardingPromptState.enabled,
        BiometricOnboardingPromptState.neverSeen,
      ]) {
        expect(
          reconcileBiometricOnboardingPromptStateForDevice(
            stored: s,
            deviceSupportsBiometric: true,
          ),
          s,
        );
      }
    });
  });

  group('gate après transition conceptuelle vers never_seen', () {
    test('never_seen + backend incomplet → onboarding bloquant', () {
      final sp = MobileSecurityPreferences.fromJson({
        'biometric': {
          'onboarding_status': 'not_started',
          'onboarding_outcome': 'unknown',
        },
        'push_notifications': {},
        'biometric_unlock_enabled': false,
        'biometric_login_onboarding_completed': false,
        'push_notifications_enabled': false,
        'push_notifications_onboarding_completed': false,
      });
      expect(
        SecurityPreferencesCoordinator.shouldShowBlockingBiometricOnboarding(
          sp,
          localPromptState: BiometricOnboardingPromptState.neverSeen,
        ),
        true,
      );
    });
  });

  group('politique inchangée : skipped / enabled', () {
    test('skipped + backend completed → toujours re-prompt', () {
      final sp = MobileSecurityPreferences.fromJson({
        'biometric': {
          'onboarding_status': 'completed',
          'onboarding_outcome': 'enabled',
        },
        'push_notifications': {},
        'biometric_unlock_enabled': true,
        'biometric_login_onboarding_completed': true,
        'push_notifications_enabled': false,
        'push_notifications_onboarding_completed': false,
      });
      expect(
        SecurityPreferencesCoordinator.shouldShowBlockingBiometricOnboarding(
          sp,
          localPromptState: BiometricOnboardingPromptState.skipped,
        ),
        true,
      );
    });

    test('enabled → jamais bloquer', () {
      final sp = MobileSecurityPreferences.fromJson({
        'biometric': {
          'onboarding_status': 'not_started',
          'onboarding_outcome': 'unknown',
        },
        'push_notifications': {},
        'biometric_unlock_enabled': false,
        'biometric_login_onboarding_completed': false,
        'push_notifications_enabled': false,
        'push_notifications_onboarding_completed': false,
      });
      expect(
        SecurityPreferencesCoordinator.shouldShowBlockingBiometricOnboarding(
          sp,
          localPromptState: BiometricOnboardingPromptState.enabled,
        ),
        false,
      );
    });
  });

  test(
    'doc : absence de chaîne persistée → tryParse null ; '
    'PasscodeService.getBiometricOnboardingPromptState mappe à never_seen',
    () {
      expect(BiometricOnboardingPromptState.tryParse(null), isNull);
    },
  );
}
