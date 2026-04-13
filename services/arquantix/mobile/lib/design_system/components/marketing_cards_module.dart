import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'app_section_title.dart';
import 'marketing_card.dart';

/// Configuration d'une carte pour [MarketingCardsModule].
/// [imageUrl] et [redirectUrl] sont requis ; titre, description, logo et bouton sont optionnels.
class MarketingCardItemConfig {
  const MarketingCardItemConfig({
    required this.imageUrl,
    required this.redirectUrl,
    this.title,
    this.description,
    this.logoLabel,
    this.buttonLabel,
  });

  final String imageUrl;
  final String redirectUrl;
  final String? title;
  final String? description;
  final String? logoLabel;
  final String? buttonLabel;
}

/// Layout des cartes : portrait (plus hautes que larges) ou paysage (plus larges que hautes).
enum MarketingCardsLayout {
  portrait,
  landscape,
}

/// Mode d'affichage : sliding (une carte à la fois, sans bullets) ou carousel (défilement avec bullets).
enum MarketingCardsMode {
  sliding,
  carousel,
}

const double _horizontalMargin = AppSpacing.pageEdge;
const double _gapBetweenCards = AppSpacing.md;
const double _portraitRatio = 1.2;
const double _landscapeRatio = 0.75;
const double _cardBorderRadiusLandscape = 24;
const double _dotSize = 8;
const double _dotSpacing = 6;
const double _visibleCardsCountPortrait = 1.2;

/// Module unifié « Marketing cards » : portrait ou paysage, sliding ou carousel, avec ou sans bullets.
/// Réutilise [MarketingCard]. Lien de redirection requis par carte via [onRedirect].
class MarketingCardsModule extends StatefulWidget {
  const MarketingCardsModule({
    super.key,
    required this.items,
    required this.onRedirect,
    this.layout = MarketingCardsLayout.landscape,
    this.mode = MarketingCardsMode.sliding,
    this.title,
    this.description,
    this.visibleCardsCount,
    this.cardAspectRatio,
  });

  /// Titre optionnel au-dessus des cartes.
  final String? title;
  /// Description optionnelle (paragraphe) sous le titre et au-dessus des cartes.
  final String? description;

  /// Liste des cartes (imageUrl + redirectUrl requis ; titre, description, logo, bouton optionnels).
  final List<MarketingCardItemConfig> items;

  /// Callback appelé au tap sur une carte (ex. ouverture de [redirectUrl] avec url_launcher).
  final void Function(String redirectUrl) onRedirect;

  /// Portrait (ratio 1.2) ou paysage (ratio 0.75).
  final MarketingCardsLayout layout;

  /// Sliding = une carte à la fois, sans bullets ; Carousel = défilement avec bullets.
  final MarketingCardsMode mode;

  /// Nombre de cartes visibles sur la largeur écran (ex: 1.2, 1.5, 1.8).
  final double? visibleCardsCount;

  /// Ratio au format "x:y" (ex: "1:1", "3:4"). Interprété comme x/y.
  final String? cardAspectRatio;

  @override
  State<MarketingCardsModule> createState() => _MarketingCardsModuleState();
}

class _MarketingCardsModuleState extends State<MarketingCardsModule> {
  late ScrollController _scrollController;
  int _currentPage = 0;

