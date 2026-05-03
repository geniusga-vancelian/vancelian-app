import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../atoms/app_colors.dart';

/// Widget standard pour afficher une icone du jeu **KALAI (line)**.
///
/// Toutes les icones KALAI sont des SVG sur une viewBox `0 0 24 24` avec
/// `fill="currentColor"`. Ce widget applique automatiquement un
/// [ColorFilter] en `srcIn` pour pouvoir teinter l'icone via [color],
/// exactement comme `Icon` de Material.
///
/// Exemple :
/// ```dart
/// KalaiIcon(KalaiIcons.add, size: 24, color: AppColors.indigo)
/// ```
///
/// [size] est appliquee a la fois en largeur et en hauteur. La taille par
/// defaut (`24`) correspond au gabarit natif des SVG, ce qui evite tout
/// rescaling visible.
class KalaiIcon extends StatelessWidget {
  const KalaiIcon(
    this.assetPath, {
    super.key,
    this.size = 24,
    this.color,
    this.semanticLabel,
  });

  /// Chemin de l'asset SVG (ex: `KalaiIcons.add`).
  final String assetPath;

  /// Taille (largeur = hauteur) en pixels logiques. Defaut : `24`.
  final double size;

  /// Couleur de remplissage. Si `null`, on utilise [AppColors.textPrimary].
  ///
  /// Mettez `null` n'est jamais transparent : la couleur des icones est
  /// utilisee partout dans l'app, donc on garantit un fallback explicite.
  final Color? color;

  /// Label d'accessibilite (lu par les lecteurs d'ecran).
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final tint = color ?? AppColors.textPrimary;
    return SvgPicture.asset(
      assetPath,
      width: size,
      height: size,
      colorFilter: ColorFilter.mode(tint, BlendMode.srcIn),
      semanticsLabel: semanticLabel,
      // KALAI est rendu par Flutter SVG sans extras particuliers.
    );
  }
}
