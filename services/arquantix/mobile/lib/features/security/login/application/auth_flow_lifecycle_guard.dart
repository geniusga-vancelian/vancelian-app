import 'package:flutter/widgets.dart';

/// Seuil après lequel un retour depuis [AppLifecycleState.paused] invalide le flux auth en cours.
/// Les tests peuvent mettre [Duration.zero] ou 1 ms.
class AuthFlowLifecycleConfig {
  AuthFlowLifecycleConfig._();

  static Duration backgroundStaleThreshold = const Duration(minutes: 5);
}

/// Logique pure pour les tests (sans [WidgetsBinding]).
bool authFlowShouldInvalidateAfterBackground({
  required DateTime? pausedAt,
  required DateTime now,
  required Duration threshold,
}) {
  if (pausedAt == null) return false;
  return now.difference(pausedAt) >= threshold;
}

/// Délègue [WidgetsBindingObserver] à une classe interne (évite les conflits d’API Flutter
/// sur [WidgetsBindingObserver] avec les mixins [State]).
class AuthFlowLifecycleObserver with WidgetsBindingObserver {
  AuthFlowLifecycleObserver({required this.onStaleAfterBackground});

  final void Function({required DateTime pausedAt}) onStaleAfterBackground;

  DateTime? _pausedAt;

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused) {
      _pausedAt = DateTime.now();
    } else if (state == AppLifecycleState.resumed) {
      final p = _pausedAt;
      _pausedAt = null;
      if (p != null &&
          authFlowShouldInvalidateAfterBackground(
            pausedAt: p,
            now: DateTime.now(),
            threshold: AuthFlowLifecycleConfig.backgroundStaleThreshold,
          )) {
        onStaleAfterBackground(pausedAt: p);
      }
    }
  }
}
