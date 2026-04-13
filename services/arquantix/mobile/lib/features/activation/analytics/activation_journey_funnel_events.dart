import 'package:flutter/foundation.dart';

import '../domain/activation_journey_models.dart';

/// Clé d’étape alignée sur ``stages[].key`` (profil API).
String? activationStepKeyForTargetRoute(String route) {
  switch (route.trim()) {
    case 'registration_resume':
      return 'account_verification';
    case 'deposit':
      return 'first_deposit';
    case 'invest_crypto':
      return 'first_investment';
    default:
      return null;
  }
}

/// Instrumentation funnel activation — **sans PII** dans les payloads.
///
/// En debug : préfixe `[funnel]` ; brancher un backend analytics via un hook global si besoin.
class ActivationJourneyFunnelEvents {
  ActivationJourneyFunnelEvents._();

  static void _emit(String name, [Map<String, Object?> props = const {}]) {
    if (!kDebugMode) return;
    final tail = props.entries.map((e) => '${e.key}=${e.value}').join(', ');
    debugPrint('[funnel] $name${tail.isEmpty ? '' : ' | $tail'}');
  }

  /// L’utilisateur voit l’étape courante du module (next step) — au montage ou changement de focus.
  static void stepViewed({required String stepKey}) {
    _emit('activation_step_viewed', {'step_key': stepKey});
  }

  static void stepClicked({required String stepKey, required String targetRoute}) {
    _emit('activation_step_clicked', {
      'step_key': stepKey,
      'target_route': targetRoute,
    });
  }

  /// Détecté après rafraîchissement profil : une étape passe à ``completed``.
  static void stepCompleted({required String stepKey}) {
    _emit('activation_step_completed', {'step_key': stepKey});
  }

  /// Les trois étapes sont franchies (``activation_complete``).
  static void journeyCompleted() {
    _emit('activation_journey_completed', const {});
  }

  /// Compare deux instantanés de parcours (retour Home / pull-to-refresh).
  static void emitProgressDiff(ActivationJourney? previous, ActivationJourney current) {
    if (previous == null) return;
    for (var i = 0; i < current.stages.length; i++) {
      if (i >= previous.stages.length) break;
      final s = current.stages[i];
      final o = previous.stages[i];
      if (o.key != s.key) continue;
      if (o.uxStatus != ActivationStageUxStatus.completed &&
          s.uxStatus == ActivationStageUxStatus.completed) {
        stepCompleted(stepKey: s.key);
      }
    }
    if (!previous.activationComplete && current.activationComplete) {
      journeyCompleted();
    }
  }
}
