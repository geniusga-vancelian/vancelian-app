import 'package:flutter/material.dart';

import 'hero_intro_motion.dart';

/// Configuration du hero « un seul écran » : fond constant + image ou vidéo optionnelle + overlay + logo + UI.
///
/// Si [useHeroVideo] est `true` et qu’une source vidéo est définie ([heroVideoAssetPath] ou
/// [networkHeroVideoUrl]), la vidéo remplace l’image — **même** fondu d’opacité que l’image
/// ([HeroIntroMotion] sur le contrôleur maître).
///
/// Priorité image (si pas de vidéo active) : [imageAssetPath] → [networkImageUrl] → aucun.
class BrandHeroIntroConfig {
  const BrandHeroIntroConfig({
    this.posterAssetPath,
    this.imageAssetPath,
    this.networkImageUrl,
    /// Active la vidéo de fond (tests / feature flag). Sans source vidéo valide, repli sur l’image.
    this.useHeroVideo = false,
    this.heroVideoAssetPath,
    this.networkHeroVideoUrl,
    this.logoAssetPath = HeroIntroMotion.defaultLogoAssetPath,
    this.logoWidthScreenFraction = HeroIntroMotion.logoWidthScreenFraction,
    this.splashBackgroundColor = Colors.white,
    this.logoColorSplash,
    this.logoColorHero = Colors.white,
    this.skipIntro = false,
    /// Après un splash froid ([AppLaunchRoot]), ne pas ré-attendre [HeroIntroMotion.splashHold].
    this.skipSplashHoldAfterColdLaunch = false,
    /// Intensité du voile (pic de l’accordéon = [HeroIntroMotion.dimPhase1PeakOpacity] × ratio).
    /// 0 = désactivé ; 0,7 ≈ pic à 70 % et fin ≈ 20 % (voir accordéon dans [HeroIntroMotion]).
    this.heroDimOverlayMaxOpacity = 0.7,
    this.pendingMediaResolution = false,
    /// Bonus : tap sur le fond avant l’apparition des contrôles pour terminer l’animation.
    this.skipIntroOnTap = false,
    /// `true` tant que [AppLaunchRoot] résout la session : logo seul, pas d’anim (évite le clignotement).
    this.bootstrapPending = false,
  });

  final String? posterAssetPath;
  final String? imageAssetPath;
  final String? networkImageUrl;

  final bool useHeroVideo;
  final String? heroVideoAssetPath;
  final String? networkHeroVideoUrl;

  final String logoAssetPath;
  final double logoWidthScreenFraction;

  double logoLayoutWidth(double screenWidth) =>
      screenWidth * logoWidthScreenFraction;

  double logoLayoutHeight(double screenWidth) =>
      logoLayoutWidth(screenWidth) / HeroIntroMotion.logoSvgViewBoxAspect;

  /// Inchangé pendant toute la séquence (pas de gris → blanc).
  final Color splashBackgroundColor;

  final Color? logoColorSplash;
  final Color logoColorHero;

  final bool skipIntro;
  final bool skipSplashHoldAfterColdLaunch;

  final double heroDimOverlayMaxOpacity;

  final bool pendingMediaResolution;

  final bool skipIntroOnTap;

  final bool bootstrapPending;

  /// Source vidéo exploitable (asset ou URL HTTPS).
  bool get hasHeroVideoSource =>
      (heroVideoAssetPath != null && heroVideoAssetPath!.trim().isNotEmpty) ||
      (networkHeroVideoUrl != null && networkHeroVideoUrl!.trim().isNotEmpty);

  /// Vidéo réellement utilisée à la place de l’image.
  bool get useHeroVideoLayer => useHeroVideo && hasHeroVideoSource;

  bool get hasStaticImage =>
      (imageAssetPath != null && imageAssetPath!.trim().isNotEmpty) ||
      (networkImageUrl != null && networkImageUrl!.trim().isNotEmpty);
}