  @override
  void initState() {
    super.initState();
    _scrollController = ScrollController();
    _scrollController.addListener(_onCarouselScroll);
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onCarouselScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onCarouselScroll() {
    if (!_isSliding && widget.items.isNotEmpty) {
      final screenWidth = MediaQuery.sizeOf(context).width;
      final cardWidth = _computeCardWidth(screenWidth);
      final index = (_scrollController.offset / (cardWidth + _gapBetweenCards)).round().clamp(0, widget.items.length - 1);
      if (index != _currentPage && mounted) setState(() => _currentPage = index);
    }
  }

  bool get _isLandscape => widget.layout == MarketingCardsLayout.landscape;
  bool get _isSliding => widget.mode == MarketingCardsMode.sliding;
  double get _effectiveVisibleCardsCount {
    final raw = widget.visibleCardsCount;
    if (raw == null || raw <= 0) return _visibleCardsCountPortrait;
    return raw;
  }

  double get _cardRatio {
    final parsed = _parseCardAspectRatio(widget.cardAspectRatio);
    if (parsed != null && parsed > 0) return parsed;
    return _isLandscape ? _landscapeRatio : _portraitRatio;
  }

  static double? _parseCardAspectRatio(String? raw) {
    final normalized = (raw ?? '').trim();
    if (normalized.isEmpty) return null;
    final parts = normalized.split(':');
    if (parts.length != 2) return null;
    final first = double.tryParse(parts[0].trim().replaceAll(',', '.'));
    final second = double.tryParse(parts[1].trim().replaceAll(',', '.'));
    if (first == null || second == null || second == 0) return null;
    return first / second;
  }

  double _computeCardWidth(double screenWidth) {
    final count = _effectiveVisibleCardsCount;
    final availableWidth = screenWidth - _horizontalMargin * 2;
    final totalGap = _gapBetweenCards * (count - 1);
    final width = (availableWidth - totalGap) / count;
    if (!width.isFinite || width <= 0) return availableWidth;
    return width;
  }

  @override
  Widget build(BuildContext context) {
    if (widget.items.isEmpty) return const SizedBox.shrink();

    final screenWidth = MediaQuery.sizeOf(context).width;
    final hasTitle = widget.title != null && widget.title!.trim().isNotEmpty;
    final hasDescription =
        widget.description != null && widget.description!.trim().isNotEmpty;

    if (_isSliding) {
      final cardWidth = _computeCardWidth(screenWidth);
      final cardHeight = cardWidth * _cardRatio;

      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (hasTitle) ...[
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
              child: AppSectionTitle(widget.title!.trim()),
            ),
            if (hasDescription) ...[
              const SizedBox(height: AppSpacing.xs),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
                child: Text(
                  widget.description!.trim(),
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppColors.textSecondary,
                    height: 1.4,
                  ),
                ),
              ),
            ],
            const SizedBox(height: AppSpacing.md),
          ] else if (hasDescription) ...[
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
              child: Text(
                widget.description!.trim(),
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.textSecondary,
                  height: 1.4,
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.md),
          ],
          SizedBox(
            height: cardHeight,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
              itemCount: widget.items.length,
              separatorBuilder: (_, __) => const SizedBox(width: _gapBetweenCards),
              itemBuilder: (context, index) {
                final item = widget.items[index];
                return SizedBox(
                  width: cardWidth,
                  height: cardHeight,
                  child: _buildCard(
                    item,
                    cardHeight,
                    borderRadius: _isLandscape ? _cardBorderRadiusLandscape : null,
                    onTap: () => widget.onRedirect(item.redirectUrl),
                  ),
                );
              },
            ),
          ),
          if (widget.mode == MarketingCardsMode.carousel) ...[
            const SizedBox(height: AppSpacing.md),
            _buildDots(),
          ],
        ],
      );
    }

    // Carousel: ListView horizontal
    final cardWidth = _computeCardWidth(screenWidth);
    final cardHeight = cardWidth * _cardRatio;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (hasTitle) ...[
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
            child: AppSectionTitle(widget.title!.trim()),
          ),
          if (hasDescription) ...[
            const SizedBox(height: AppSpacing.xs),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
              child: Text(
                widget.description!.trim(),
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.textSecondary,
                  height: 1.4,
                ),
              ),
            ),
          ],
          const SizedBox(height: AppSpacing.md),
        ] else if (hasDescription) ...[
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
            child: Text(
              widget.description!.trim(),
              style: AppTypography.bodyMedium.copyWith(
                color: AppColors.textSecondary,
                height: 1.4,
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.md),
        ],
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
                child: _buildCard(
                  item,
                  cardHeight,
                  borderRadius: _isLandscape ? _cardBorderRadiusLandscape : null,
                  onTap: () => widget.onRedirect(item.redirectUrl),
                ),
              );
            },
          ),
        ),
        if (widget.mode == MarketingCardsMode.carousel) ...[
          const SizedBox(height: AppSpacing.md),
          _buildDots(),
        ],
      ],
    );
  }

  Widget _buildCard(
    MarketingCardItemConfig item,
    double height, {
    double? borderRadius,
    required VoidCallback onTap,
  }) {
    return MarketingCard(
      imageUrl: item.imageUrl,
      title: item.title ?? '',
      description: item.description,
      logoLabel: item.logoLabel,
      buttonLabel: item.buttonLabel,
      onTap: onTap,
      onButtonTap: item.buttonLabel != null ? onTap : null,
      size: MarketingCardSize.medium,
      customHeight: height,
      borderRadius: borderRadius,
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
