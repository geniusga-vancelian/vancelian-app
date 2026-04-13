import 'package:flutter/material.dart';

import '../atoms/app_spacing.dart';
import '../layout/module_horizontal_margin.dart';
import 'app_section_title.dart';
import 'carousel_pagination_dots.dart';
import 'marketing_card.dart';
import 'marketing_cards_carousel.dart';

/// Marge horizontale : [kModuleHorizontalMargin] (identique au dashboard).
const double _horizontalMargin = kModuleHorizontalMargin;

/// Ratio hauteur / largeur pour une carte (format 4:3 paysage).
const double _cardHeightRatio = 0.75;

/// Espace entre deux cartes (aligné sur [MarketingCardsCarousel] = AppSpacing.md).
const double _gapBetweenCards = AppSpacing.md;

/// Rayon des coins des cartes (plus arrondi que le carousel classique).
const double _cardBorderRadius = 24;

/// Module « Marketing cards » avec sliding (PageView) et indicateurs en points sous les cartes.
/// Réutilise [MarketingCardsCarouselItem] et [MarketingCard] du DS.
class MarketingCardsSlidingModule extends StatefulWidget {
  const MarketingCardsSlidingModule({
    super.key,
    required this.items,
    this.title,
  });

  /// Titre optionnel au-dessus du carousel (même style que [MarketingCardsCarousel]).
  final String? title;

  /// Liste des cartes (ex. 3 pour un essai).
  final List<MarketingCardsCarouselItem> items;

  @override
  State<MarketingCardsSlidingModule> createState() => _MarketingCardsSlidingModuleState();
}

class _MarketingCardsSlidingModuleState extends State<MarketingCardsSlidingModule> {
  late PageController _pageController;
  int _currentPage = 0;

  @override
  void initState() {
    super.initState();
    _pageController = PageController(viewportFraction: 1);
  }

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

    final screenWidth = MediaQuery.sizeOf(context).width;
    final last = widget.items.length - 1;
    /// Carte la plus large = page « milieu » (W − gap) — évite de couper les cartes.
    final maxCardWidth = screenWidth - _gapBetweenCards;
    final cardHeight = maxCardWidth * _cardHeightRatio;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (widget.title != null && widget.title!.isNotEmpty) ...[
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
            child: AppSectionTitle(widget.title!),
          ),
          const SizedBox(height: AppSpacing.md),
        ],
        SizedBox(
          height: cardHeight,
          child: PageView.builder(
            controller: _pageController,
            onPageChanged: (index) => setState(() => _currentPage = index),
            itemCount: widget.items.length,
            padEnds: false,
            itemBuilder: (context, index) {
              final item = widget.items[index];
              final left =
                  index == 0 ? _horizontalMargin : _gapBetweenCards / 2;
              final right =
                  index == last ? _horizontalMargin : _gapBetweenCards / 2;
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
                        borderRadius: _cardBorderRadius,
                      ),
                    );
                  },
                ),
              );
            },
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        CarouselPaginationDots(
          count: widget.items.length,
          activeIndex: _currentPage,
        ),
      ],
    );
  }
}
