import 'package:flutter/material.dart';

import 'app_primary_button.dart';

/// Action secondaire type Figma Access — [AppPrimaryButton] variante `secondary` (fond blanc, texte noir).
class AppSecondaryButton extends StatelessWidget {
  const AppSecondaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.size = AppPrimaryButtonSize.medium,
    this.shrinkWrap = false,
    this.horizontalPadding,
    this.leading,
  });

  final String label;
  final VoidCallback? onPressed;
  final AppPrimaryButtonSize size;
  final bool shrinkWrap;

  /// Réduit le padding horizontal (ex. deux boutons côte à côte dans le hero).
  final double? horizontalPadding;

  /// Icône à gauche du libellé (même comportement que [AppPrimaryButton.leading]).
  final Widget? leading;

  @override
  Widget build(BuildContext context) {
    return AppPrimaryButton(
      label: label,
      onPressed: onPressed,
      variant: AppPrimaryButtonVariant.secondary,
      size: size,
      shrinkWrap: shrinkWrap,
      horizontalPadding: horizontalPadding,
      leading: leading,
    );
  }
}
