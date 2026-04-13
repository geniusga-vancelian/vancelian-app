import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/features/registration/screens/registration_flow_launcher_screen.dart';
import 'package:arquantix_news/features/registration/screens/registration_flow_screen.dart';

Widget _wrap(Widget child) {
  return MaterialApp(home: child);
}

void main() {
  group('RegistrationTestLauncherScreen', () {
    testWidgets('shows loading then content', (tester) async {
      await tester.pumpWidget(
        _wrap(const RegistrationTestLauncherScreen()),
      );

      // Initially loading
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows Registration Lab header', (tester) async {
      await tester.pumpWidget(
        _wrap(const RegistrationTestLauncherScreen()),
      );

      // After attempting to load (will fail without backend)
      await tester.pump(const Duration(seconds: 1));

      // The header should still be rendered even on error
      // because it's in the Scaffold title
      expect(find.text('Parcours d’inscription'), findsOneWidget);
    });

    testWidgets(
      'titre présent pendant le chargement (réseau non mocké — pas d’attente de fin)',
      (tester) async {
      await tester.pumpWidget(
        _wrap(const RegistrationTestLauncherScreen()),
      );

      await tester.pump();
      expect(find.text('Parcours d’inscription'), findsOneWidget);
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    },
    );
  });

  group('RegistrationFlowScreen', () {
    testWidgets('can be constructed with jurisdiction parameter',
        (tester) async {
      await tester.pumpWidget(
        _wrap(const RegistrationFlowScreen(jurisdiction: 'EU')),
      );

      // Should render — will show loading or error since no backend
      expect(find.byType(RegistrationFlowScreen), findsOneWidget);
      await tester.pump(const Duration(milliseconds: 400));
    });
  });
}
