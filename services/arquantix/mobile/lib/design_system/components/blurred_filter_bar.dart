import 'dart:ui';

import 'package:flutter/material.dart';

/// Conteneur glassy/blur pour envelopper des filtres (chips, tabs, etc.).
class BlurredFilterBar extends StatelessWidget {
  const BlurredFilterBar({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
    this.borderRadius = 16,
    this.sigmaX = 14,
    this.sigmaY = 14,
    this.tintColor = Colors.white,
    this.tintOpacity = 0.55,
    this.borderColor = Colors.white,
    this.borderOpacity = 0.35,
    this.borderWidth = 1,
  });

  /// Preset officiel "Apple glass" pour un rendu homogène.
  const BlurredFilterBar.apple({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
    this.borderRadius = 16,
    this.sigmaX = 14,
    this.sigmaY = 14,
    this.tintColor = Colors.white,
    this.tintOpacity = 0.55,
    this.borderColor = Colors.white,
    this.borderOpacity = 0.35,
    this.borderWidth = 1,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final double borderRadius;
  final double sigmaX;
  final double sigmaY;
  final Color tintColor;
  final double tintOpacity;
  final Color borderColor;
  final double borderOpacity;
  final double borderWidth;

  @override
  Widget build(BuildContext context) {
    final clampedTintOpacity = tintOpacity.clamp(0.0, 1.0);
    final clampedBorderOpacity = borderOpacity.clamp(0.0, 1.0);
    return ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: sigmaX, sigmaY: sigmaY),
        child: Container(
          padding: padding,
          decoration: BoxDecoration(
            color: tintColor.withValues(alpha: clampedTintOpacity),
            borderRadius: BorderRadius.circular(borderRadius),
            border: Border.all(
              color: borderColor.withValues(alpha: clampedBorderOpacity),
              width: borderWidth,
            ),
          ),
          child: child,
        ),
      ),
    );
  }
}
