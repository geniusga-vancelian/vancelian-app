import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:arquantix_news/ui/navigation/app_bottom_nav.dart';
import 'package:arquantix_news/ui/theme/app_colors.dart';

void main() {
  group('AppBottomNav', () {
    testWidgets('renders 4 labels and search icon', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Stack(
              children: [
                AppBottomNav(
                  currentIndex: 0,
                  onTap: (_) {},
                ),
              ],
            ),
          ),
        ),
      );

      expect(find.text('Accueil'), findsOneWidget);
      expect(find.text('Investir'), findsOneWidget);
      expect(find.text('Markets'), findsOneWidget);
      expect(find.text('Design'), findsOneWidget);
      expect(find.byIcon(Icons.search_rounded), findsOneWidget);
    });

    testWidgets('tapping calls onTap with correct index',
        (WidgetTester tester) async {
      int? tappedIndex;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Stack(
              children: [
                AppBottomNav(
                  currentIndex: 0,
                  onTap: (index) => tappedIndex = index,
                ),
              ],
            ),
          ),
        ),
      );

      await tester.tap(find.byIcon(Icons.search_rounded));
      await tester.pumpAndSettle();
      expect(tappedIndex, 4);

      tappedIndex = null;
      await tester.tap(find.text('Design'));
      await tester.pumpAndSettle();
      expect(tappedIndex, 3);
    });

    testWidgets('selected item uses selected color', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Stack(
              children: [
                AppBottomNav(
                  currentIndex: 1,
                  onTap: (_) {},
                ),
              ],
            ),
          ),
        ),
      );

      final iconWidgets = tester.widgetList<Icon>(find.byType(Icon)).toList();
      expect(iconWidgets.length, 5);
      expect(iconWidgets[1].color, AppColors.navSelected);
    });

    testWidgets('unselected items use unselected color',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Stack(
              children: [
                AppBottomNav(
                  currentIndex: 0,
                  onTap: (_) {},
                ),
              ],
            ),
          ),
        ),
      );

      final iconWidgets = tester.widgetList<Icon>(find.byType(Icon)).toList();
      expect(iconWidgets.length, 5);
      expect(iconWidgets[1].color, AppColors.navUnselected);
      expect(iconWidgets[2].color, AppColors.navUnselected);
      expect(iconWidgets[3].color, AppColors.navUnselected);
      expect(iconWidgets[4].color, AppColors.navUnselected);
    });
  });
}
