import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:arquantix_news/ui/components/transaction/transaction_avatar.dart';
import 'package:arquantix_news/ui/components/transaction/transaction_tile.dart';

void main() {
  group('TransactionTile', () {
    testWidgets('renders title', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TransactionTile(
              avatar: TransactionAvatar(
                icon: Icons.savings,
                backgroundColor: Colors.orange,
              ),
              title: 'Savings',
            ),
          ),
        ),
      );

      expect(find.text('Savings'), findsOneWidget);
    });

    testWidgets('subtitle optional when null not found', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TransactionTile(
              avatar: TransactionAvatar(
                icon: Icons.savings,
                backgroundColor: Colors.orange,
              ),
              title: 'Savings',
              subtitle: null,
            ),
          ),
        ),
      );

      expect(find.text('Savings'), findsOneWidget);
      expect(find.byType(TransactionTile), findsOneWidget);
      expect(find.text('Earn interest'), findsNothing);
    });

    testWidgets('subtitle shown when provided', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TransactionTile(
              avatar: TransactionAvatar(
                icon: Icons.savings,
                backgroundColor: Colors.orange,
              ),
              title: 'Savings',
              subtitle: 'Earn interest',
            ),
          ),
        ),
      );

      expect(find.text('Savings'), findsOneWidget);
      expect(find.text('Earn interest'), findsOneWidget);
    });

    testWidgets('right texts optional when null not found', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TransactionTile(
              avatar: TransactionAvatar(
                icon: Icons.currency_bitcoin,
                backgroundColor: Colors.orange,
              ),
              title: 'Bitcoin',
              rightPrimary: null,
              rightSecondary: null,
            ),
          ),
        ),
      );

      expect(find.text('Bitcoin'), findsOneWidget);
      expect(find.text('£9,440.64'), findsNothing);
      expect(find.text('▲ 1.86%'), findsNothing);
    });

    testWidgets('right primary and secondary shown when provided', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TransactionTile(
              avatar: TransactionAvatar(
                icon: Icons.currency_bitcoin,
                backgroundColor: Colors.orange,
              ),
              title: 'Bitcoin',
              rightPrimary: '£9,440.64',
              rightSecondary: '▲ 1.86%',
            ),
          ),
        ),
      );

      expect(find.text('Bitcoin'), findsOneWidget);
      expect(find.text('£9,440.64'), findsOneWidget);
      expect(find.text('▲ 1.86%'), findsOneWidget);
    });

    testWidgets('chevron appears only when showChevron true', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                TransactionTile(
                  avatar: TransactionAvatar(
                    icon: Icons.savings,
                    backgroundColor: Colors.orange,
                  ),
                  title: 'Savings',
                  showChevron: false,
                ),
                TransactionTile(
                  avatar: TransactionAvatar(
                    icon: Icons.account_balance,
                    backgroundColor: Colors.blue,
                  ),
                  title: 'Cash',
                  showChevron: true,
                ),
              ],
            ),
          ),
        ),
      );

      final chevrons = find.byIcon(Icons.chevron_right);
      expect(chevrons, findsOneWidget);
    });

    testWidgets('tap triggers onTap when enabled', (WidgetTester tester) async {
      int tapCount = 0;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TransactionTile(
              avatar: TransactionAvatar(
                icon: Icons.savings,
                backgroundColor: Colors.orange,
              ),
              title: 'Savings',
              showChevron: true,
              onTap: () => tapCount++,
              isEnabled: true,
            ),
          ),
        ),
      );

      await tester.tap(find.text('Savings'));
      await tester.pumpAndSettle();
      expect(tapCount, 1);
    });

    testWidgets('disabled state does not trigger onTap', (WidgetTester tester) async {
      int tapCount = 0;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TransactionTile(
              avatar: TransactionAvatar(
                icon: Icons.savings,
                backgroundColor: Colors.orange,
              ),
              title: 'Savings',
              onTap: () => tapCount++,
              isEnabled: false,
            ),
          ),
        ),
      );

      await tester.tap(find.text('Savings'));
      await tester.pumpAndSettle();
      expect(tapCount, 0);
    });
  });
}
