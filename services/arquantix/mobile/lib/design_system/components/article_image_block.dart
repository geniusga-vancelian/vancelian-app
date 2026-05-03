import 'package:flutter/material.dart';

import '../atoms/atoms.dart';
import 'kalai_icon.dart';

/// Image d'article avec légende optionnelle.
///
/// Figma: image pleine largeur, borderRadius 16, légende italique 13px gray
/// alignée à droite, gap 8px.
///
/// [borderColor] ajoute un trait de 2px autour de l'image (charts financiers).
/// Valeurs Figma : light #E5E5EA, medium #D1D1D6, dark #C7C7CC.
class ArticleImageBlock extends StatelessWidget {
  final String imageUrl;
  final String? caption;
  final double? height;
  final BoxFit fit;
  final Color? borderColor;
  final double? aspectRatio;

  static const Color borderLight = Color(0xFFE5E5EA);
  static const Color borderMedium = Color(0xFFD1D1D6);
  static const Color borderDark = Color(0xFFC7C7CC);

  const ArticleImageBlock({
    super.key,
    required this.imageUrl,
    this.caption,
    this.height,
    this.fit = BoxFit.cover,
    this.borderColor,
    this.aspectRatio,
  });

  @override
  Widget build(BuildContext context) {
    Widget imageWidget = Image.network(
      imageUrl,
      fit: fit,
      errorBuilder: (_, __, ___) => Container(
        height: height ?? 193,
        decoration: BoxDecoration(
          color: AppColors.placeholderBg,
          borderRadius: BorderRadius.circular(AppRadius.lg),
        ),
        alignment: Alignment.center,
        child: const KalaiIcon(
          KalaiIcons.photo,
          size: 40,
          color: AppColors.placeholderIcon,
        ),
      ),
    );

    Widget container;
    if (aspectRatio != null) {
      container = AspectRatio(
        aspectRatio: aspectRatio!,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          child: imageWidget,
        ),
      );
    } else {
      container = ClipRRect(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        child: SizedBox(
          width: double.infinity,
          height: height,
          child: imageWidget,
        ),
      );
    }

    if (borderColor != null) {
      container = DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          border: Border.all(color: borderColor!, width: 2),
        ),
        child: container,
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        container,
        if (caption != null && caption!.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.s2),
          Text(
            caption!,
            style: AppTypography.bodySmItalic.copyWith(
              color: AppColors.gray,
            ),
            textAlign: TextAlign.right,
          ),
        ],
      ],
    );
  }
}

/// Bloc vidéo avec image de couverture + bouton play.
///
/// Figma: image rounded 16, height 193, overlay 20%, bouton play 61px circle.
class ArticleVideoBlock extends StatelessWidget {
  final String thumbnailUrl;
  final VoidCallback? onPlay;
  final double height;

  const ArticleVideoBlock({
    super.key,
    required this.thumbnailUrl,
    this.onPlay,
    this.height = 193,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onPlay,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        clipBehavior: Clip.hardEdge,
        child: SizedBox(
          width: double.infinity,
          height: height,
          child: Stack(
            fit: StackFit.expand,
            clipBehavior: Clip.hardEdge,
            children: [
              Positioned.fill(
                child: Image.network(
                  thumbnailUrl,
                  fit: BoxFit.cover,
                  alignment: Alignment.center,
                  width: double.infinity,
                  height: double.infinity,
                  errorBuilder: (_, __, ___) => Container(
                    color: AppColors.placeholderBg,
                    alignment: Alignment.center,
                    child: const KalaiIcon(
                      KalaiIcons.video,
                      size: 40,
                      color: AppColors.placeholderIcon,
                    ),
                  ),
                ),
              ),
              Positioned.fill(
                child: IgnorePointer(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.2),
                    ),
                  ),
                ),
              ),
              Center(child: _PlayButton()),
            ],
          ),
        ),
      ),
    );
  }
}

class _PlayButton extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 61,
      height: 61,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(color: AppColors.white, width: 4),
      ),
      alignment: Alignment.center,
      child: const KalaiIcon(KalaiIcons.play, color: AppColors.white, size: 32),
    );
  }
}

/// Galerie horizontale d'images avec sliding (comme BlogALaUne).
///
/// Affiche ~1.2 images visibles avec peek sur l'image suivante.
/// Gère son propre padding horizontal pour être pleine largeur.
class ArticleGalleryBlock extends StatelessWidget {
  final List<String> imageUrls;
  final double imageHeight;
  final double horizontalPadding;

  static const double _gap = AppSpacing.s2;
  static const double _visibleCards = 1.15;

  const ArticleGalleryBlock({
    super.key,
    required this.imageUrls,
    this.imageHeight = 175,
    this.horizontalPadding = AppSpacing.s4,
  });

  @override
  Widget build(BuildContext context) {
    if (imageUrls.isEmpty) return const SizedBox.shrink();

    final screenWidth = MediaQuery.sizeOf(context).width;
    final availableWidth = screenWidth - horizontalPadding * 2;
    final cardWidth = imageUrls.length == 1
        ? availableWidth
        : (availableWidth - _gap) / _visibleCards;

    return SizedBox(
      height: imageHeight,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: EdgeInsets.symmetric(horizontal: horizontalPadding),
        itemCount: imageUrls.length,
        separatorBuilder: (_, __) => const SizedBox(width: _gap),
        itemBuilder: (_, index) => ClipRRect(
          borderRadius: BorderRadius.circular(AppRadius.lg),
          child: SizedBox(
            width: cardWidth,
            height: imageHeight,
            child: Image.network(
              imageUrls[index],
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => Container(
                color: AppColors.placeholderBg,
                alignment: Alignment.center,
                child: const KalaiIcon(
                  KalaiIcons.photo,
                  size: 40,
                  color: AppColors.placeholderIcon,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
