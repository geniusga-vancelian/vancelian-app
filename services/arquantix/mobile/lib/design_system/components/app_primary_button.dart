import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../atoms/app_colors.dart';

/// Variante visuelle du [AppPrimaryButton] — alignée Figma Access / ZIP (4).
enum AppPrimaryButtonVariant {
  /// Fond marque #6155F5, texte blanc.
  primary,

  /// Fond blanc, texte noir (« Not Now » / action secondaire).
  secondary,

  /// Fond noir, texte blanc.
  black,

  /// Fond #AEAEB2, texte blanc.
  gray,

  /// Fond transparent, bordure et texte #6155F5.
  ghost,

  /// Fond #AEAEB2, texte blanc — non interactif.
  disabled,
}

/// Taille du [AppPrimaryButton] — hauteurs Figma sm / md / lg.
enum AppPrimaryButtonSize {
  /// 36px, padding horizontal 24, texte 14px.
  small,

  /// 48px, padding horizontal 40, texte 16px.
  medium,

  /// 56px, padding horizontal 48, texte 18px.
  large,
}

/// Bouton Call-to-Action principal du DS.
///
/// Spécification Figma (extrait module React) :
/// - Forme pill (`StadiumBorder`)
/// - Inter Semi Bold, tracking -0.31
/// - Variantes primary (#6155F5), secondary (blanc + noir), ghost (#6155F5), disabled (#AEAEB2 + blanc)
class AppPrimaryButton extends StatelessWidget {
  const AppPrimaryButton({
    super.key,
    required this.label,
    this.onPressed,
    this.variant = AppPrimaryButtonVariant.primary,
    this.size = AppPrimaryButtonSize.medium,
    this.shrinkWrap = false,
    this.horizontalPadding,
    this.leading,
    this.isLoading = false,
  });

  final String label;
  final VoidCallback? onPressed;
  final AppPrimaryButtonVariant variant;
  final AppPrimaryButtonSize size;
  final bool shrinkWrap;

  /// Si non null, remplace le padding horizontal implicite de [size] (ex. boutons compacts côte à côte).
  final double? horizontalPadding;
  final Widget? leading;

  /// Affiche un indicateur à la place du libellé (même gabarit, pas de saut de layout).
  final bool isLoading;

  static const _letterSpacing = -0.31;

  double get _height => switch (size) {
        AppPrimaryButtonSize.small => 36,
        AppPrimaryButtonSize.medium => 48,
        AppPrimaryButtonSize.large => 56,
      };

  double get _hPadding => switch (size) {
        AppPrimaryButtonSize.small => 24,
        AppPrimaryButtonSize.medium => 40,
        AppPrimaryButtonSize.large => 48,
      };

  double get _fontSize => switch (size) {
        AppPrimaryButtonSize.small => 14,
        AppPrimaryButtonSize.medium => 16,
        AppPrimaryButtonSize.large => 18,
      };

  double get _lineHeight => switch (size) {
        AppPrimaryButtonSize.small => 20 / 14,
        AppPrimaryButtonSize.medium => 21 / 16,
        AppPrimaryButtonSize.large => 24 / 18,
      };

  AppPrimaryButtonVariant get _effectiveVariant {
    if (isLoading) {
      if (variant == AppPrimaryButtonVariant.disabled) {
        return AppPrimaryButtonVariant.disabled;
      }
      return variant;
    }
    if (variant == AppPrimaryButtonVariant.disabled) return variant;
    if (onPressed == null) return AppPrimaryButtonVariant.disabled;
    return variant;
  }

  bool get _isGhost => _effectiveVariant == AppPrimaryButtonVariant.ghost;

  Color get _backgroundColor => switch (_effectiveVariant) {
        AppPrimaryButtonVariant.primary => AppColors.indigo,
        AppPrimaryButtonVariant.secondary => AppColors.white,
        AppPrimaryButtonVariant.black => AppColors.black,
        AppPrimaryButtonVariant.gray => AppColors.semanticNeutral,
        AppPrimaryButtonVariant.ghost => Colors.transparent,
        AppPrimaryButtonVariant.disabled => AppColors.buttonDisabledBg,
      };

