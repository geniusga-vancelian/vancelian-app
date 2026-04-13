import 'package:arquantix_news/design_system/components/app_otp_input.dart';
import 'package:arquantix_news/features/registration/data/registration_api.dart';
import 'package:arquantix_news/features/registration/data/registration_models.dart';
import 'package:arquantix_news/features/registration/widgets/registration_phone_sms_otp_panel.dart';
import 'package:arquantix_news/features/security/data/two_factor_api.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class _FakeRegApi extends RegistrationApi {
  _FakeRegApi() : super(baseUrl: 'http://test.local');

  int completeCalls = 0;
  int prepareCalls = 0;

  @override
  Future<ApiResult<Map<String, dynamic>>> prepareInteraction(
      String sessionId) async {
    prepareCalls++;
    return ApiResult(
      statusCode: 200,
      data: {
        'otp_token': 'jwt-test',
        'challenge_id': 'challenge-1',
        'purpose': 'verify_phone',
        'target_masked': '+33 •• •• 78',
        'resend_after_seconds': 2,
      },
    );
  }

  @override
  Future<ApiResult<Map<String, dynamic>>> resendInteraction(
    String sessionId, {
    required String screenId,
    required String interactionType,
  }) async {
    return ApiResult(
      statusCode: 200,
      data: {
        'otp_token': 'jwt-test-2',
        'challenge_id': 'challenge-2',
        'target_masked': '+33 •• •• 78',
        'resend_after_seconds': 2,
      },
    );
  }

  @override
  Future<ApiResult<Map<String, dynamic>>> completeInteraction(
    String sessionId, {
    required String screenId,
    required String interactionType,
    required String challengeId,
    required bool verified,
  }) async {
    completeCalls++;
    return ApiResult(statusCode: 200, data: {'status': 'ok'});
  }
}

class _AlwaysOkTwoFactorApi extends TwoFactorApi {
  _AlwaysOkTwoFactorApi({required super.accessToken})
      : super(
          startUrl: 'http://test.local/api/2fa/start',
          verifyUrl: 'http://test.local/api/2fa/verify',
        );

  @override
  Future<TwoFactorApiResult<void>> verify({
    required String challengeId,
    required String code,
    String? personId,
  }) async {
    return const TwoFactorApiResult(statusCode: 200, data: null);
  }
}

RegistrationScreen _smsScreen() {
  return RegistrationScreen.fromJson({
    'id': 'screen-1',
    'screen_key': 'sms',
    'title': 'Confirm your mobile number',
    'subtitle': 'Enter the 6-digit code sent to your phone',
    'layout_type': 'form',
    'screen_type': 'interaction',
    'interaction_type': 'phone_verification_sms',
    'interaction_config': {},
    'interaction_payload': {'challenge_ready': false},
    'components': [],
  });
}

void main() {
  testWidgets('shows AppOtpInput, timer text, and completes on 6 digits',
      (tester) async {
    final api = _FakeRegApi();
    var completed = 0;
    var backTaps = 0;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: RegistrationPhoneSmsOtpPanel(
            screen: _smsScreen(),
            sessionId: 'sess-1',
            registrationApi: api,
            collectedData: const {'phone_number': '+33612345678'},
            onGoBack: () => backTaps++,
            twoFactorApiBuilder: (t) => _AlwaysOkTwoFactorApi(accessToken: t),
            onCompleted: () async {
              completed++;
            },
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(api.prepareCalls, 1);
    expect(find.byType(AppOtpInput), findsOneWidget);
    expect(find.textContaining('Renvoyer'), findsOneWidget);

    final field = find.byType(TextField);
    expect(field, findsOneWidget);
    await tester.enterText(field, '123456');
    await tester.pumpAndSettle();

    expect(completed, 1);
    expect(api.completeCalls, 1);
  });

  testWidgets('payload error shows message without OTP', (tester) async {
    final screen = RegistrationScreen.fromJson({
      'id': 'screen-2',
      'screen_key': 'sms',
      'title': 'T',
      'layout_type': 'form',
      'screen_type': 'interaction',
      'interaction_type': 'phone_verification_sms',
      'interaction_payload': {
        'error_code': 'phone_number_required',
        'message': 'Please enter your phone number',
      },
      'components': [],
    });

    final api = _FakeRegApi();

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: RegistrationPhoneSmsOtpPanel(
            screen: screen,
            sessionId: 'sess-1',
            registrationApi: api,
            collectedData: const {},
            onGoBack: () {},
            onCompleted: () async {},
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(api.prepareCalls, 0);
    expect(find.text('Please enter your phone number'), findsOneWidget);
    expect(find.byType(AppOtpInput), findsNothing);
    expect(find.text('Réessayer'), findsNothing);
    expect(find.text('Retour'), findsOneWidget);
  });

  testWidgets('missing collected phone does not call prepare', (tester) async {
    final api = _FakeRegApi();

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: RegistrationPhoneSmsOtpPanel(
            screen: _smsScreen(),
            sessionId: 'sess-1',
            registrationApi: api,
            collectedData: const {},
            onGoBack: () {},
            onCompleted: () async {},
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(api.prepareCalls, 0);
    expect(find.byType(AppOtpInput), findsNothing);
    expect(
      find.textContaining('étape précédente'),
      findsOneWidget,
    );
    expect(find.text('Réessayer'), findsNothing);
    expect(find.text('Retour'), findsOneWidget);
  });

  testWidgets('prepare 422 invalid_phone shows retry and retour', (tester) async {
    final api = _PrepareFailsInvalidPhoneApi();

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: RegistrationPhoneSmsOtpPanel(
            screen: _smsScreen(),
            sessionId: 'sess-1',
            registrationApi: api,
            collectedData: const {'phone_number': '+33612345678'},
            onGoBack: () {},
            onCompleted: () async {},
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(
      find.text('Please enter your phone number without the leading 0'),
      findsOneWidget,
    );
    expect(find.text('Réessayer'), findsOneWidget);
    expect(find.text('Retour'), findsOneWidget);
    expect(find.byType(AppOtpInput), findsNothing);
  });
}

class _PrepareFailsInvalidPhoneApi extends _FakeRegApi {
  @override
  Future<ApiResult<Map<String, dynamic>>> prepareInteraction(
      String sessionId) async {
    prepareCalls++;
    return ApiResult(
      statusCode: 422,
      errorMessage:
          'Please enter your phone number without the leading 0',
      errorCode: 'invalid_phone_number',
    );
  }
}
