import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';

/// Pastille verte compacte avec crochet blanc — indicateur de succès (liste, statut inline).
///
/// Utilise [AppColors.semanticPositive] (aligné Figma / sémantique « positive »).
class DsSuccessIcon extends StatelessWidget {
  const DsSuccessIcon({
    super.key,
    this.size = 16,
  });

  /// Diamètre du disque (px logiques).
  final double size;

  @override
  Widget build(BuildContext context) {
    final iconSize = size * 0.625;
    return Semantics(
      label: 'Succès',
      child: Container(
        width: size,
        height: size,
        decoration: const BoxDecoration(
          color: AppColors.semanticPositive,
          shape: BoxShape.circle,
        ),
        alignment: Alignment.center,
        child: Icon(
          Icons.check_rounded,
          size: iconSize,
          color: Colors.white,
        ),
      ),
    );
  }
}
