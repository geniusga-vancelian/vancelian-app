import 'package:flutter/foundation.dart';

/// Événements de sécurité **légers** pour audit / analytics futurs (pas de PII dans les logs).
///
/// Brancher ici un backend analytics si besoin ; par défaut : [debugPrint] en debug uniquement.
class PostAuthFlowSecurityEvents {
  PostAuthFlowSecurityEvents._();

  static void _emit(String name, [Map<String, Object?> props = const {}]) {
    if (!kDebugMode) return;
    final tail = props.entries.map((e) => '${e.key}=${e.value}').join(', ');
    debugPrint('[security_event] $name${tail.isEmpty ? '' : ' | $tail'}');
  }

  /// Session valide mais setup PIN non terminé au cold start → session révoquée / effacée.
  static void interruptedSensitiveFlowRevoked({required String reason}) {
    _emit('auth.interrupted_sensitive_flow_revoked', {'reason': reason});
  }

  /// Politique refuse une reprise automatique (documentation / futur hook UI).
  static void postAuthFlowResumeDenied({
    required String flow,
    required String cause,
  }) {
    _emit('auth.post_auth_flow_resume_denied', {'flow': flow, 'cause': cause});
  }

  /// Continuation attendue dans la même exécution (réservé — éviter spam).
  static void postAuthFlowResumedSameExecution({required String flow}) {
    _emit('auth.post_auth_flow_resumed_same_execution', {'flow': flow});
  }

  /// Changement de compte JWT `sub` détecté à [SessionService.storeTokens] (pas de valeur `sub` loggée).
  static void postAuthFlowInvalidatedOnUserSwitch({
    required int previousSubLength,
    required int newSubLength,
  }) {
    _emit('auth.post_auth_flow_invalidated_on_user_switch', {
      'prev_sub_len': previousSubLength,
      'new_sub_len': newSubLength,
    });
  }

  /// OTP SMS/e-mail : flux invalidé après background prolongé (seuil ``AuthFlowLifecycleConfig``).
  static void otpFlowInvalidatedOnResume({required int backgroundSeconds}) {
    _emit('auth.otp_flow_invalidated_on_resume', {'bg_sec': backgroundSeconds});
  }

  /// Passkey / écran fallback : interruption ou background prolongé.
  static void passkeyFlowInvalidatedOnResume({required int backgroundSeconds}) {
    _emit('auth.passkey_flow_invalidated_on_resume', {'bg_sec': backgroundSeconds});
  }
}
