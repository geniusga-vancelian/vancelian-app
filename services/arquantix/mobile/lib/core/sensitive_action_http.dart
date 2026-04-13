/// Codes `detail["code"]` attendus (alignés backend).
/// Interprétation des réponses API pour l’auth continue / actions sensibles
/// (source de vérité : FastAPI `session_intelligence_dependencies`).
abstract final class SensitiveActionHttpCodes {
  static const reauthRequired = 'session.reauth_required';
  static const stepUpRequired = 'session.step_up_required';
  static const continuousAuthDenied = 'session.continuous_auth_denied';
}

/// Indications `detail["next_step"]` (alignées [next_step_hint] côté API).
abstract final class SensitiveActionNextStep {
  static const fullReauth = 'full_reauth';
  static const otpOrPasskey = 'otp_or_passkey';
  static const biometricOrPasscode = 'biometric_or_passcode';
  static const otpOrPasskeyThenBiometric = 'otp_or_passkey_then_biometric';
  static const none = 'none';
}

/// Extrait code / next_step depuis un corps d’erreur JSON déjà décodé (ex. Dio).
SensitiveActionErrorShape? parseSensitiveActionError(Object? detail) {
  if (detail is! Map) return null;
  final m = Map<String, dynamic>.from(
    detail.map((k, v) => MapEntry(k.toString(), v)),
  );
  final code = m['code']?.toString();
  if (code == null || code.isEmpty) return null;
  return SensitiveActionErrorShape(
    code: code,
    message: m['message']?.toString(),
    actionKey: m['action_key']?.toString(),
    nextStep: m['next_step']?.toString(),
    reasonCodes: (m['reason_codes'] is List)
        ? (m['reason_codes'] as List).map((e) => e.toString()).toList()
        : const [],
    policy: m['policy'] is Map<String, dynamic>
        ? Map<String, dynamic>.from(m['policy'] as Map)
        : null,
    uxMessage: m['ux_message']?.toString(),
    uxTone: m['ux_tone']?.toString(),
    uxActionLabel: m['ux_action_label']?.toString(),
    uxContext: m['ux_context']?.toString(),
  );
}

class SensitiveActionErrorShape {
  const SensitiveActionErrorShape({
    required this.code,
    this.message,
    this.actionKey,
    this.nextStep,
    this.reasonCodes = const [],
    this.policy,
    this.uxMessage,
    this.uxTone,
    this.uxActionLabel,
    this.uxContext,
  });

  final String code;
  final String? message;
  final String? actionKey;
  final String? nextStep;
  final List<String> reasonCodes;
  final Map<String, dynamic>? policy;

  /// Phase 5A — texte court non technique ; préférer à l’affichage utilisateur.
  final String? uxMessage;

  /// `soft` | `warning` | `critical` — style d’urgence (modal vs plein écran, etc.).
  final String? uxTone;

  /// Libellé bouton principal suggéré (CTA).
  final String? uxActionLabel;

  /// `withdrawal` | `data_access` | `security_change`
  final String? uxContext;

  bool get requiresFullReauth => code == SensitiveActionHttpCodes.reauthRequired;
  bool get requiresStepUp => code == SensitiveActionHttpCodes.stepUpRequired;

  /// Message à montrer à l’utilisateur (UX Phase 5A si présent, sinon message API).
  String get displayMessage => (uxMessage != null && uxMessage!.isNotEmpty)
      ? uxMessage!
      : (message ?? '');
}
