import 'package:arquantix_news/features/security/passcode/domain/resume_lock_logic.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('no paused time => no relock', () {
    expect(
      shouldRequireResumeUnlock(
        pausedAt: null,
        now: DateTime(2026, 1, 2, 12, 0, 30),
        threshold: const Duration(seconds: 45),
      ),
      isFalse,
    );
  });

  test('under threshold => no relock', () {
    final paused = DateTime(2026, 1, 2, 12, 0, 0);
    final now = paused.add(const Duration(seconds: 30));
    expect(
      shouldRequireResumeUnlock(
        pausedAt: paused,
        now: now,
        threshold: const Duration(seconds: 45),
      ),
      isFalse,
    );
  });

  test('at or over threshold => relock', () {
    final paused = DateTime(2026, 1, 2, 12, 0, 0);
    final now = paused.add(const Duration(seconds: 45));
    expect(
      shouldRequireResumeUnlock(
        pausedAt: paused,
        now: now,
        threshold: const Duration(seconds: 45),
      ),
      isTrue,
    );
  });
}
