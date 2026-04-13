import 'package:flutter_test/flutter_test.dart';

import 'package:arquantix_news/features/auth/orchestrator/login_orchestrator.dart';

void main() {
  group('LoginOrchestratorResult.fromSmsStartResponse', () {
    test('blocked → route blocked', () {
      final r = LoginOrchestratorResult.fromSmsStartResponse(
        {
          'orchestrator': {
            'blocked': true,
            'reason_codes': ['account_locked'],
            'ui_variant': 'blocked',
          },
        },
        phoneE164: '+33123456789',
        passkeyEmail: 'a@b.c',
      );
      expect(r.route, LoginOrchestratorRoute.blocked);
      expect(r.uiVariant, 'blocked');
    });

    test('passkey + auto + email → fast lane', () {
      final r = LoginOrchestratorResult.fromSmsStartResponse(
        {
          'orchestrator': {
            'primary_method': 'passkey',
            'auto_trigger_passkey': true,
            'fallback_methods': ['otp_sms'],
            'ui_variant': 'fast_lane',
          },
        },
        phoneE164: '+33123456789',
        passkeyEmail: 'user@example.com',
      );
      expect(r.route, LoginOrchestratorRoute.fastLanePasskey);
      expect(r.uiVariant, 'fast_lane');
      expect(r.fallbackOptions, ['otp_sms']);
    });

    test('passkey + auto sans email → standard OTP', () {
      final r = LoginOrchestratorResult.fromSmsStartResponse(
        {
          'orchestrator': {
            'primary_method': 'passkey',
            'auto_trigger_passkey': true,
            'ui_variant': 'fast_lane',
          },
        },
        phoneE164: '+33123456789',
        passkeyEmail: null,
      );
      expect(r.route, LoginOrchestratorRoute.standardOtp);
    });

    test('step_up → cautious OTP', () {
      final r = LoginOrchestratorResult.fromSmsStartResponse(
        {
          'orchestrator': {
            'primary_method': 'otp_sms',
            'step_up_required': true,
            'ui_variant': 'standard',
          },
        },
        phoneE164: '+33123456789',
        passkeyEmail: null,
      );
      expect(r.route, LoginOrchestratorRoute.cautiousOtp);
    });

    test('ui_variant cautious → cautious OTP', () {
      final r = LoginOrchestratorResult.fromSmsStartResponse(
        {
          'orchestrator': {
            'primary_method': 'otp_sms',
            'ui_variant': 'cautious',
          },
        },
        phoneE164: '+33123456789',
        passkeyEmail: null,
      );
      expect(r.route, LoginOrchestratorRoute.cautiousOtp);
    });

    test('sans orchestrator : recommended passkey + email → fast lane', () {
      final r = LoginOrchestratorResult.fromSmsStartResponse(
        {
          'recommended_auth_method': 'passkey',
        },
        phoneE164: '+33123456789',
        passkeyEmail: 'u@x.y',
      );
      expect(r.route, LoginOrchestratorRoute.fastLanePasskey);
    });

    test('sans orchestrator : défaut standard OTP', () {
      final r = LoginOrchestratorResult.fromSmsStartResponse(
        {},
        phoneE164: '+33123456789',
        passkeyEmail: null,
      );
      expect(r.route, LoginOrchestratorRoute.standardOtp);
    });
  });
}
