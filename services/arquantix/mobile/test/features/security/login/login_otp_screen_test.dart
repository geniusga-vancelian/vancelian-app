import 'package:arquantix_news/core/app_nav_routes.dart';
import 'package:arquantix_news/features/security/login/application/auth_flow_lifecycle_guard.dart';
import 'package:arquantix_news/features/security/login/presentation/login_method_sheet.dart';
import 'package:arquantix_news/features/security/login/presentation/login_otp_screen.dart';
import 'package:arquantix_news/features/security/passkeys/data/passkey_api.dart';
import 'package:arquantix_news/features/security/passkeys/domain/passkey_exceptions.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

class _FakeOtpPasskeyApi extends PasskeyApi {
  _FakeOtpPasskeyApi() : super(debugBaseUrl: 'http://test.local');

  int startCalls = 0;
  int verifyCalls = 0;
  bool verifyUnauthorized = false;
  bool verifyAccountLocked = false;

  @override
  Future<Map<String, dynamic>> mobileLoginStart({required String phone}) async {
    startCalls++;
    return {
      'masked_target': '+33 •• •• 64',
      'resend_after_seconds': 0,
    };
  }

  @override
  Future<Map<String, dynamic>> mobileLoginVerify({
    required String phone,
    required String code,
    required String deviceId,
    String? fingerprintHeader,
  }) async {
    verifyCalls++;
    if (verifyAccountLocked) {
      throw PasskeyApiException(
        403,
        '{"detail":{"code":"security.account_locked","message":"Compte temporairement verrouillé pour raison de sécurité."}}',
      );
    }
    if (verifyUnauthorized || code != '123456') {
      throw PasskeyApiException(401, '{}');
    }
    return {'access_token': 'jwt-access', 'refresh_token': 'jwt-refresh'};
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() {
    FlutterSecureStorage.setMockInitialValues({});
  });

  tearDown(() {
    AuthFlowLifecycleConfig.backgroundStaleThreshold = const Duration(minutes: 5);
  });

  testWidgets('LoginOtpScreen : OTP valide → setup PIN (pile remplacée)', (tester) async {
    final fake = _FakeOtpPasskeyApi();
    bool? popped;

    await tester.pumpWidget(
      MaterialApp(
        routes: {
          AppNavRoutes.passcodeSetupBootstrap: (_) =>
              const Scaffold(body: Text('PASSCODE_SETUP_ROUTE')),
        },
        home: Scaffold(
          body: Builder(
            builder: (ctx) {
              return TextButton(
                onPressed: () async {
                  popped = await Navigator.of(ctx).push<bool>(
                    MaterialPageRoute<bool>(
                      builder: (_) => LoginOtpScreen(
                        phoneE164: '+33612345678',
                        passkeyApi: fake,
                      ),
                    ),
                  );
                },
                child: const Text('open'),
              );
            },
          ),
        ),
      ),
    );

    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();

    expect(find.text('Connexion'), findsOneWidget);
    expect(find.textContaining('+33 •• •• 64'), findsOneWidget);
    expect(fake.startCalls, 1);

    expect(find.byType(TextField), findsOneWidget);
    final otpField = find.byType(TextField);
    await tester.ensureVisible(otpField);
    await tester.tap(otpField);
    await tester.pump();
    await tester.enterText(otpField, '123456');
    await tester.pumpAndSettle();

    expect(fake.verifyCalls, 1);
    expect(find.text('PASSCODE_SETUP_ROUTE'), findsOneWidget);
    expect(popped, isNull);
  });

  testWidgets('LoginOtpScreen : code invalide affiche le message d’erreur',
      (tester) async {
    final fake = _FakeOtpPasskeyApi();

    await tester.pumpWidget(
      MaterialApp(
        home: LoginOtpScreen(
          phoneE164: '+33612345678',
          passkeyApi: fake,
        ),
      ),
    );
    await tester.pumpAndSettle();

    final otpField = find.byType(TextField);
    expect(otpField, findsOneWidget);
    await tester.tap(otpField);
    await tester.pump();
    await tester.enterText(otpField, '000000');
    await tester.pumpAndSettle();

    expect(fake.verifyCalls, 1);
    expect(find.text('Code incorrect ou expiré.'), findsOneWidget);
  });

