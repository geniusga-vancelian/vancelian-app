import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/features/wallet/wallet_page.dart';

void main() {
  group('WalletPage', () {
    testWidgets('renders without errors and contains balance placeholder', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: WalletPage(balanceAmount: '£0'),
        ),
      );

      expect(find.text('£0'), findsOneWidget);
    });

    testWidgets('AppBar exists and is pinned', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: WalletPage(),
        ),
      );

      expect(find.byType(SliverAppBar), findsOneWidget);
      final appBar = tester.widget<SliverAppBar>(find.byType(SliverAppBar));
      expect(appBar.pinned, true);
    });

    testWidgets('custom balance amount is displayed', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: WalletPage(balanceAmount: '£1,234.56'),
        ),
      );

      expect(find.text('£1,234.56'), findsOneWidget);
    });
  });
}
