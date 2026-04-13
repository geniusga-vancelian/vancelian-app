import 'package:flutter/material.dart';

import '../atoms/app_typography.dart';

/// Composant : titre de page (ex: "Blog").
class AppPageTitle extends StatelessWidget {
  final String text;

  const AppPageTitle(this.text, {super.key});

  @override
  Widget build(BuildContext context) {
    return Text(text, style: AppTypography.pageTitle);
  }
}
