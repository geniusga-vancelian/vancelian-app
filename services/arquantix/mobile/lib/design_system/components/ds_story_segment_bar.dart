import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';

/// Variante : segments clairs sur photo (stories) vs foncés sur fond page claire.
enum DsStorySegmentBarVariant {
  /// Piste blanche / blanche 48 % — au-dessus d’une image sombre.
  onMedia,

  /// Piste noire / gris léger — sous le titre, fond [AppColors.pageBackground].
  onSurface,
}

/// Barre type « stories » (segments en haut) — Figma / ZIP PaginationIndicator.
/// À n’afficher que lorsque [segmentCount] > 1.
class DsStorySegmentBar extends StatelessWidget {
  const DsStorySegmentBar({
    super.key,
    required this.segmentCount,
    required this.activeIndex,
    this.variant = DsStorySegmentBarVariant.onSurface,
    this.height = 3,
    this.gap = 4,
  });

  final int segmentCount;
  final int activeIndex;
  final DsStorySegmentBarVariant variant;
  final double height;
  final double gap;

  @override
  Widget build(BuildContext context) {
    if (segmentCount <= 1) return const SizedBox.shrink();
    final safeIndex = activeIndex.clamp(0, segmentCount - 1);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xs),
      child: Row(
        children: List.generate(segmentCount, (i) {
          final isActive = i == safeIndex;
          return Expanded(
            child: Padding(
              padding: EdgeInsets.symmetric(horizontal: gap / 2),
              child: _Segment(
                height: height,
                isActive: isActive,
                variant: variant,
              ),
            ),
          );
        }),
      ),
    );
  }
}

class _Segment extends StatelessWidget {
  const _Segment({
    required this.height,
    required this.isActive,
    required this.variant,
  });

  final double height;
  final bool isActive;
  final DsStorySegmentBarVariant variant;

  @override
  Widget build(BuildContext context) {
    final (Color active, Color inactive) = switch (variant) {
      DsStorySegmentBarVariant.onMedia => (
          AppColors.white,
          AppColors.white.withValues(alpha: 0.48),
        ),
      DsStorySegmentBarVariant.onSurface => (
          AppColors.textPrimary,
          AppColors.textPrimary.withValues(alpha: 0.18),
        ),
    };
    return Container(
      height: height,
      decoration: BoxDecoration(
        color: isActive ? active : inactive,
        borderRadius: BorderRadius.circular(50),
      ),
    );
  }
}
