import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_spacing.dart';
import 'app_section_title.dart';
import 'app_skeleton.dart';

/// Skeleton du module « Vancelian News » / Blog à la une : cartes grises en **scroll horizontal**
/// (même logique de largeur que [BlogALaUne], ~1,2 carte visible).
class VancelianNewsModuleSkeleton extends StatelessWidget {
  const VancelianNewsModuleSkeleton({
    super.key,
    required this.title,
    this.cardCount = 2,
  });

  final String title;
  final int cardCount;

  static const double _imageBlockHeight = 167;
  static const double _cardRadius = 16;

  /// Aligné sur [BlogALaUne] : marge page, gap titre → carousel, peek 2e carte.
  static const double _horizontalMargin = AppSpacing.xl;
  static const double _shadowPaddingVertical = AppSpacing.sm;
  static const double _titleToCarouselGap = AppSpacing.md - _shadowPaddingVertical;
  static const double _visibleCardsCount = 1.2;

  /// Hauteur indicative alignée sur la carte [NewsCard] (image + texte + meta).
  static const double _carouselBlockHeight =
      167 + 8 + 66 + 8 + 18 + 16 + _shadowPaddingVertical;

  @override
  Widget build(BuildContext context) {
    final n = cardCount < 2 ? 2 : cardCount;
    final screenWidth = MediaQuery.sizeOf(context).width;
    const gap = AppSpacing.md;
    final availableWidth = screenWidth - _horizontalMargin * 2;
    final cardWidth = (availableWidth - gap) / _visibleCardsCount;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
          child: AppSectionTitle(title),
        ),
        const SizedBox(height: _titleToCarouselGap),
        SizedBox(
          height: _carouselBlockHeight,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.only(
              left: _horizontalMargin,
              right: _horizontalMargin,
              top: _shadowPaddingVertical,
            ),
            itemCount: n,
            separatorBuilder: (_, __) => const SizedBox(width: gap),
            itemBuilder: (context, index) {
              return SizedBox(
                width: cardWidth,
                child: _skeletonCard(),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _skeletonCard() {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(_cardRadius),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.08),
            blurRadius: 16,
            spreadRadius: -4,
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: AppSkeleton(
              height: _imageBlockHeight,
              borderRadius: AppRadius.md,
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(
                  width: double.infinity,
                  child: AppSkeleton(height: 14, borderRadius: AppRadius.sm),
                ),
                const SizedBox(height: AppSpacing.sm),
                SizedBox(
                  width: double.infinity,
                  child: AppSkeleton(height: 14, borderRadius: AppRadius.sm),
                ),
                const SizedBox(height: AppSpacing.sm),
                AppSkeleton(
                  width: 180,
                  height: 14,
                  borderRadius: AppRadius.sm,
                ),
                const SizedBox(height: AppSpacing.md),
                AppSkeleton(
                  width: 120,
                  height: 12,
                  borderRadius: AppRadius.sm,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
