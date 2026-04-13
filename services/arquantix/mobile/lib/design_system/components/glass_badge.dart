import 'dart:ui';

import 'package:flutter/material.dart';

import '../atoms/atoms.dart';

/// Étiquette avec effet glassmorphism (backdrop blur).
///
/// Deux niveaux d'opacité :
///   - [GlassBadgeOpacity.medium] (0.6) — défaut, plus lisible
///   - [GlassBadgeOpacity.light] (0.3) — plus subtil
enum GlassBadgeOpacity { light, medium }

class GlassBadge extends StatelessWidget {
  final String text;
  final GlassBadgeOpacity opacity;
  final VoidCallback? onTap;

  const GlassBadge({
    super.key,
    required this.text,
    this.opacity = GlassBadgeOpacity.medium,
    this.onTap,
  });

  static const double _blur = 12;

  @override
  Widget build(BuildContext context) {
    final bgColor = opacity == GlassBadgeOpacity.medium
        ? AppColors.glassOverlay
        : AppColors.darkOpacity30;

    return ClipRRect(
      borderRadius: BorderRadius.circular(AppRadius.full),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: _blur, sigmaY: _blur),
        child: Material(
          color: bgColor,
          borderRadius: BorderRadius.circular(AppRadius.full),
          child: InkWell(
            onTap: onTap,
            borderRadius: BorderRadius.circular(AppRadius.full),
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.s2),
              child: Text(
                text,
                style: AppTypography.labelEmphasized.copyWith(
                  color: AppColors.white,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
