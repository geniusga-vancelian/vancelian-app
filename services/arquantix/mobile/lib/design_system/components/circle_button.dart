import 'dart:ui';

import 'package:flutter/material.dart';

import '../atoms/atoms.dart';

/// Variante visuelle du [CircleButton].
enum CircleButtonVariant {
  /// Fond indigo, icône et label blancs.
  primary,

  /// Fond glass (darkOpacity30), icône et label blancs.
  glass,

  /// Fond blanc, icône et label noirs.
  white,

  /// Fond bleu info (#0088FF), icône blanche, label noir.
  info,
}

/// Taille du [CircleButton].
enum CircleButtonSize {
  /// Disque 56px, icône 24px — forme pill si [CircleButtonVariant.primary].
  large,

  /// Disque 56px, icône 24px — toujours circulaire.
  medium,

  /// Disque 32px, icône 18px.
  small,
}

/// Bouton circulaire avec icône et label en dessous.
///
/// Figma spec — 3 tailles × 4 variantes.
/// Le paramètre legacy [isPrimary] est conservé pour compatibilité :
/// s'il est fourni sans [variant], il est mappé vers
/// [CircleButtonVariant.primary] / [CircleButtonVariant.glass].
class CircleButton extends StatelessWidget {
  final Widget icon;
  final String label;
  final CircleButtonVariant? variant;
  final CircleButtonSize buttonSize;
  final double? primaryWidth;
  final VoidCallback? onPressed;

  @Deprecated('Use variant instead')
  final bool isPrimary;

  const CircleButton({
    super.key,
    required this.icon,
    required this.label,
    this.variant,
    this.buttonSize = CircleButtonSize.large,
    this.isPrimary = false,
    this.primaryWidth,
    this.onPressed,
  });

  static const double _defaultPrimaryWidth = 106;
  static const double _blur = 12;
  static const double _labelFontSize = 13;
  static const double _labelMinHeight = _labelFontSize;
  static const double _gapIconToLabel = AppSpacing.s1; // 4px below disc
  static const double _labelTopPad = AppSpacing.s1;    // 4px above text
  static const double _labelOverflow = 20;

  CircleButtonVariant get _effectiveVariant =>
      variant ?? (isPrimary ? CircleButtonVariant.primary : CircleButtonVariant.glass);

  double get _iconContainerSize => switch (buttonSize) {
        CircleButtonSize.large => 56,
        CircleButtonSize.medium => 56,
        CircleButtonSize.small => 32,
      };

  Color get _backgroundColor => switch (_effectiveVariant) {
        CircleButtonVariant.primary => AppColors.indigo,
        CircleButtonVariant.glass => AppColors.darkOpacity30,
        CircleButtonVariant.white => AppColors.white,
        CircleButtonVariant.info => AppColors.semanticInfo,
      };

  Color get _labelColor => switch (_effectiveVariant) {
        CircleButtonVariant.primary || CircleButtonVariant.glass => AppColors.white,
        CircleButtonVariant.white || CircleButtonVariant.info => AppColors.black,
      };

  bool get _isPill =>
      _effectiveVariant == CircleButtonVariant.primary &&
      buttonSize == CircleButtonSize.large;

  @override
  Widget build(BuildContext context) {
    final labelStyle = AppTypography.bodySmEmphasized.copyWith(
      color: _labelColor,
      fontSize: _labelFontSize,
      height: 1.0,
      leadingDistribution: TextLeadingDistribution.even,
    );
    final containerHeight = _iconContainerSize;
    final containerWidth =
        _isPill ? (primaryWidth ?? _defaultPrimaryWidth) : _iconContainerSize;
    final labelWidth = containerWidth + _labelOverflow;

    return GestureDetector(
      onTap: onPressed,
      behavior: HitTestBehavior.opaque,
      child: SizedBox(
        width: containerWidth,
        child: Stack(
          clipBehavior: Clip.none,
          alignment: Alignment.topCenter,
          children: [
            Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(AppRadius.full),
                  child: BackdropFilter(
                    filter: ImageFilter.blur(sigmaX: _blur, sigmaY: _blur),
                    child: Container(
                      width: containerWidth,
                      height: containerHeight,
                      decoration: BoxDecoration(
                        color: _backgroundColor,
                        borderRadius: BorderRadius.circular(AppRadius.full),
                      ),
                      child: Center(child: icon),
                    ),
                  ),
                ),
                const SizedBox(height: _gapIconToLabel + _labelTopPad),
                ConstrainedBox(
                  constraints:
                      const BoxConstraints(minHeight: _labelMinHeight),
                  child: const SizedBox.shrink(),
                ),
              ],
            ),
            Positioned(
              top: containerHeight + _gapIconToLabel + _labelTopPad,
              left: -_labelOverflow / 2,
              width: labelWidth,
              child: ConstrainedBox(
                constraints:
                    const BoxConstraints(minHeight: _labelMinHeight),
                child: Text(
                  label,
                  textAlign: TextAlign.center,
                  style: labelStyle,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Élément pour [CircleButtonRow].
class CircleButtonItem {
  const CircleButtonItem({
    required this.icon,
    required this.label,
    this.onTap,
    this.isPrimary = false,
    this.variant,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @Deprecated('Use variant instead')
  final bool isPrimary;

  final CircleButtonVariant? variant;
}

/// Ligne de [CircleButton] répartis dans une grille de 4 colonnes égales.
///
/// La largeur totale est divisée en 4 slots de même largeur. Chaque bouton
/// est centré dans son slot. Si le nombre de boutons est inférieur à 4,
/// les slots occupés sont centrés horizontalement dans la rangée.
class CircleButtonRow extends StatelessWidget {
  const CircleButtonRow({
    super.key,
    required this.items,
    this.iconColor = AppColors.white,
    this.buttonSize = CircleButtonSize.large,
  });

  final List<CircleButtonItem> items;
  final Color iconColor;
  final CircleButtonSize buttonSize;

  static const double _slotCount = 4;
  static const double _primaryWidthRatio = 1.0;

  @override
  Widget build(BuildContext context) {
    final iconSize = buttonSize == CircleButtonSize.small ? 18.0 : 24.0;

    return LayoutBuilder(
      builder: (context, constraints) {
        final availableWidth = constraints.maxWidth.isFinite
            ? constraints.maxWidth
            : MediaQuery.sizeOf(context).width;
        final slotWidth = availableWidth / _slotCount;
        final pillWidth = (slotWidth * _primaryWidthRatio)
            .clamp(0.0, CircleButton._defaultPrimaryWidth);

        return Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            for (int i = 0; i < items.length; i++)
              SizedBox(
                width: slotWidth,
                child: Center(
                  child: CircleButton(
                    icon: Icon(items[i].icon, color: iconColor, size: iconSize),
                    label: items[i].label,
                    variant: items[i].variant,
                    buttonSize: buttonSize,
                    isPrimary: items[i].isPrimary,
                    primaryWidth: pillWidth,
                    onPressed: items[i].onTap,
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}
