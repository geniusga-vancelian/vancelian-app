import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'category_badge.dart';
import 'market_trend_caret.dart';

/// Ligne de performance du hero détail instrument (puces [SurfaceTag] + libellé de période),
/// identique au rendu historique du détail crypto.
class InstrumentDetailHeroPerformanceRow extends StatelessWidget {
  const InstrumentDetailHeroPerformanceRow({
    super.key,
    this.absChipText,
    this.absChipColor,
    required this.percentChipText,
    required this.periodLabel,
    required this.percentColor,
    required this.percentIsPositive,
  });

  /// Variation absolue (ex. devise). Si null ou vide, seule la pilule % est affichée (bundles).
  final String? absChipText;
  final Color? absChipColor;
  final String percentChipText;
  final String periodLabel;
  final Color percentColor;
  final bool percentIsPositive;

  @override
  Widget build(BuildContext context) {
    final showAbs =
        absChipText != null && absChipText!.trim().isNotEmpty;
    return Wrap(
      spacing: AppSpacing.s2,
      runSpacing: AppSpacing.xs,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        if (showAbs)
          SurfaceTag(
            child: Text(
              absChipText!,
              style: AppTypography.supportingBdPerformanceChip.copyWith(
                color: absChipColor ?? AppColors.textPrimary,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        SurfaceTag(
          child: Row(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              MarketTrendCaret(up: percentIsPositive, color: percentColor),
              const SizedBox(width: AppSpacing.s1),
              Text(
                percentChipText,
                style: AppTypography.supportingBdPerformanceChip.copyWith(
                  color: percentColor,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
        Text(
          periodLabel,
          style: AppTypography.itemSupporting.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }
}

/// Couleur de la puce « variation absolue » (même règles que le détail instrument crypto).
Color instrumentHeroAbsChipColor({
  required double? changeAbs,
  required double? changePct,
  required Color perfColor,
}) {
  if (changePct != null) return perfColor;
  if (changeAbs == null) return AppColors.textPrimary;
  if (changeAbs > 0) return AppColors.semanticPositive;
  if (changeAbs < 0) return AppColors.semanticNegative;
  return AppColors.textPrimary;
}
