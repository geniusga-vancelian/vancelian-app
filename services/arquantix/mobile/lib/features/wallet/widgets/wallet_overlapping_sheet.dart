import 'package:flutter/material.dart';

import '../../../../ui/theme/app_colors.dart';

/// Contenu qui chevauche le hero (translate vers le haut).
/// Si [useBackground] est true : un conteneur blanc avec ombre (feuille type Revolut).
/// Si false : seul le décalage est appliqué (pas de module blanc au-dessus du contenu).
class WalletOverlappingSheet extends StatelessWidget {
  const WalletOverlappingSheet({
    super.key,
    required this.child,
    this.overlapOffset = -32,
    this.borderRadius = 24,
    this.useBackground = true,
  });

  final Widget child;
  final double overlapOffset;
  final double borderRadius;
  /// false = pas de conteneur blanc, le contenu (ex. WalletsModule) chevauche seul le violet.
  final bool useBackground;

  @override
  Widget build(BuildContext context) {
    final content = useBackground
        ? Container(
            width: double.infinity,
            decoration: BoxDecoration(
              color: AppColors.walletSheetBg,
              borderRadius: BorderRadius.vertical(
                top: Radius.circular(borderRadius),
              ),
              boxShadow: [
                BoxShadow(
                  color: AppColors.walletSheetShadow,
                  blurRadius: 12,
                  offset: const Offset(0, -2),
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.vertical(
                top: Radius.circular(borderRadius),
              ),
              child: child,
            ),
          )
        : child;

    return Transform.translate(
      offset: Offset(0, overlapOffset),
      child: content,
    );
  }
}
