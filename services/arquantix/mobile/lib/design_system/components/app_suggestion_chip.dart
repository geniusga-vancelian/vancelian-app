import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Chip de suggestion (ex: catégories sur l’écran Search). Un seul style, cliquable.
class AppSuggestionChip extends StatelessWidget {
  final String label;
  final VoidCallback onPressed;

  const AppSuggestionChip({
    required this.label,
    required this.onPressed,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return ActionChip(
      label: Text(label, style: AppTypography.labelMedium),
      onPressed: onPressed,
      backgroundColor: AppColors.navBarActivePill,
      side: BorderSide.none,
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.xs,
      ),
    );
  }
}
