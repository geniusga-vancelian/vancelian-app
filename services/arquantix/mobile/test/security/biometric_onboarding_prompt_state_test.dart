import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/features/security/passcode/domain/biometric_onboarding_prompt_state.dart';

void main() {
  test('storageValue / tryParse roundtrip', () {
    for (final s in BiometricOnboardingPromptState.values) {
      expect(BiometricOnboardingPromptState.tryParse(s.storageValue), s);
    }
  });

  test('cancel / inconnu → tryParse null', () {
    expect(BiometricOnboardingPromptState.tryParse(null), isNull);
    expect(BiometricOnboardingPromptState.tryParse(''), isNull);
    expect(BiometricOnboardingPromptState.tryParse('1'), isNull);
  });
}
