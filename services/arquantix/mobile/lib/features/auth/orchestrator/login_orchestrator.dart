import 'package:flutter/material.dart';

import '../../security/login/presentation/login_auto_auth_screen.dart';
import '../../security/login/presentation/login_otp_screen.dart';
import 'login_blocked_screen.dart';

/// Route cible après décision backend (Adaptive Auth).
enum LoginOrchestratorRoute {
  fastLanePasskey,
  standardOtp,
  cautiousOtp,
  blocked,
}

/// Résultat d’orchestration — navigation + options de repli.
class LoginOrchestratorResult {
  LoginOrchestratorResult({
    required this.route,
    this.orchestratorPayload,
    this.fallbackOptions = const [],
  });

  final LoginOrchestratorRoute route;
  final Map<String, dynamic>? orchestratorPayload;
  final List<String> fallbackOptions;

  String get uiVariant =>
      (orchestratorPayload?['ui_variant'] as String?) ?? 'standard';

  /// Interprète la réponse ``POST /auth/login/sms/start`` (champ optionnel ``orchestrator``).
  factory LoginOrchestratorResult.fromSmsStartResponse(
    Map<String, dynamic> data, {
    required String phoneE164,
    required String? passkeyEmail,
  }) {
    final orc = data['orchestrator'];
    if (orc is Map<String, dynamic>) {
      if (orc['blocked'] == true) {
        return LoginOrchestratorResult(
          route: LoginOrchestratorRoute.blocked,
          orchestratorPayload: orc,
          fallbackOptions: const [],
        );
      }
      final primary = orc['primary_method'] as String?;
      final auto = orc['auto_trigger_passkey'] == true;
      final fb = (orc['fallback_methods'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [];
      if (primary == 'passkey' &&
          auto &&
          passkeyEmail != null &&
          passkeyEmail.isNotEmpty) {
        return LoginOrchestratorResult(
          route: LoginOrchestratorRoute.fastLanePasskey,
          orchestratorPayload: orc,
          fallbackOptions: fb,
        );
      }
      final variant = orc['ui_variant'] as String? ?? 'standard';
      if (variant == 'cautious' || orc['step_up_required'] == true) {
        return LoginOrchestratorResult(
          route: LoginOrchestratorRoute.cautiousOtp,
          orchestratorPayload: orc,
          fallbackOptions: fb,
        );
      }
      return LoginOrchestratorResult(
        route: LoginOrchestratorRoute.standardOtp,
        orchestratorPayload: orc,
        fallbackOptions: fb,
      );
    }

    final rec = data['recommended_auth_method'] as String?;
    final email = passkeyEmail?.trim() ?? '';
    final usePasskey = rec == 'passkey' && email.isNotEmpty;
    if (usePasskey) {
      return LoginOrchestratorResult(
        route: LoginOrchestratorRoute.fastLanePasskey,
        fallbackOptions: const ['otp_sms'],
      );
    }
    return LoginOrchestratorResult(
      route: LoginOrchestratorRoute.standardOtp,
      fallbackOptions: const ['passkey', 'otp_sms'],
    );
  }

  /// Pousse l’écran approprié ; retour ``true`` si login réussi.
  Future<bool?> pushFlow(
    BuildContext context, {
    required String phoneE164,
    required Map<String, dynamic> smsStartResult,
    required String passkeyEmail,
  }) {
    switch (route) {
      case LoginOrchestratorRoute.blocked:
        final codes = (orchestratorPayload?['reason_codes'] as List<dynamic>?)
                ?.map((e) => e.toString())
                .toList() ??
            [];
        return Navigator.of(context).push<bool>(
          MaterialPageRoute<bool>(
            builder: (_) => LoginBlockedScreen(reasonCodes: codes),
          ),
        );
      case LoginOrchestratorRoute.fastLanePasskey:
        if (passkeyEmail.isEmpty) {
          return Navigator.of(context).push<bool>(
            MaterialPageRoute<bool>(
              builder: (_) => LoginOtpScreen(
                phoneE164: phoneE164,
                smsStartResult: smsStartResult,
                resumeRegistrationHintFromSms:
                    (smsStartResult['resume_registration_hint'] as bool?) ??
                        false,
              ),
            ),
          );
        }
        final fast = uiVariant == 'fast_lane';
        return Navigator.of(context).push<bool>(
          MaterialPageRoute<bool>(
            builder: (_) => LoginAutoAuthScreen(
              phoneE164: phoneE164,
              smsStartResult: smsStartResult,
              passkeyEmail: passkeyEmail,
              headline: fast
                  ? 'Connexion sécurisée en cours…'
                  : null,
              subtitle: fast
                  ? 'Nous utilisons votre passkey sur cet appareil.'
                  : null,
            ),
          ),
        );
      case LoginOrchestratorRoute.cautiousOtp:
        return Navigator.of(context).push<bool>(
          MaterialPageRoute<bool>(
            builder: (_) => LoginOtpScreen(
              phoneE164: phoneE164,
              smsStartResult: smsStartResult,
              extraSecurityMessage:
                  'Pour votre sécurité, nous vérifions ce code sur cet appareil.',
              resumeRegistrationHintFromSms:
                  (smsStartResult['resume_registration_hint'] as bool?) ??
                      false,
            ),
          ),
        );
      case LoginOrchestratorRoute.standardOtp:
        return Navigator.of(context).push<bool>(
          MaterialPageRoute<bool>(
            builder: (_) => LoginOtpScreen(
              phoneE164: phoneE164,
              smsStartResult: smsStartResult,
              resumeRegistrationHintFromSms:
                  (smsStartResult['resume_registration_hint'] as bool?) ??
                      false,
            ),
          ),
        );
    }
  }
}
