import 'package:flutter/material.dart';

import 'transaction_tile.dart';
import 'transaction_module.dart';

/// Icône dans un carré à coins arrondis (pour le module marketing).
/// Taille volontairement plus petite que l’avatar des transactions (44px) pour différencier visuellement.
class _RoundedSquareIcon extends StatelessWidget {
  const _RoundedSquareIcon({
    required this.icon,
    required this.backgroundColor,
    this.iconColor = Colors.white,
    this.size = 38,
    this.iconSize,
    this.borderRadius = 10,
  });

  final IconData icon;
  final Color backgroundColor;
  final Color iconColor;
  final double size;
  final double? iconSize;
  final double borderRadius;

  @override
  Widget build(BuildContext context) {
    final iSize = iconSize ?? size * 0.55;
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(borderRadius),
      ),
      alignment: Alignment.center,
      child: Icon(icon, size: iSize, color: iconColor),
    );
  }
}

/// Module marketing : une seule row type transaction (blanc, titre + sous-titre à gauche, caret à droite).
/// Titre jusqu'à 2 lignes, sous-titre jusqu'à 3 lignes. Icône dans un carré arrondi.
class MarketingModule extends StatelessWidget {
  const MarketingModule({
    super.key,
    required this.title,
    required this.subtitle,
    this.onTap,
    this.icon = Icons.savings_rounded,
    this.iconBackgroundColor = Colors.orange,
    this.margin,
  });

  /// Texte principal (ligne du haut, jusqu'à 2 lignes).
  final String title;
  /// Texte secondaire (ligne du bas, jusqu'à 3 lignes).
  final String subtitle;
  /// Callback au tap sur la row (navigation ou action).
  final VoidCallback? onTap;
  /// Icône à gauche (défaut : tirelire).
  final IconData icon;
  /// Couleur du fond du carré arrondi.
  final Color iconBackgroundColor;
  /// Marge extérieure. Si null, [TransactionModule] utilise sa marge par défaut.
  final EdgeInsetsGeometry? margin;

  /// Rayon des coins du module blanc (aligné sur le module Transactions, ex. 24).
  static const double moduleBorderRadius = 24;

  @override
  Widget build(BuildContext context) {
    return TransactionModule(
      margin: margin,
      borderRadius: moduleBorderRadius,
      children: [
        TransactionTile(
          avatar: _RoundedSquareIcon(
            icon: icon,
            backgroundColor: iconBackgroundColor,
            iconColor: Colors.white,
          ),
          title: title,
          subtitle: subtitle,
          titleMaxLines: 2,
          subtitleMaxLines: 3,
          showChevron: true,
          onTap: onTap,
        ),
      ],
    );
  }
}
