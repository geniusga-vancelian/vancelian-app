import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_motion.dart';
import '../atoms/app_radius.dart';

/// Barre de progression linéaire animée.
///
/// [value] de 0.0 à 1.0. Si null, la barre est en mode indéterminé.
class AppProgressBar extends StatelessWidget {
  const AppProgressBar({
    super.key,
    this.value,
    this.height = 6,
    this.color,
    this.backgroundColor,
    this.borderRadius = AppRadius.full,
  });

  final double? value;
  final double height;
  final Color? color;
  final Color? backgroundColor;
  final double borderRadius;

  @override
  Widget build(BuildContext context) {
    final bgColor = backgroundColor ?? AppColors.indigo.withValues(alpha: 0.15);
    final fgColor = color ?? AppColors.indigo;

    if (value == null) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(borderRadius),
        child: SizedBox(
          height: height,
          child: LinearProgressIndicator(
            backgroundColor: bgColor,
            valueColor: AlwaysStoppedAnimation<Color>(fgColor),
          ),
        ),
      );
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: SizedBox(
        height: height,
        child: Stack(
          children: [
            Container(color: bgColor),
            AnimatedFractionallySizedBox(
              duration: AppMotion.base,
              curve: AppMotion.standard,
              widthFactor: value!.clamp(0.0, 1.0),
              alignment: Alignment.centerLeft,
              child: Container(
                decoration: BoxDecoration(
                  color: fgColor,
                  borderRadius: BorderRadius.circular(borderRadius),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
