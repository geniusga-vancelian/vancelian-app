import 'package:flutter/material.dart';

import 'navigation/app_bottom_nav.dart';
import 'theme/app_theme.dart';

/// Minimal demo: 5 placeholder pages + floating bottom nav.
/// State is lifted: [DemoNavApp] holds [currentIndex] and passes it to [AppBottomNav].
class DemoNavApp extends StatefulWidget {
  const DemoNavApp({super.key});

  @override
  State<DemoNavApp> createState() => _DemoNavAppState();
}

class _DemoNavAppState extends State<DemoNavApp> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      theme: AppTheme.light,
      debugShowCheckedModeBanner: false,
      home: Scaffold(
        body: Stack(
          children: [
            IndexedStack(
              index: _currentIndex,
              children: const [
                _PlaceholderPage(title: 'Accueil', color: Color(0xFFE8F4F8)),
                _PlaceholderPage(title: 'Investir', color: Color(0xFFF5E8F0)),
                _PlaceholderPage(title: 'Markets', color: Color(0xFFE8F0F5)),
                _PlaceholderPage(title: 'Design', color: Color(0xFFF0E8F5)),
                _PlaceholderPage(title: 'Recherche', color: Color(0xFFF5F0E8)),
              ],
            ),
            AppBottomNav(
              currentIndex: _currentIndex,
              onTap: (index) => setState(() => _currentIndex = index),
            ),
          ],
        ),
      ),
    );
  }
}

class _PlaceholderPage extends StatelessWidget {
  final String title;
  final Color color;

  const _PlaceholderPage({required this.title, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: color,
      child: SafeArea(
        child: Center(
          child: Text(
            title,
            style: Theme.of(context).textTheme.headlineMedium,
          ),
        ),
      ),
    );
  }
}
