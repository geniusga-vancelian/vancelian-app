import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Taille de hauteur du module: small (-50%), medium (-20%), large (100%).
enum MarktingCardLargePortraitHeight { small, medium, large }

/// 3e carte marketing DS: visuel hero uniquement (image + titre overlay).
class MarktingCardLargePortrait extends StatelessWidget {
  static const double _baseHeight = 560;

  const MarktingCardLargePortrait({
    super.key,
    this.imageUrl,
    this.imageAssetPath,
    required this.title,
    this.onTap,
    this.height,
    this.heightSize = MarktingCardLargePortraitHeight.large,
    this.borderRadius = 28,
  });

  final String? imageUrl;
  final String? imageAssetPath;
  final String title;
  final VoidCallback? onTap;
  final double? height;
  final MarktingCardLargePortraitHeight heightSize;
  final double borderRadius;

  double get _effectiveHeight {
    if (height != null) return height!;
    switch (heightSize) {
      case MarktingCardLargePortraitHeight.small:
        return _baseHeight * 0.5;
      case MarktingCardLargePortraitHeight.medium:
        return _baseHeight * 0.8;
      case MarktingCardLargePortraitHeight.large:
        return _baseHeight;
    }
  }

  @override
  Widget build(BuildContext context) {
    final card = _HeroVisual(
      imageUrl: imageUrl,
      imageAssetPath: imageAssetPath,
      title: title,
      height: _effectiveHeight,
      borderRadius: borderRadius,
    );

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(borderRadius),
        child: card,
      ),
    );
  }
}

class _HeroVisual extends StatelessWidget {
  const _HeroVisual({
    required this.imageUrl,
    required this.imageAssetPath,
    required this.title,
    required this.height,
    required this.borderRadius,
  });

  final String? imageUrl;
  final String? imageAssetPath;
  final String title;
  final double height;
  final double borderRadius;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: Container(
        height: height,
        color: const Color(0xFF101116),
        child: Stack(
          fit: StackFit.expand,
          children: [
            if ((imageAssetPath ?? '').trim().isNotEmpty)
              Image.asset(
                imageAssetPath!,
                fit: BoxFit.cover,
                alignment: Alignment.bottomCenter,
                errorBuilder: (_, __, ___) => const SizedBox.shrink(),
              )
            else if ((imageUrl ?? '').trim().isNotEmpty)
              Image.network(
                imageUrl!,
                fit: BoxFit.cover,
                alignment: Alignment.bottomCenter,
                errorBuilder: (_, __, ___) => const SizedBox.shrink(),
              ),
            DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    Colors.black.withValues(alpha: 0.35),
                    Colors.transparent,
                    Colors.transparent,
                    Colors.black.withValues(alpha: 0.2),
                  ],
                  stops: const [0, 0.22, 0.76, 1],
                ),
              ),
            ),
            Positioned(
              left: AppSpacing.lg,
              right: AppSpacing.lg,
              top: AppSpacing.xl,
              child: Text(
                title,
                style: AppTypography.pageTitle.copyWith(
                  color: Colors.white,
                  fontSize: (AppTypography.pageTitle.fontSize ?? 30) + 4,
                  fontWeight: FontWeight.w800,
                  height: 1.05,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
