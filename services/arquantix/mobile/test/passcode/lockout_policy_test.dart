import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/features/security/passcode/domain/lockout_policy.dart';

void main() {
  test('LockoutPolicy durations escalate', () {
    expect(LockoutPolicy.lockDurationForTier(0), const Duration(seconds: 30));
    expect(LockoutPolicy.lockDurationForTier(1), const Duration(minutes: 5));
    expect(LockoutPolicy.lockDurationForTier(2), const Duration(hours: 1));
    expect(LockoutPolicy.lockDurationForTier(99), const Duration(hours: 1));
  });

  test('maxAttemptsBeforeLock is 5', () {
    expect(LockoutPolicy.maxAttemptsBeforeLock, 5);
  });
}
