import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/ui/components/buttons/button_rounded.dart';

void main() {
  group('ButtonRounded', () {
    testWidgets('renders label', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ButtonRounded(
              icon: Icons.add,
              label: 'Déposer',
              onTap: () {},
            ),
          ),
        ),
      );

      expect(find.text('Déposer'), findsOneWidget);
    });

    testWidgets('applies primary variant when variant is primary',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ButtonRounded(
              icon: Icons.add,
              label: 'Déposer',
              onTap: () {},
              variant: ButtonRoundedVariant.primary,
            ),
          ),
        ),
      );

      expect(find.text('Déposer'), findsOneWidget);
      final button = tester.widget<ButtonRounded>(find.byType(ButtonRounded));
      expect(button.variant, ButtonRoundedVariant.primary);
    });

    testWidgets('disabled when onTap is null (no tap action)',
        (WidgetTester tester) async {
      int tapCount = 0;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ButtonRounded(
              icon: Icons.add,
              label: 'Déposer',
              onTap: null,
            ),
          ),
        ),
      );

      await tester.tap(find.byIcon(Icons.add));
      await tester.pumpAndSettle();
      expect(tapCount, 0);
    });

    testWidgets('calls onTap when enabled', (WidgetTester tester) async {
      int tapCount = 0;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ButtonRounded(
              icon: Icons.add,
              label: 'Déposer',
              onTap: () => tapCount++,
            ),
          ),
        ),
      );

      await tester.tap(find.byIcon(Icons.add));
      await tester.pumpAndSettle();
      expect(tapCount, 1);
    });
  });
}