  testWidgets('LoginOtpScreen : compte verrouillé (403) affiche un message clair',
      (tester) async {
    final fake = _FakeOtpPasskeyApi()..verifyAccountLocked = true;

    await tester.pumpWidget(
      MaterialApp(
        home: LoginOtpScreen(
          phoneE164: '+33612345678',
          passkeyApi: fake,
        ),
      ),
    );
    await tester.pumpAndSettle();

    final otpField = find.byType(TextField);
    await tester.tap(otpField);
    await tester.pump();
    await tester.enterText(otpField, '123456');
    await tester.pumpAndSettle();

    expect(fake.verifyCalls, 1);
    expect(find.textContaining('verrouillé'), findsOneWidget);
  });

  testWidgets('LoginOtpScreen : renvoi appelle start une seconde fois',
      (tester) async {
    final fake = _FakeOtpPasskeyApi();

    await tester.pumpWidget(
      MaterialApp(
        home: LoginOtpScreen(
          phoneE164: '+33612345678',
          passkeyApi: fake,
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(fake.startCalls, 1);

    await tester.tap(find.text('Renvoyer le code'));
    await tester.pumpAndSettle();

    expect(fake.startCalls, 2);
  });

  testWidgets('LoginOtpScreen : background prolongé → modale session expirée',
      (tester) async {
    AuthFlowLifecycleConfig.backgroundStaleThreshold = Duration.zero;
    final fake = _FakeOtpPasskeyApi();

    await tester.pumpWidget(
      MaterialApp(
        home: LoginOtpScreen(
          phoneE164: '+33612345678',
          passkeyApi: fake,
        ),
      ),
    );
    await tester.pumpAndSettle();

    final binding = tester.binding;
    // Séquence conforme à AppLifecycleListener (Flutter 3.41+) : inactive → hidden → paused,
    // puis hidden → inactive → resumed (pas de saut d’états).
    binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
    await tester.pump();
    binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
    await tester.pump();
    binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    await tester.pump();
    binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
    await tester.pump();
    binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
    await tester.pump();
    binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pumpAndSettle();

    expect(find.text('Session expirée, veuillez recommencer'), findsOneWidget);
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();
  });

  testWidgets('LoginOtpScreen : smsStartResult évite mobileLoginStart au montage',
      (tester) async {
    final fake = _FakeOtpPasskeyApi();

    await tester.pumpWidget(
      MaterialApp(
        home: LoginOtpScreen(
          phoneE164: '+33612345678',
          passkeyApi: fake,
          smsStartResult: {
            'masked_target': '+33 •• •• 99',
            'resend_after_seconds': 0,
          },
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(fake.startCalls, 0);
    expect(find.textContaining('+33 •• •• 99'), findsOneWidget);
    expect(find.text('Connexion'), findsOneWidget);
  });

  testWidgets('showLoginOtpFallbackSheet expose e-mail et passkey', (tester) async {
    LoginOtpFallbackChoice? picked;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (ctx) {
              return TextButton(
                onPressed: () async {
                  picked = await showLoginOtpFallbackSheet(ctx);
                },
                child: const Text('open'),
              );
            },
          ),
        ),
      ),
    );

    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();

    expect(find.text('Autres options de connexion'), findsOneWidget);
    expect(find.text('Continuer avec l’e-mail'), findsOneWidget);
    expect(find.text('Utiliser une passkey'), findsOneWidget);

    await tester.tap(find.text('Utiliser une passkey'));
    await tester.pumpAndSettle();
    expect(picked, LoginOtpFallbackChoice.passkey);
  });
}
