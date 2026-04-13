import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Bouton Filled compact (moins de padding vertical qu’un bouton standard).
class AppMiniButton extends StatelessWidget {
  const AppMiniButton({
    super.key,
    required this.onPressed,
    required this.label,
    this.backgroundColor,
    this.foregroundColor,
  });

  final VoidCallback? onPressed;
  final String label;
  final Color? backgroundColor;
  final Color? foregroundColor;

  @override
  Widget build(BuildContext context) {
    return FilledButton(
      onPressed: onPressed,
      style: FilledButton.styleFrom(
        backgroundColor: backgroundColor ?? AppColors.accent,
        foregroundColor: foregroundColor ?? Colors.white,
        padding: const EdgeInsets.all(10),
        minimumSize: Size.zero,
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        alignment: Alignment.center,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.button),
        ),
        textStyle: AppTypography.bodyMedium.copyWith(
          fontWeight: FontWeight.w700,
          height: 1.0,
        ),
      ),
      child: Text(label),
    );
  }
}
