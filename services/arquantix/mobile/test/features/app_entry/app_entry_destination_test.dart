import 'package:flutter_test/flutter_test.dart';

import 'package:arquantix_news/features/app_entry/domain/app_entry_destination.dart';
import 'package:arquantix_news/features/app_entry/domain/app_entry_ux_state.dart';

void main() {
  group('resolveAppEntryDestination', () {
    test('sans jetons → login0', () {
      expect(
        resolveAppEntryDestination(
          hasStoredTokens: false,
          sessionStillValid: false,
          passcodeConfigured: false,
        ),
        AppEntryDestination.login0,
      );
    });

    test('jetons mais session invalide → login0', () {
      expect(
        resolveAppEntryDestination(
          hasStoredTokens: true,
          sessionStillValid: false,
          passcodeConfigured: true,
        ),
        AppEntryDestination.login0,
      );
    });

    test('session valide sans PIN → login0 (pas de reprise création PIN au cold start)', () {
      expect(
        resolveAppEntryDestination(
          hasStoredTokens: true,
          sessionStillValid: true,
          passcodeConfigured: false,
        ),
        AppEntryDestination.login0,
      );
    });

    test('session valide + PIN → secureGate', () {
      expect(
        resolveAppEntryDestination(
          hasStoredTokens: true,
          sessionStillValid: true,
          passcodeConfigured: true,
        ),
        AppEntryDestination.secureGate,
      );
    });
  });

  group('destinationForUxState', () {
    test('unlockingLocalAccess → null', () {
      expect(destinationForUxState(AppEntryUxState.unlockingLocalAccess), isNull);
    });
  });
}
