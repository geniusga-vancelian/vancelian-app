import 'package:flutter/foundation.dart';

/// Analytics produit — notifications push (onboarding + réglages).
///
/// Fire-and-forget : ne lance pas d’exception vers l’UI. Brancher ici Firebase / autre
/// backend d’événements si besoin ([kDebugMode] garde les logs verbeux en dev).
class PushNotificationsProductAnalytics {
  PushNotificationsProductAnalytics._();

  static void pushOnboardingPromptShown({
    required String source,
    required String currentState,
  }) {
    _emit('push_onboarding_prompt_shown', {
      'source': source,
      'current_state': currentState,
    });
  }

  static void pushOnboardingAction({
    required String source,
    required String action,
    required String permissionStatus,
    required String resultingState,
  }) {
    _emit('push_onboarding_action', {
      'source': source,
      'action': action,
      'permission_status': permissionStatus,
      'resulting_state': resultingState,
    });
  }

  static void pushNotificationsSettingsToggled({
    required bool targetValue,
    required String permissionStatus,
    required bool syncAttempted,
  }) {
    _emit('push_notifications_settings_toggled', {
      'target_value': targetValue,
      'permission_status': permissionStatus,
      'sync_attempted': syncAttempted,
    });
  }

  static void _emit(String name, Map<String, Object?> props) {
    try {
      if (kDebugMode) {
        final tail =
            props.entries.map((e) => '${e.key}=${e.value}').join(' ');
        debugPrint('[analytics] $name ${tail.isEmpty ? '' : '| $tail'}');
      }
    } catch (_) {}
  }
}
