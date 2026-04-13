import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../atoms/app_colors.dart';

/// Variante visuelle du [AppSmallButton].
enum AppSmallButtonVariant {
  /// Fond indigo (#6155F5), texte blanc.
  primary,

  /// Fond noir, texte blanc.
  black,

  /// Fond gris neutre (#AEAEB2), texte blanc.
  gray,

  /// Fond warning light (#FFF4E9), texte warning (#FF8D28).
  warning,

  /// Fond #D1D1D6, texte #8E8E93 — non interactif.
  disabled,
}

/// Bouton CTA compact du DS.
///
/// Figma spec:
/// - Height: 31px
/// - Border radius: 40px
/// - Padding: 12px horizontal, 5px vertical
/// - Backdrop blur: 12px
/// - Inter Bold 12px, line-height 16
class AppSmallButton extends StatelessWidget {
  const AppSmallButton({
    super.key,
    required this.label,
    this.onPressed,
    this.variant = AppSmallButtonVariant.primary,
  });

  final String label;
  final VoidCallback? onPressed;
  final AppSmallButtonVariant variant;

  static const _brandPrimary = Color(0xFF6155F5);
  static const double _blur = 12;
  static const double _height = 31;
  static const double _radius = 40;

  static const _textStyle = TextStyle(
    fontWeight: FontWeight.w700,
    fontSize: 12,
    height: 16 / 12,
  );

  Color get _backgroundColor => switch (variant) {
        AppSmallButtonVariant.primary => _brandPrimary,
        AppSmallButtonVariant.black => AppColors.black,
        AppSmallButtonVariant.gray => AppColors.semanticNeutral,
        AppSmallButtonVariant.warning => AppColors.semanticWarningLight,
        AppSmallButtonVariant.disabled => AppColors.buttonDisabledBg,
      };

  Color get _foregroundColor => switch (variant) {
        AppSmallButtonVariant.warning => AppColors.semanticWarning,
        AppSmallButtonVariant.disabled => AppColors.buttonDisabledFg,
        _ => AppColors.white,
      };

  bool get _isDisabled =>
      variant == AppSmallButtonVariant.disabled || onPressed == null;

  @override
  Widget build(BuildContext context) {
    final style = GoogleFonts.inter(textStyle: _textStyle);

    return ClipRRect(
      borderRadius: BorderRadius.circular(_radius),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: _blur, sigmaY: _blur),
        child: SizedBox(
          height: _height,
          child: FilledButton(
            onPressed: _isDisabled ? null : onPressed,
            style: FilledButton.styleFrom(
              backgroundColor: _backgroundColor,
              foregroundColor: _foregroundColor,
              disabledBackgroundColor: _backgroundColor,
              disabledForegroundColor: _foregroundColor,
              padding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(_radius),
              ),
              elevation: 0,
              minimumSize: Size.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
            child: Text(label, style: style),
          ),
        ),
      ),
    );
  }
}
