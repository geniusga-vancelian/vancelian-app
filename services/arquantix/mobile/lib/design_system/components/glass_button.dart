import 'dart:ui';

import 'package:flutter/material.dart';

import '../atoms/atoms.dart';

/// Variante visuelle du [GlassButton].
///
/// - [GlassButtonVariant.dark] : fond sombre semi-transparent (`glassOverlay`)
///   pour les overlays image type InvestmentCard, PropertyCard.
/// - [GlassButtonVariant.light] : fond clair semi-transparent (`darkOpacity30`)
///   pour les barres de navigation sur fond photographique.
enum GlassButtonVariant { dark, light }

/// Bouton circulaire avec effet glassmorphism (backdrop blur).
///
/// Utilisé principalement sur des arrière-plans photographiques (PropertyCard,
/// headers immersifs, barres de navigation).
class GlassButton extends StatelessWidget {
  final Widget icon;
  final double size;
  final VoidCallback? onPressed;
  final GlassButtonVariant variant;

  const GlassButton({
    super.key,
    required this.icon,
    this.size = 40,
    this.onPressed,
    this.variant = GlassButtonVariant.dark,
  });

  static const double _blur = 12;

  @override
  Widget build(BuildContext context) {
    final bgColor = variant == GlassButtonVariant.light
        ? AppColors.darkOpacity30
        : AppColors.glassOverlay;

    return SizedBox(
      width: size,
      height: size,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(AppRadius.full),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: _blur, sigmaY: _blur),
          child: Material(
            color: bgColor,
            borderRadius: BorderRadius.circular(AppRadius.full),
            child: InkWell(
              onTap: onPressed,
              borderRadius: BorderRadius.circular(AppRadius.full),
              child: Center(child: icon),
            ),
          ),
        ),
      ),
    );
  }
}
