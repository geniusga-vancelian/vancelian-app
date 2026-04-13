import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/core/sensitive_action_http.dart';

void main() {
  test('parseSensitiveActionError maps Phase 5A ux fields', () {
    final detail = <String, dynamic>{
      'code': 'session.step_up_required',
      'message': 'Vérification supplémentaire requise (OTP / passkey).',
      'action_key': 'view_sensitive_data',
      'reason_codes': ['recent_auth_required'],
      'next_step': 'otp_or_passkey',
      'policy': <String, dynamic>{},
      'ux_message': 'Confirmez votre identité pour accéder à ces informations.',
      'ux_tone': 'soft',
      'ux_action_label': 'Confirmer',
      'ux_context': 'data_access',
    };
    final s = parseSensitiveActionError(detail);
    expect(s, isNotNull);
    expect(s!.uxMessage, contains('identité'));
    expect(s.uxTone, 'soft');
    expect(s.uxActionLabel, 'Confirmer');
    expect(s.uxContext, 'data_access');
    expect(s.displayMessage, s.uxMessage);
  });

  test('displayMessage falls back to message when ux_message absent', () {
    final detail = <String, dynamic>{
      'code': 'session.step_up_required',
      'message': 'Fallback API',
      'action_key': 'x',
      'reason_codes': <String>[],
      'next_step': 'none',
    };
    final s = parseSensitiveActionError(detail);
    expect(s!.displayMessage, 'Fallback API');
  });
}
