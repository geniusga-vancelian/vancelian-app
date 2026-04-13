import 'package:flutter_test/flutter_test.dart';
import 'package:permission_handler/permission_handler.dart';

import 'package:arquantix_news/features/profile/application/security_preferences_coordinator.dart';
import 'package:arquantix_news/features/security/onboarding/notification_permission_analytics_status.dart';
import 'package:arquantix_news/features/security/onboarding/push_notifications_onboarding_kind.dart';
import 'package:arquantix_news/features/security/passcode/data/passcode_service.dart';
import 'package:arquantix_news/features/security/passcode/domain/push_notification_onboarding_prompt_state.dart';

void main() {
  group('PushNotificationOnboardingPromptState', () {
    test('tryParse round-trip', () {
      for (final v in PushNotificationOnboardingPromptState.values) {
        expect(
          PushNotificationOnboardingPromptState.tryParse(v.storageValue),
          v,
        );
      }
      expect(PushNotificationOnboardingPromptState.tryParse(null), isNull);
      expect(PushNotificationOnboardingPromptState.tryParse(''), isNull);
    });
  });

  group('PasscodeService automatic push cooldown', () {
    test('null last → pas dans le cooldown', () {
      expect(
        PasscodeService.isWithinAutomaticPushOnboardingCooldown(
          null,
          DateTime(2026, 6, 1),
        ),
        isFalse,
      );
    });

    test('moins de 24h → cooldown actif', () {
      final last = DateTime(2026, 6, 1, 10);
      final now = DateTime(2026, 6, 1, 12);
      expect(
        PasscodeService.isWithinAutomaticPushOnboardingCooldown(last, now),
        isTrue,
      );
    });

    test('après 24h → plus de cooldown', () {
      final last = DateTime(2026, 6, 1, 10);
      final now = last.add(const Duration(hours: 25));
      expect(
        PasscodeService.isWithinAutomaticPushOnboardingCooldown(last, now),
        isFalse,
      );
    });
  });

  group('SecurityPreferencesCoordinator push onboarding', () {
    test('registration : offer uniquement si neverSeen', () {
      expect(
        SecurityPreferencesCoordinator.shouldOfferRegistrationPushOnboarding(
          PushNotificationOnboardingPromptState.neverSeen,
        ),
        isTrue,
      );
      expect(
        SecurityPreferencesCoordinator.shouldOfferRegistrationPushOnboarding(
          PushNotificationOnboardingPromptState.skippedRegistration,
        ),
        isFalse,
      );
      expect(
        SecurityPreferencesCoordinator.shouldOfferRegistrationPushOnboarding(
          PushNotificationOnboardingPromptState.enabled,
        ),
        isFalse,
      );
    });

    test('registration + cooldown actif → pas d’offre', () {
      final last = DateTime(2026, 6, 1, 10);
      final now = DateTime(2026, 6, 1, 11);
      expect(
        SecurityPreferencesCoordinator.shouldOfferRegistrationPushOnboarding(
          PushNotificationOnboardingPromptState.neverSeen,
          lastAutomaticPromptAt: last,
          now: now,
        ),
        isFalse,
      );
    });

    test('registration + cooldown expiré → offre', () {
      final last = DateTime(2026, 6, 1, 10);
      final now = last.add(const Duration(hours: 25));
      expect(
        SecurityPreferencesCoordinator.shouldOfferRegistrationPushOnboarding(
          PushNotificationOnboardingPromptState.neverSeen,
          lastAutomaticPromptAt: last,
          now: now,
        ),
        isTrue,
      );
    });

    test('re-login : offer uniquement si skippedRegistration', () {
      expect(
        SecurityPreferencesCoordinator.shouldOfferReloginPushOnboarding(
          PushNotificationOnboardingPromptState.skippedRegistration,
        ),
        isTrue,
      );
      expect(
        SecurityPreferencesCoordinator.shouldOfferReloginPushOnboarding(
          PushNotificationOnboardingPromptState.skippedFirstRelogin,
        ),
        isFalse,
      );
      expect(
        SecurityPreferencesCoordinator.shouldOfferReloginPushOnboarding(
          PushNotificationOnboardingPromptState.enabled,
        ),
        isFalse,
      );
    });

    test(
      're-login : ignore le cooldown 24h (première montée shell après skip inscription)',
      () {
      expect(
        SecurityPreferencesCoordinator.shouldOfferReloginPushOnboarding(
          PushNotificationOnboardingPromptState.skippedRegistration,
        ),
        isTrue,
      );
    });

    test('shouldOfferPostAuthInitialPushOnboarding = alias de registration', () {
      expect(
        SecurityPreferencesCoordinator.shouldOfferPostAuthInitialPushOnboarding(
          PushNotificationOnboardingPromptState.neverSeen,
        ),
        SecurityPreferencesCoordinator.shouldOfferRegistrationPushOnboarding(
          PushNotificationOnboardingPromptState.neverSeen,
        ),
      );
    });
  });

  group('NotificationPermissionAnalyticsStatus', () {
    test('mapping permission_handler', () {
      expect(
        NotificationPermissionAnalyticsStatus.fromPermissionStatus(
          PermissionStatus.granted,
        ),
        NotificationPermissionAnalyticsStatus.granted,
      );
      expect(
        NotificationPermissionAnalyticsStatus.fromPermissionStatus(
          PermissionStatus.permanentlyDenied,
        ),
        NotificationPermissionAnalyticsStatus.permanentlyDenied,
      );
      expect(
        NotificationPermissionAnalyticsStatus.fromPermissionStatus(
          PermissionStatus.provisional,
        ),
        NotificationPermissionAnalyticsStatus.provisional,
      );
    });
  });

  group('PushOnboardingCopy', () {
    test('titres distincts par kind', () {
      expect(
        PushOnboardingCopy.title(PushNotificationsOnboardingKind.registration),
        'Restez informé en temps réel',
      );
      expect(
        PushOnboardingCopy.title(PushNotificationsOnboardingKind.reloginReprompt),
        'Activez vos notifications importantes',
      );
    });

    test('CTA principal relogin', () {
      expect(
        PushOnboardingCopy.primaryCta(
          PushNotificationsOnboardingKind.reloginReprompt,
        ),
        'Activer maintenant',
      );
    });
  });
}
