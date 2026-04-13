import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_typography.dart';

/// Ligne secondaire sous le montant du hero [LayoutPageInstrumentDetail],
/// sans puces (alternative à [InstrumentDetailHeroPerformanceRow] pour le détail transaction).
class InstrumentDetailHeroSupportingLine extends StatelessWidget {
  const InstrumentDetailHeroSupportingLine({
    super.key,
    required this.text,
    this.secondarySuffix,
  });

  final String text;
  final String? secondarySuffix;

  @override
  Widget build(BuildContext context) {
    final primary = text.trim();
    final suffix = secondarySuffix?.trim();
    final full = (suffix != null && suffix.isNotEmpty)
        ? '$primary · $suffix'
        : primary;
    return Text(
      full,
      style: AppTypography.itemSupporting.copyWith(
        color: AppColors.textSecondary,
      ),
      textAlign: TextAlign.start,
      maxLines: 3,
      overflow: TextOverflow.ellipsis,
    );
  }
}
