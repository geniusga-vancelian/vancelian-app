import 'package:flutter/widgets.dart';

/// Constantes motion pour [BrandHeroIntroPage] — alignées sur le flux type Revolut.
abstract final class HeroIntroMotion {
  HeroIntroMotion._();

  /// Largeur du logo = fraction de la largeur d’écran (identique splash + intro).
  static const double logoWidthScreenFraction = 0.5;

  /// Ratio largeur / hauteur du viewBox SVG (`assets/logo.svg`, wordmark Vancelian).
  static const double logoSvgViewBoxAspect = 658 / 78;

  static double logoLayoutWidth(double screenWidth) =>
      screenWidth * logoWidthScreenFraction;

  static double logoLayoutHeight(double screenWidth) =>
      logoLayoutWidth(screenWidth) / logoSvgViewBoxAspect;

  /// Arrondi sur la grille des **pixels physiques** : même logique que le rendu iOS
  /// (LaunchScreen contraint 0,5 × largeur), réduit l’écart 1–2 px avec le splash natif.
  static double snapLogoWidthToPhysicalPixels(
    BuildContext context,
    double logicalWidth,
  ) {
    final dpr = MediaQuery.devicePixelRatioOf(context);
    if (dpr <= 0 || !logicalWidth.isFinite) return logicalWidth;
    return (logicalWidth * dpr).round() / dpr;
  }

  /// Wordmark Vancelian — identique splash froid et intro.
  static const String defaultLogoAssetPath = 'assets/logo.svg';

  /// Délai artificiel avant le mouvement logo (après le splash natif). `Duration.zero`
  /// = démarrage dès le premier [addPostFrameCallback] (aucune attente supplémentaire).
  static const Duration splashHold = Duration.zero;

  // --- Timeline maître (un seul [AnimationController]) ---

  /// Durée totale de la séquence intro (logo + fondu image + accordéon du voile).
  static const int introTimelineTotalMs = 2000;

  /// Montée du logo : 0 → 1000 ms (première moitié de [introTimelineTotalMs]).
  static const int logoMoveDurationMs = 1000;

  /// Le fondu de l’image démarre à 70 % de la montée du logo : 700 ms.
  static const int imageFadeStartMs = 700;

  /// Durée du fondu image jusqu’à opacité 1 : 1000 ms (700 → 1700 ms).
  static const int imageFadeDurationMs = 1000;

  /// Pic du voile noir (phase 1) et fin d’accordéon (phase 2), en alpha 0–1.
  static const double dimPhase1PeakOpacity = 0.7;
  static const double dimPhase2EndOpacity = 0.2;

  /// Fin de la montée logo sur la timeline normalisée [0, 1].
  static double get logoMoveEndFraction =>
      logoMoveDurationMs / introTimelineTotalMs;

  /// Début / fin du fondu image sur la timeline normalisée [0, 1].
  static double get imageFadeStartFraction =>
      imageFadeStartMs / introTimelineTotalMs;

  static double get imageFadeEndFraction =>
      (imageFadeStartMs + imageFadeDurationMs) / introTimelineTotalMs;

  /// Durée du contrôleur maître (logo + image + voile synchronisés).
  static const Duration introMasterDuration =
      Duration(milliseconds: introTimelineTotalMs);

  /// Translation logo (centre → haut). Alignée sur une transition lisible sans précipitation.
  static const Duration logoMove = Duration(milliseconds: logoMoveDurationMs);

  static const Curve logoCurve = Curves.easeOutCubic;

  /// Courbe du fondu image sur son intervalle [imageFadeStartFraction, imageFadeEndFraction].
  static const Curve imageFadeCurve = Curves.easeOutCubic;

  /// Voile noir : opacité 0 → [dimPhase1PeakOpacity] sur [logoMoveDurationMs], puis
  /// [dimPhase1PeakOpacity] → [dimPhase2EndOpacity] sur les [imageFadeDurationMs] restants.
  ///
  /// [t] est la valeur du contrôleur maître dans [0, 1] ([introTimelineTotalMs]).
  static double accordionDimOpacity(double t) {
    if (t <= 0) return 0;
    if (t >= 1) return dimPhase2EndOpacity;
    final endPhase1 = logoMoveEndFraction;
    if (t <= endPhase1) {
      return dimPhase1PeakOpacity * (t / endPhase1);
    }
    final u = (t - endPhase1) / (1.0 - endPhase1);
    return dimPhase1PeakOpacity +
        (dimPhase2EndOpacity - dimPhase1PeakOpacity) * u;
  }

  /// Opacité effective du voile : l’accordéon est calé sur [dimPhase1PeakOpacity] ;
  /// [heroDimOverlayMaxOpacity] règle l’intensité (pic = cette valeur quand l’accordéon est au pic).
  static double accordionDimOpacityScaled(
    double t,
    double heroDimOverlayMaxOpacity,
  ) {
    if (heroDimOverlayMaxOpacity <= 0) return 0;
    return accordionDimOpacity(t) *
        (heroDimOverlayMaxOpacity / dimPhase1PeakOpacity);
  }

  /// Après fin du mouvement logo (t = [logoMoveEndFraction]) : début du fondu des boutons.
  static const Duration controlsDelayAfterLogo = Duration.zero;

  /// Fondu d’apparition des CTA après la première animation (logo).
  static const Duration controlsFadeIn = Duration(milliseconds: 500);

  static const Curve controlsCurve = Curves.easeOutCubic;

  /// Centre du logo final : offset sous la safe area top (px).
  static const double logoFinalOffsetBelowSafeTop = 40;
}
