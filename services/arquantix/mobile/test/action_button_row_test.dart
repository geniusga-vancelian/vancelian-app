import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/ui/components/buttons/action_button_row.dart';
import 'package:arquantix_news/ui/components/buttons/button_rounded.dart';

void main() {
  group('ActionButtonRow', () {
    testWidgets('renders 4 labels when using default constructor',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ActionButtonRow.defaultActions(),
          ),
        ),
      );

      expect(find.text('Déposer'), findsOneWidget);
      expect(find.text('Envoyer'), findsOneWidget);
      expect(find.text('Acheter'), findsOneWidget);
      expect(find.text('Plus'), findsOneWidget);
    });

    testWidgets('tapping one calls the correct callback',
        (WidgetTester tester) async {
      bool depositTapped = false;
      bool sendTapped = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ActionButtonRow.defaultActions(
              onDeposit: () => depositTapped = true,
              onSend: () => sendTapped = true,
            ),
          ),
        ),
      );

      await tester.tap(find.byIcon(Icons.arrow_forward_rounded));
      await tester.pumpAndSettle();
      expect(sendTapped, true);
      expect(depositTapped, false);

      depositTapped = false;
      sendTapped = false;
      await tester.tap(find.byIcon(Icons.add));
      await tester.pumpAndSettle();
      expect(depositTapped, true);
      expect(sendTapped, false);
    });

    testWidgets('renders custom items when using generic constructor',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ActionButtonRow(
              items: const [
                ActionButtonItem(
                  icon: Icons.star,
                  label: 'One',
                  variant: ButtonRoundedVariant.primary,
                ),
                ActionButtonItem(icon: Icons.favorite, label: 'Two'),
              ],
            ),
          ),
        ),
      );

      expect(find.text('One'), findsOneWidget);
      expect(find.text('Two'), findsOneWidget);
      expect(find.text('Déposer'), findsNothing);
    });
  });
}
