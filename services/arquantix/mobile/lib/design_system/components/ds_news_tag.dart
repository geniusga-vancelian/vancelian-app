import 'dart:ui';

import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_typography.dart';

/// Pastille « tag » news (Figma design-system / Tag.tsx) : blur 12, fond blanc,
/// point coloré + libellé 11px semibold.
class DsNewsTag extends StatelessWidget {
  const DsNewsTag({
    super.key,
    required this.label,
    this.dotColor = const Color(0xFFFF383C),
  });

  final String label;

  /// Couleur du point (défaut Figma `#FF383C`).
  final Color dotColor;

  static const double _blur = 12;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(8),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: _blur, sigmaY: _blur),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
          color: AppColors.white,
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
              const SizedBox(width: 4),
              Text(
                label,
                style: AppTypography.labelEmphasized.copyWith(
                  color: AppColors.black,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
