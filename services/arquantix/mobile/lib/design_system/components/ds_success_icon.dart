import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/kalai_icons.dart';
import 'kalai_icon.dart';

/// Pastille verte compacte avec crochet blanc — indicateur de succès (liste, statut inline).
///
/// Utilise [AppColors.semanticPositive] (aligné Figma / sémantique « positive »).
///
/// **Centrage optique** : la glyph KALAI `KalaiIcons.check` apparaît
/// très légèrement haute dans sa bounding box (la pointe haute de la coche
/// remonte plus que sa base ne descend, biais visible dès que `size <= 20`).
/// On la pousse de `size / 32` px vers le bas (≈ 0,5 px à 16 px) via
/// [Transform.translate] — sans changer la dimension du widget — pour que la
/// coche apparaisse parfaitement centrée verticalement dans le disque.
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
    final opticalNudge = size / 32; // 0.5 px à size = 16, 1 px à size = 32
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
        child: Transform.translate(
          offset: Offset(0, opticalNudge),
          child: KalaiIcon(
            KalaiIcons.check,
            size: iconSize,
            color: Colors.white,
          ),
        ),
      ),
    );
  }
}

/// Item « bullet » : pastille [DsSuccessIcon] à **gauche** + texte à droite,
/// alignement vertical sur la **première ligne** du texte (et pas sur le top
/// de la `Row`, qui ferait flotter l'avatar trop haut).
///
/// Pattern utilisé : `Row(crossAxisAlignment: start)` + colonne gauche fixée à
/// la **hauteur d'une ligne du texte** (`fontSize * height`) avec l'avatar
/// centré dedans → l'icône est calée pile sur le centre vertical de la 1re
/// ligne, quel que soit le nombre de lignes du texte (le texte continue de
/// wrapper sous l'avatar dans une gouttière propre).
///
/// Utilisé notamment par le module `BULLET_LIST` côté détail d'article.
class DsSuccessBulletItem extends StatelessWidget {
  const DsSuccessBulletItem({
    required this.text,
    required this.style,
    super.key,
    this.iconSize = 16,
    this.gap = AppSpacing.s2,
    this.semanticsLabel,
  });

  final String text;
  final TextStyle style;
  final double iconSize;
  final double gap;
  final String? semanticsLabel;

  @override
  Widget build(BuildContext context) {
    /// Hauteur d'une ligne de texte (fontSize × height). Si `style.height` est
    /// `null`, on retombe sur 1.0 (cohérent avec le rendu Flutter par défaut).
    final fontSize = style.fontSize ?? 14;
    final lineHeight = fontSize * (style.height ?? 1.0);

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          height: lineHeight,
          child: Center(child: DsSuccessIcon(size: iconSize)),
        ),
        SizedBox(width: gap),
        Expanded(
          child: Text(
            text,
            style: style,
            semanticsLabel: semanticsLabel,
          ),
        ),
      ],
    );
  }
}
