import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Composant : chip de filtre / tabulation (sans contour, sans icône à l'état actif).
class AppFilterChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const AppFilterChip({
    required this.label,
    required this.selected,
    required this.onTap,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: AppSpacing.sm + 2), // 10
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(AppRadius.chip),
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.lg,
              vertical: AppSpacing.sm + 2,
            ),
            decoration: BoxDecoration(
              color: selected ? AppColors.textPrimary : AppColors.cardBackground,
              borderRadius: BorderRadius.circular(AppRadius.chip),
              border: Border.all(color: Colors.transparent, width: 0),
            ),
            child: Text(
              label,
              style: AppTypography.chipLabel(selected: selected),
            ),
          ),
        ),
      ),
    );
  }
}