  Color get _foregroundColor => switch (_effectiveVariant) {
        AppPrimaryButtonVariant.secondary => AppColors.black,
        AppPrimaryButtonVariant.ghost => AppColors.indigo,
        _ => AppColors.white,
      };

  bool get _isDisabled => _effectiveVariant == AppPrimaryButtonVariant.disabled;

  Color get _spinnerColor => switch (_effectiveVariant) {
        AppPrimaryButtonVariant.secondary => AppColors.indigo,
        AppPrimaryButtonVariant.ghost => AppColors.indigo,
        _ => AppColors.white,
      };

  double get _effectiveHorizontalPadding => horizontalPadding ?? _hPadding;

  @override
  Widget build(BuildContext context) {
    final textStyle = GoogleFonts.inter(
      fontWeight: FontWeight.w600,
      fontSize: _fontSize,
      letterSpacing: _letterSpacing,
      height: _lineHeight,
      color: _foregroundColor,
    );

    final labelChild = Row(
      mainAxisSize: shrinkWrap ? MainAxisSize.min : MainAxisSize.max,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (leading != null && !isLoading) ...[
          leading!,
          const SizedBox(width: 4),
        ],
        if (shrinkWrap)
          Text(label, style: textStyle)
        else
          Expanded(
            child: Text(
              label,
              style: textStyle,
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
      ],
    );

    final child = AnimatedSwitcher(
      duration: const Duration(milliseconds: 220),
      switchInCurve: Curves.easeOut,
      switchOutCurve: Curves.easeIn,
      layoutBuilder: (current, previous) {
        return Stack(
          alignment: Alignment.center,
          clipBehavior: Clip.none,
          children: <Widget>[
            ...previous,
            if (current != null) current,
          ],
        );
      },
      transitionBuilder: (child, animation) {
        return FadeTransition(
          opacity: animation,
          child: child,
        );
      },
      child: isLoading
          ? RepaintBoundary(
              key: const ValueKey<Object>('app_primary_btn_loading'),
              child: SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(
                  strokeWidth: 2.5,
                  color: _spinnerColor,
                ),
              ),
            )
          : RepaintBoundary(
              key: ValueKey<String>('app_primary_btn_$label'),
              child: labelChild,
            ),
    );

    const shape = StadiumBorder();

    if (_isGhost) {
      return SizedBox(
        width: shrinkWrap ? null : double.infinity,
        height: _height,
        child: OutlinedButton(
          onPressed: (isLoading || _isDisabled) ? null : onPressed,
          style: OutlinedButton.styleFrom(
            foregroundColor: AppColors.indigo,
            disabledForegroundColor:
                isLoading ? AppColors.indigo : AppColors.textMuted,
            side: BorderSide(
              color: _isDisabled && !isLoading
                  ? AppColors.buttonDisabledBg
                  : AppColors.indigo,
            ),
            padding: EdgeInsets.symmetric(horizontal: _effectiveHorizontalPadding),
            shape: shape,
            elevation: 0,
            minimumSize: Size.zero,
            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            backgroundColor: Colors.transparent,
          ),
          child: child,
        ),
      );
    }

    return SizedBox(
      width: shrinkWrap ? null : double.infinity,
      height: _height,
      child: FilledButton(
        onPressed: (isLoading || _isDisabled) ? null : onPressed,
        style: FilledButton.styleFrom(
          backgroundColor: _backgroundColor,
          foregroundColor: _foregroundColor,
          disabledBackgroundColor:
              isLoading ? _backgroundColor : AppColors.buttonDisabledBg,
          disabledForegroundColor:
              isLoading ? _foregroundColor : AppColors.buttonDisabledFg,
          padding: EdgeInsets.symmetric(horizontal: _effectiveHorizontalPadding),
          shape: shape,
          elevation: 0,
          minimumSize: Size.zero,
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        ),
        child: child,
      ),
    );
  }
}
