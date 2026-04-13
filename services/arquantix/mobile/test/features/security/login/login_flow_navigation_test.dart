import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:arquantix_news/features/auth/presentation/screens/welcome_landing_screen.dart';
import 'package:arquantix_news/features/security/login/presentation/login_phone_screen.dart';
import 'package:arquantix_news/features/security/login/presentation/login_method_sheet.dart';

void main() {
  testWidgets('WelcomeLanding (Login0) affiche Me connecter et Créer un compte', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: WelcomeLandingScreen()),
    );
    await tester.pump();

    expect(find.text('Créer un compte'), findsOneWidget);
    expect(find.text('Me connecter'), findsOneWidget);
    // Créer un compte (primary) au-dessus de Me connecter (secondary blanc).
    expect(
      tester.getTopLeft(find.text('Créer un compte')).dy,
      lessThan(tester.getTopLeft(find.text('Me connecter')).dy),
    );
  });

  testWidgets('LoginPhone affiche le champ mobile et Continuer', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: LoginPhoneScreen(hydrateLastSession: false),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Continuer'), findsOneWidget);
    expect(find.text('Autres options de connexion'), findsOneWidget);
    expect(find.text('Numéro de mobile'), findsOneWidget);
  });

  testWidgets('LoginMethodSheet expose e-mail, passkey et récupération', (tester) async {
    LoginMethodSheetChoice? picked;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (ctx) {
              return TextButton(
                onPressed: () async {
                  picked = await showLoginMethodSheet(ctx);
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

    expect(find.text('Continuer avec l’e-mail'), findsOneWidget);
    expect(find.text('Continuer avec une passkey'), findsOneWidget);
    expect(find.text('Je n’ai plus accès à mon numéro'), findsOneWidget);

    await tester.tap(find.text('Continuer avec l’e-mail'));
    await tester.pumpAndSettle();
    expect(picked, LoginMethodSheetChoice.email);
  });
}
