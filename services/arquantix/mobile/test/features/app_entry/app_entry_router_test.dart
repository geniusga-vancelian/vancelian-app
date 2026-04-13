import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:arquantix_news/core/app_nav_routes.dart';
import 'package:arquantix_news/features/app_entry/domain/app_entry_destination.dart';
import 'package:arquantix_news/features/app_entry/presentation/app_entry_router.dart';
import 'package:arquantix_news/features/auth/presentation/screens/welcome_landing_screen.dart';
import 'package:arquantix_news/features/security/passcode/presentation/screens/passcode_setup_screen.dart';

void main() {
  Future<void> pumpRouter(
    WidgetTester tester, {
    required Future<AppEntryDestination> Function() resolve,
  }) async {
    await tester.pumpWidget(
      MaterialApp(
        routes: {
          AppNavRoutes.welcome: (_) => const Scaffold(body: Text('LOGIN0')),
          AppNavRoutes.passcodeSetupBootstrap: (_) =>
              const Scaffold(body: Text('PASSCODE_SETUP')),
          AppNavRoutes.secureGate: (_) => const Scaffold(body: Text('SECURE_GATE')),
          AppNavRoutes.secureGatePostAuth: (_) =>
              const Scaffold(body: Text('SECURE_POST')),
        },
        home: AppEntryRouter(resolveDestinationOverride: resolve),
      ),
    );
    await tester.pump();
    await tester.pumpAndSettle();
  }

  testWidgets('AppEntryRouter → Login0', (tester) async {
    await pumpRouter(
      tester,
      resolve: () async => AppEntryDestination.login0,
    );
    expect(find.byType(WelcomeLandingScreen), findsOneWidget);
    expect(find.text('Me connecter'), findsOneWidget);
  });

  testWidgets('AppEntryRouter → PasscodeSetup', (tester) async {
    await pumpRouter(
      tester,
      resolve: () async => AppEntryDestination.passcodeSetup,
    );
    expect(find.byType(PasscodeSetupScreen), findsOneWidget);
  });

  testWidgets('WelcomeLanding présent sur route nommée (Login0)', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        routes: {AppNavRoutes.welcome: (_) => const WelcomeLandingScreen()},
        initialRoute: AppNavRoutes.welcome,
      ),
    );
    await tester.pump();
    expect(find.text('Me connecter'), findsOneWidget);
  });
}
