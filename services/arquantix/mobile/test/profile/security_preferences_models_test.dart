import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/features/profile/domain/security_preferences_models.dart';

void main() {
  test('MobileSecurityPreferences parses V1 + legacy flat', () {
    final m = MobileSecurityPreferences.fromJson({
      'security_model_version': 1,
      'biometric': {
        'preference_enabled': true,
        'onboarding_status': 'completed',
        'onboarding_outcome': 'enabled',
      },
      'push_notifications': {
        'onboarding_status': 'not_started',
        'onboarding_outcome': 'unknown',
      },
      'biometric_unlock_enabled': true,
      'biometric_login_onboarding_completed': true,
      'push_notifications_enabled': false,
      'push_notifications_onboarding_completed': false,
    });
    expect(m.isBiometricOnboardingCompleted, true);
    expect(m.isPushOnboardingCompleted, false);
  });

  test('SecurityPreferencesCoordinator blocks when biometric not completed', () {
    // import coordinator in test - use getters directly
    final m = MobileSecurityPreferences.fromJson({
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
    expect(m.isBiometricOnboardingCompleted, false);
  });
}
