import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import 'marketing_module.dart';

/// Un item pour [MarketingFeatures] (même contenu qu’un [MarketingModule]).
class MarketingFeaturesItem {
  const MarketingFeaturesItem({
    required this.title,
    required this.subtitle,
    this.onTap,
    this.icon = Icons.savings_rounded,
    this.iconBackgroundColor = Colors.orange,
  });

  final String title;
  final String subtitle;
  final VoidCallback? onTap;
  final IconData icon;
  final Color iconBackgroundColor;
}

/// Hauteur du bandeau carousel (une carte marketing, 2 lignes titre + 3 lignes sous-titre).
const double _carouselItemHeight = 110;

/// Espace entre les bullets et les modules.
const double _dotsTopMargin = 10;

/// Taille d’un bullet (point actif ou inactif).
const double _dotSize = 8;
const double _dotSizeActive = 9;

/// Espace entre les bullets.
const double _dotSpacing = 6;

/// Padding horizontal appliqué au premier/dernier item du carousel.
const double _cardEdgePaddingHorizontal = 16;

/// Liste de modules marketing : 1 item = affichage unique, 2+ = carousel horizontal + bullets en dessous.
class MarketingFeatures extends StatefulWidget {
  const MarketingFeatures({
    super.key,
    required this.items,
    this.margin,
    this.showDots = true,
  });

  final List<MarketingFeaturesItem> items;
  final EdgeInsetsGeometry? margin;
  final bool showDots;

  @override
  State<MarketingFeatures> createState() => _MarketingFeaturesState();
}

class _MarketingFeaturesState extends State<MarketingFeatures> {
  late PageController _pageController;
  int _currentPage = 0;

  @override
  void initState() {
    super.initState();
    _pageController = PageController();
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _onPageChanged(int index) {
    if (_currentPage != index) setState(() => _currentPage = index);
  }

  @override
  Widget build(BuildContext context) {
    if (widget.items.isEmpty) return const SizedBox.shrink();

    if (widget.items.length == 1) {
      return MarketingModule(
        title: widget.items.first.title,
        subtitle: widget.items.first.subtitle,
        onTap: widget.items.first.onTap,
        icon: widget.items.first.icon,
        iconBackgroundColor: widget.items.first.iconBackgroundColor,
        margin: const EdgeInsets.symmetric(horizontal: _cardEdgePaddingHorizontal),
      );
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        LayoutBuilder(
          builder: (context, constraints) {
            final viewportWidth = constraints.maxWidth;
            final cardWidth = viewportWidth - 2 * _cardEdgePaddingHorizontal;
            return SizedBox(
              height: _carouselItemHeight,
              child: PageView.builder(
                controller: _pageController,
                onPageChanged: _onPageChanged,
                itemCount: widget.items.length,
                itemBuilder: (context, index) {
                  final item = widget.items[index];
                  final isFirst = index == 0;
                  final isLast = index == widget.items.length - 1;
                  return Padding(
                    padding: EdgeInsets.only(
                      left: isFirst ? _cardEdgePaddingHorizontal : 0,
                      right: isLast ? _cardEdgePaddingHorizontal : 0,
                    ),
                    child: SizedBox(
                      width: cardWidth,
                      child: MarketingModule(
                        title: item.title,
                        subtitle: item.subtitle,
                        onTap: item.onTap,
                        icon: item.icon,
                        iconBackgroundColor: item.iconBackgroundColor,
                        margin: EdgeInsets.zero,
                      ),
                    ),
                  );
                },
              ),
            );
          },
        ),
        if (widget.showDots) ...[
          const SizedBox(height: _dotsTopMargin),
          _buildDots(context),
        ],
      ],
    );
  }

  Widget _buildDots(BuildContext context) {
    final inactiveColor = AppColors.textSecondary.withValues(alpha: 0.6);
    const activeColor = AppColors.textPrimary;

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      mainAxisSize: MainAxisSize.min,
      children: List.generate(
        widget.items.length,
        (index) {
          final isActive = index == _currentPage;
          return GestureDetector(
            onTap: () {
              _pageController.animateToPage(
                index,
                duration: const Duration(milliseconds: 300),
                curve: Curves.easeOutCubic,
              );
            },
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              margin: EdgeInsets.only(right: index < widget.items.length - 1 ? _dotSpacing : 0),
              width: isActive ? _dotSizeActive : _dotSize,
              height: isActive ? _dotSizeActive : _dotSize,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: isActive ? activeColor : inactiveColor,
              ),
            ),
          );
        },
      ),
    );
  }
}
