import 'dart:ui';

import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/kalai_icons.dart';
import 'kalai_icon.dart';

/// Variante visuelle du [AppBackButton].
enum AppBackButtonVariant {
  /// Fond blanc, icône noire, ombre portée.
  white,

  /// Fond glass clair (darkOpacity30), icône blanche, backdrop blur.
  glass,

  /// Fond glass sombre (glassOverlay), icône blanche, backdrop blur.
  glassDark,
}

/// Bouton circulaire du DS — retour, menu, actions glass.
///
/// Figma spec:
/// - Default size: 40×40
/// - White variant: bg white, icon black, shadow 0 0 20 rgba(0,0,0,0.12)
/// - Glass variant: bg rgba(235,235,245,0.3), icon white, backdrop blur 12
/// - GlassDark variant: bg rgba(60,60,67,0.6), icon white, backdrop blur 12
class AppBackButton extends StatelessWidget {
  const AppBackButton({
    super.key,
    this.variant = AppBackButtonVariant.white,
    this.size = 40,
    this.onPressed,
    this.icon,
    this.kalaiIcon,
    this.child,
  });

  final AppBackButtonVariant variant;
  final double size;
  final VoidCallback? onPressed;

  /// Icône Material (legacy). Si fournie, prend le pas sur [kalaiIcon].
  final IconData? icon;

  /// Asset SVG d'une icône KALAI (ex: `KalaiIcons.chevronLeft`).
  ///
  /// Utilisé par défaut quand [icon] et [child] sont nuls.
  final String? kalaiIcon;

  /// Contenu libre (prioritaire sur [icon]/[kalaiIcon]). Permet d'afficher un avatar, etc.
  final Widget? child;

  static const double _blur = 12;

  Color get _backgroundColor => switch (variant) {
        AppBackButtonVariant.white => AppColors.white,
        AppBackButtonVariant.glass => AppColors.darkOpacity30,
        AppBackButtonVariant.glassDark => AppColors.glassOverlay,
      };

  Color get _iconColor => switch (variant) {
        AppBackButtonVariant.white => AppColors.black,
        AppBackButtonVariant.glass || AppBackButtonVariant.glassDark =>
          AppColors.white,
      };

  List<BoxShadow>? get _shadow => switch (variant) {
        AppBackButtonVariant.white => const [
            BoxShadow(blurRadius: 20, color: Color(0x1F000000)),
          ],
        _ => null,
      };

  bool get _needsBlur =>
      variant == AppBackButtonVariant.glass ||
      variant == AppBackButtonVariant.glassDark;

  @override
  Widget build(BuildContext context) {
    Widget buildContent() {
      if (child != null) return child!;
      if (icon != null) {
        return Icon(icon, color: _iconColor, size: size * 0.6);
      }
      return KalaiIcon(
        kalaiIcon ?? KalaiIcons.chevronLeft,
        color: _iconColor,
        size: size * 0.6,
      );
    }

    final content = buildContent();

    Widget button = Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: _backgroundColor,
        borderRadius: BorderRadius.circular(AppRadius.full),
        boxShadow: _shadow,
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(AppRadius.full),
        child: InkWell(
          onTap: onPressed,
          borderRadius: BorderRadius.circular(AppRadius.full),
          child: Center(child: content),
        ),
      ),
    );

    if (_needsBlur) {
      button = ClipRRect(
        borderRadius: BorderRadius.circular(AppRadius.full),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: _blur, sigmaY: _blur),
          child: button,
        ),
      );
    }

    return SizedBox(width: size, height: size, child: button);
  }
}
