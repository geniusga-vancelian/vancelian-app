import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'app_section_title.dart';
import 'marketing_card.dart';

/// Élément pour [VaultsCarousel].
class VaultCarouselItem {
  const VaultCarouselItem({
    required this.slug,
    required this.title,
    this.description,
    required this.coverImage,
    this.onTap,
  });

  final String slug;
  final String title;
  final String? description;
  final String coverImage;
  final VoidCallback? onTap;
}

const double _horizontalMargin = AppSpacing.pageEdge;
const double _gapBetweenCards = AppSpacing.md;
const double _landscapeRatio = 0.75;
const double _cardBorderRadiusLandscape = 24;
const double _dotSize = 8;
const double _dotSpacing = 6;
const double _visibleCardsCount = 1.2;

/// Module Vaults : carousel horizontal avec sliding et bullets.
class VaultsCarousel extends StatefulWidget {
  const VaultsCarousel({
    super.key,
    required this.title,
    required this.items,
    this.onTitleTap,
  });

  final String title;
  final List<VaultCarouselItem> items;
  final VoidCallback? onTitleTap;

  @override
  State<VaultsCarousel> createState() => _VaultsCarouselState();
}

class _VaultsCarouselState extends State<VaultsCarousel> {
  final ScrollController _scrollController = ScrollController();
  int _currentPage = 0;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (widget.items.isEmpty || !mounted) return;
    final screenWidth = MediaQuery.sizeOf(context).width;
    final availableWidth = screenWidth - _horizontalMargin * 2;
    final cardWidth = (availableWidth - _gapBetweenCards) / _visibleCardsCount;
    final index = (_scrollController.offset / (cardWidth + _gapBetweenCards))
        .round()
        .clamp(0, widget.items.length - 1);
    if (index != _currentPage) setState(() => _currentPage = index);
  }

  @override
  Widget build(BuildContext context) {
    if (widget.items.isEmpty) return const SizedBox.shrink();

    final screenWidth = MediaQuery.sizeOf(context).width;
    final availableWidth = screenWidth - _horizontalMargin * 2;
    final cardWidth = (availableWidth - _gapBetweenCards) / _visibleCardsCount;
    final cardHeight = cardWidth * _landscapeRatio;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
          child: widget.onTitleTap != null
              ? Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: widget.onTitleTap,
                    borderRadius: BorderRadius.circular(4),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            widget.title,
                            style: AppTypography.sectionTitle.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(width: AppSpacing.xs),
                          Icon(
                            Icons.chevron_right,
                            size: 22,
                            color: AppColors.textPrimary,
                          ),
                        ],
                      ),
                    ),
                  ),
                )
              : AppSectionTitle(widget.title),
        ),
        const SizedBox(height: AppSpacing.md),
        SizedBox(
          height: cardHeight,
          child: ListView.separated(
            controller: _scrollController,
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
            itemCount: widget.items.length,
            separatorBuilder: (_, __) => const SizedBox(width: _gapBetweenCards),
            itemBuilder: (context, index) {
              final item = widget.items[index];
              return SizedBox(
                width: cardWidth,
                child: MarketingCard(
                  imageUrl: item.coverImage,
                  title: item.title,
                  description: item.description,
                  onTap: item.onTap ?? () {},
                  size: MarketingCardSize.medium,
                  customHeight: cardHeight,
                  borderRadius: _cardBorderRadiusLandscape,
                ),
              );
            },
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        _buildDots(),
      ],
    );
  }

  Widget _buildDots() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(
        widget.items.length,
        (index) => _PaginationDot(isActive: index == _currentPage),
      ),
    );
  }
}

class _PaginationDot extends StatelessWidget {
  const _PaginationDot({required this.isActive});
  final bool isActive;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      margin: const EdgeInsets.symmetric(horizontal: _dotSpacing / 2),
      width: _dotSize,
      height: _dotSize,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: isActive
            ? AppColors.textPrimary
            : AppColors.textPrimary.withValues(alpha: 0.25),
      ),
    );
  }
}
