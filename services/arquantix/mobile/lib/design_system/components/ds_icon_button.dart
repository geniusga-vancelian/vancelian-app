import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';

/// Variante Figma `IconButton` (module design-system).
enum DsIconButtonVariant {
  /// Fond blanc, ombre légère.
  standard,

  /// Fond #6155F5 (secondaire Figma).
  primary,
}

/// Bouton circulaire 40×40 avec ombre — export Figma / ZIP `IconButton`.
class DsIconButton extends StatelessWidget {
  const DsIconButton({
    super.key,
    required this.icon,
    this.variant = DsIconButtonVariant.standard,
    this.onPressed,
    this.tooltip,
    this.semanticLabel,
  });

  final Widget icon;
  final DsIconButtonVariant variant;
  final VoidCallback? onPressed;
  final String? tooltip;
  final String? semanticLabel;

  static const double _size = 40;

  static const BoxShadow _shadow = BoxShadow(
    color: Color(0x1F000000),
    blurRadius: 20,
    offset: Offset(0, 0),
  );

  @override
  Widget build(BuildContext context) {
    final bg = switch (variant) {
      DsIconButtonVariant.standard => AppColors.white,
      DsIconButtonVariant.primary => AppColors.indigo,
    };

    final button = Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onPressed,
        customBorder: const CircleBorder(),
        child: Ink(
          width: _size,
          height: _size,
          decoration: BoxDecoration(
            color: bg,
            shape: BoxShape.circle,
            boxShadow: const [_shadow],
          ),
          child: Center(child: icon),
        ),
      ),
    );

    Widget result = button;
    if (semanticLabel != null) {
      result = Semantics(
        label: semanticLabel,
        button: true,
        child: result,
      );
    }
    if (tooltip != null) {
      result = Tooltip(message: tooltip!, child: result);
    }
    return result;
  }
}
