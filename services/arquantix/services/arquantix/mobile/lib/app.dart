import 'package:flutter/material.dart';

import 'core/theme/app_theme.dart';
import 'features/news/presentation/screens/article_list_screen.dart';

/// Point d'entrée UI de l'application Arquantix News
class App extends StatelessWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Arquantix News',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      home: const ArticleListScreen(),
    );
  }
}
