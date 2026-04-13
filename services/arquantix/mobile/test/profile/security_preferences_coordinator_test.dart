import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/features/profile/application/security_preferences_coordinator.dart';
import 'package:arquantix_news/features/profile/domain/security_preferences_models.dart';
import 'package:arquantix_news/features/security/passcode/domain/biometric_onboarding_prompt_state.dart';

MobileSecurityPreferences _prefs({
  required bool bioCompleted,
}) {
  return MobileSecurityPreferences.fromJson({
    'biometric': {
      'onboarding_status': bioCompleted ? 'completed' : 'not_started',
      'onboarding_outcome': bioCompleted ? 'enabled' : 'unknown',
    },
    'push_notifications': {},
    'biometric_unlock_enabled': bioCompleted,
    'biometric_login_onboarding_completed': bioCompleted,
    'push_notifications_enabled': false,
    'push_notifications_onboarding_completed': false,
  });
}

void main() {
  group('shouldShowBlockingBiometricOnboarding', () {
    test('enabled → jamais bloquer', () {
      final sp = _prefs(bioCompleted: false);
      expect(
        SecurityPreferencesCoordinator.shouldShowBlockingBiometricOnboarding(
          sp,
          localPromptState: BiometricOnboardingPromptState.enabled,
        ),
        false,
      );
    });

    test('skipped → bloquer même si backend dit completed (re-invite)', () {
      final sp = _prefs(bioCompleted: true);
      expect(sp.isBiometricOnboardingCompleted, true);
      expect(
        SecurityPreferencesCoordinator.shouldShowBlockingBiometricOnboarding(
          sp,
          localPromptState: BiometricOnboardingPromptState.skipped,
        ),
        true,
      );
    });

    test('unavailable → ne pas bloquer', () {
      final sp = _prefs(bioCompleted: false);
      expect(
        SecurityPreferencesCoordinator.shouldShowBlockingBiometricOnboarding(
          sp,
          localPromptState: BiometricOnboardingPromptState.unavailable,
        ),
        false,
      );
    });

    test('neverSeen → suit le backend (non complété → bloquer)', () {
      final sp = _prefs(bioCompleted: false);
      expect(
        SecurityPreferencesCoordinator.shouldShowBlockingBiometricOnboarding(
          sp,
          localPromptState: BiometricOnboardingPromptState.neverSeen,
        ),
        true,
      );
    });

    test('neverSeen + backend complété → ne pas bloquer', () {
      final sp = _prefs(bioCompleted: true);
      expect(
        SecurityPreferencesCoordinator.shouldShowBlockingBiometricOnboarding(
          sp,
          localPromptState: BiometricOnboardingPromptState.neverSeen,
        ),
        false,
      );
    });

    test('profil null → ne pas bloquer', () {
      expect(
        SecurityPreferencesCoordinator.shouldShowBlockingBiometricOnboarding(
          null,
          localPromptState: BiometricOnboardingPromptState.neverSeen,
        ),
        false,
      );
    });
  });
}
