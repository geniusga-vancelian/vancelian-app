import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/features/profile/data/patch_security_preferences_result.dart';
import 'package:arquantix_news/features/profile/data/security_preferences_patch_feedback.dart';

void main() {
  group('userMessageForPatchSecurityPreferencesFailure', () {
    test('sessionMissing', () {
      final m = userMessageForPatchSecurityPreferencesFailure(
        const PatchSecurityPreferencesFailure(
          PatchSecurityPreferencesFailureKind.sessionMissing,
        ),
      );
      expect(m, contains('Session'));
      expect(m, contains('automatiquement'));
    });

    test('endpointNotFound', () {
      final m = userMessageForPatchSecurityPreferencesFailure(
        const PatchSecurityPreferencesFailure(
          PatchSecurityPreferencesFailureKind.endpointNotFound,
        ),
      );
      expect(m, contains('environnement'));
    });

    test('unauthorized vs network différenciés', () {
      final u = userMessageForPatchSecurityPreferencesFailure(
        const PatchSecurityPreferencesFailure(
          PatchSecurityPreferencesFailureKind.unauthorized,
        ),
      );
      final n = userMessageForPatchSecurityPreferencesFailure(
        const PatchSecurityPreferencesFailure(
          PatchSecurityPreferencesFailureKind.network,
        ),
      );
      expect(u, contains('Session expirée'));
      expect(n, contains('réseau'));
      expect(u, isNot(equals(n)));
    });
  });
}
