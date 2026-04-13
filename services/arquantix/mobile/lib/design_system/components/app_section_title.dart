import 'package:flutter/material.dart';

import '../atoms/app_typography.dart';

/// Composant : titre de section (ex: "A la une", "All news").
class AppSectionTitle extends StatelessWidget {
  final String text;

  const AppSectionTitle(this.text, {super.key});

  @override
  Widget build(BuildContext context) {
    return Text(text, style: AppTypography.sectionTitle);
  }
}

/// Composant : titre de module secondaire (~20% plus petit que AppSectionTitle).
class AppSectionTitle2 extends StatelessWidget {
  final String text;

  const AppSectionTitle2(this.text, {super.key});

  @override
  Widget build(BuildContext context) {
    return Text(text, style: AppTypography.sectionTitle2);
  }
}
