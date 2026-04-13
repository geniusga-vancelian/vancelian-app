import 'package:arquantix_news/features/security/login/application/auth_flow_lifecycle_guard.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('authFlowShouldInvalidateAfterBackground', () {
    test('false si jamais en pause', () {
      expect(
        authFlowShouldInvalidateAfterBackground(
          pausedAt: null,
          now: DateTime(2025, 1, 1, 12),
          threshold: const Duration(minutes: 5),
        ),
        false,
      );
    });

    test('true si durée >= seuil', () {
      final p = DateTime(2025, 1, 1, 12);
      expect(
        authFlowShouldInvalidateAfterBackground(
          pausedAt: p,
          now: p.add(const Duration(minutes: 6)),
          threshold: const Duration(minutes: 5),
        ),
        true,
      );
    });

    test('false si durée < seuil', () {
      final p = DateTime(2025, 1, 1, 12);
      expect(
        authFlowShouldInvalidateAfterBackground(
          pausedAt: p,
          now: p.add(const Duration(minutes: 1)),
          threshold: const Duration(minutes: 5),
        ),
        false,
      );
    });
  });
}
