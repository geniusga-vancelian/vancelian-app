import 'dart:ui';

import 'package:flutter/material.dart';

import '../atoms/atoms.dart';

/// Même enveloppe que la puce catégorie Figma (**Category**) : backdrop-blur 12,
/// fond blanc, coins [AppRadius.sm], padding horizontal 8 / vertical 6.
///
/// Utilisable pour les tags sous le prix (variation absolue, %) comme pour [CategoryBadge].
class SurfaceTag extends StatelessWidget {
  const SurfaceTag({
    super.key,
    required this.child,
    this.onTap,
    /// Fond de la puce (défaut blanc). Ex. [AppColors.pageBackground] sur carte blanche.
    this.backgroundColor = AppColors.white,
  });

  final Widget child;
  final VoidCallback? onTap;
  final Color backgroundColor;

  static const double _blurSigma = 12;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(AppRadius.sm),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: _blurSigma, sigmaY: _blurSigma),
        child: GestureDetector(
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.s2,
              vertical: 6,
            ),
            decoration: BoxDecoration(
              color: backgroundColor,
              borderRadius: BorderRadius.circular(AppRadius.sm),
            ),
            child: child,
          ),
        ),
      ),
    );
  }
}

/// Badge catégorie avec point coloré + texte sur fond glassmorphism blanc.
///
/// Figma: backdrop-blur 12, bg white, rounded 8, px 8, py 6.
/// Point: 4px circle [dotColor].
/// Texte: [AppTypography.labelTagEmphasized] (11px / w700 / tracking 0.06 / lh 13).
class CategoryBadge extends StatelessWidget {
  final String label;
  final Color dotColor;
  final VoidCallback? onTap;
  final Color surfaceColor;

  const CategoryBadge({
    super.key,
    required this.label,
    required this.dotColor,
    this.onTap,
    this.surfaceColor = AppColors.white,
  });

  @override
  Widget build(BuildContext context) {
    return SurfaceTag(
      onTap: onTap,
      backgroundColor: surfaceColor,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 4,
            height: 4,
            decoration: BoxDecoration(
              color: dotColor,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: AppSpacing.s1),
          Text(
            label,
            style: AppTypography.labelTagEmphasized.copyWith(
              color: AppColors.black,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}
