import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import 'hero_intro_motion.dart';

/// Logo marque — **même largeur** partout (splash froid + [BrandHeroIntroPage]) :
/// [HeroIntroMotion.logoWidthScreenFraction] × largeur d’écran.
///
/// [ColorFilter] (srcIn) pour le rendu fiable du wordmark (`currentColor` dans le SVG).
class SplashBrandLogo extends StatelessWidget {
  const SplashBrandLogo({
    super.key,
    this.color,
    this.assetPath = HeroIntroMotion.defaultLogoAssetPath,
    this.logoWidth,
    this.screenWidth,
    this.logoWidthScreenFraction = HeroIntroMotion.logoWidthScreenFraction,
  });

  final Color? color;
  final String assetPath;
  final double? logoWidth;
  final double? screenWidth;
  final double logoWidthScreenFraction;

  @override
  Widget build(BuildContext context) {
    final c = color ?? const Color(0xFF000000);
    return LayoutBuilder(
      builder: (context, constraints) {
        final w = logoWidth ?? _widthPx(context, constraints);
        final h = w / HeroIntroMotion.logoSvgViewBoxAspect;
        return SvgPicture.asset(
          assetPath,
          width: w,
          height: h,
          fit: BoxFit.contain,
          alignment: Alignment.center,
          allowDrawingOutsideViewBox: true,
          clipBehavior: Clip.none,
          colorFilter: ColorFilter.mode(c, BlendMode.srcIn),
        );
      },
    );
  }

  double _widthPx(BuildContext context, BoxConstraints constraints) {
    double sw = screenWidth ?? 0;
    if (sw <= 0) {
      final cw = constraints.maxWidth;
      if (cw.isFinite && cw > 0 && cw < double.infinity) {
        sw = cw;
      } else {
        sw = MediaQuery.sizeOf(context).width;
      }
    }
    final safe = sw > 0 ? sw : 400.0;
    final raw = safe * logoWidthScreenFraction;
    return HeroIntroMotion.snapLogoWidthToPhysicalPixels(context, raw);
  }
}
