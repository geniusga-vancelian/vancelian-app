import 'package:flutter/material.dart';

import '../atoms/app_spacing.dart';
import '../layout/module_horizontal_margin.dart';
import 'app_section_title.dart';
import 'ds_story_segment_bar.dart';
import 'marketing_card.dart';

/// Élément pour [MarketingCardsCarousel] et [MarketingCardsSlidingModule].
class MarketingCardsCarouselItem {
  final String imageUrl;
  final String title;
  final String? description;
  final String? label;
  final String? logoLabel;
  final String? buttonLabel;
  final VoidCallback? onTap;
  final VoidCallback? onButtonTap;

  const MarketingCardsCarouselItem({
    required this.imageUrl,
    required this.title,
    this.description,
    this.label,
    this.logoLabel,
    this.buttonLabel,
    this.onTap,
    this.onButtonTap,
  });
}

/// Marge horizontale : [kModuleHorizontalMargin] (dashboard / modules).
const double _horizontalMargin = kModuleHorizontalMargin;

/// Ratio hauteur / largeur pour une carte (hauteur = largeur * ratio).
const double _cardHeightRatio = 1.2;

/// Widget "Marketing Cards" : titre avec marge, carrousel une carte par swipe.
/// Marges : [kModuleHorizontalMargin] sur le bord extérieur de la 1re / dernière carte uniquement ;
/// entre les cartes, demi-[AppSpacing.md] de chaque côté.
class MarketingCardsCarousel extends StatefulWidget {
  /// Titre du module (avec padding gauche/droite).
  final String title;

  /// Liste des cartes (ex. 4).
  final List<MarketingCardsCarouselItem> items;

  const MarketingCardsCarousel({
    required this.title,
    required this.items,
    super.key,
  });

  @override
  State<MarketingCardsCarousel> createState() => _MarketingCardsCarouselState();
}

class _MarketingCardsCarouselState extends State<MarketingCardsCarousel> {
  late final PageController _pageController = PageController(viewportFraction: 1);
  int _pageIndex = 0;

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.items.isEmpty) {
      return const SizedBox.shrink();
    }

    final multi = widget.items.length > 1;
    final screenWidth = MediaQuery.sizeOf(context).width;
    const gap = AppSpacing.md;
    final last = widget.items.length - 1;
    /// Hauteur du bandeau = carte la plus large (page centrale : W − gap).
    final maxCardWidth = screenWidth - gap;
    final cardHeight = maxCardWidth * _cardHeightRatio;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
          child: AppSectionTitle(widget.title),
        ),
        if (multi) ...[
          const SizedBox(height: AppSpacing.sm),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
            child: DsStorySegmentBar(
              segmentCount: widget.items.length,
              activeIndex: _pageIndex,
              variant: DsStorySegmentBarVariant.onSurface,
            ),
          ),
        ],
        const SizedBox(height: AppSpacing.md),
        SizedBox(
          height: cardHeight,
          child: PageView.builder(
            controller: _pageController,
            onPageChanged: (i) {
              if (multi) setState(() => _pageIndex = i);
            },
            padEnds: false,
            itemCount: widget.items.length,
            itemBuilder: (context, index) {
              final item = widget.items[index];
              final left = index == 0 ? _horizontalMargin : gap / 2;
              final right = index == last ? _horizontalMargin : gap / 2;
              return Padding(
                padding: EdgeInsets.only(left: left, right: right),
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final w = constraints.maxWidth;
                    final h = w * _cardHeightRatio;
                    return SizedBox(
                      width: w,
                      height: h,
                      child: MarketingCard(
                        imageUrl: item.imageUrl,
                        title: item.title,
                        description: item.description,
                        label: item.label,
                        logoLabel: item.logoLabel,
                        buttonLabel: item.buttonLabel,
                        onTap: item.onTap,
                        onButtonTap: item.onButtonTap,
                        size: MarketingCardSize.medium,
                        customHeight: h,
                      ),
                    );
                  },
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}
