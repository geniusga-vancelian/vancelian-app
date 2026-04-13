import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'app_section_title.dart';
import 'investment_card.dart';

/// Élément pour [ExclusiveOffersCarousel].
class ExclusiveOfferCarouselItem {
  /// Clé de cache stable (ex. id projet) pour éviter rechargement image au changement d'onglet.
  final String? cacheKey;
  final String imageUrl;
  final String category;
  final String title;
  final String? description;
  final double progress;
  final String raisedAmount;
  final int investorsCount;
  final double? annualizedReturnPercent;
  final int? targetDurationMonths;
  final String? targetAmountLabel;
  final bool isLiked;
  final VoidCallback? onTap;
  final VoidCallback? onInvestTap;
  final VoidCallback? onLikeTap;

  const ExclusiveOfferCarouselItem({
    this.cacheKey,
    required this.imageUrl,
    required this.category,
    required this.title,
    this.description,
    required this.progress,
    required this.raisedAmount,
    required this.investorsCount,
    this.annualizedReturnPercent,
    this.targetDurationMonths,
    this.targetAmountLabel,
    required this.isLiked,
    this.onTap,
    this.onInvestTap,
    this.onLikeTap,
  });
}

/// Nombre de cartes visibles (1,05 = 1 pleine + léger peek 2e).
const double _visibleCardsCount = 1.05;

/// Marge horizontale (même que BlogALaUne / Marketing Cards).
const double _horizontalMargin = AppSpacing.xl;

/// Padding vertical pour ne pas couper les ombres des cartes (top/bottom).
const double _shadowPaddingVertical = AppSpacing.sm;

/// Espace titre → carousel (réduit de _shadowPaddingVertical pour garder le même ordre de grandeur).
const double _titleToCarouselGap = AppSpacing.md - _shadowPaddingVertical;

/// Module Exclusive Offers slidable utilisant [InvestmentCard].
class ExclusiveOffersCarousel extends StatefulWidget {
  final String title;
  final List<ExclusiveOfferCarouselItem> items;
  final VoidCallback? onTitleTap;
  final bool withDescription;

  const ExclusiveOffersCarousel({
    required this.title,
    required this.items,
    this.onTitleTap,
    this.withDescription = true,
    super.key,
  });

  @override
  State<ExclusiveOffersCarousel> createState() => _ExclusiveOffersCarouselState();
}

class _ExclusiveOffersCarouselState extends State<ExclusiveOffersCarousel> {
  double? _measuredHeight;
  bool _measureScheduled = false;
  final GlobalKey _measureKey = GlobalKey();

  void _measureCardHeight() {
    final box = _measureKey.currentContext?.findRenderObject() as RenderBox?;
    if (box == null || !box.hasSize || !mounted) return;
    setState(() => _measuredHeight = box.size.height);
  }

  @override
  Widget build(BuildContext context) {
    if (widget.items.isEmpty) return const SizedBox.shrink();

    final screenWidth = MediaQuery.sizeOf(context).width;
    const gap = AppSpacing.md;
    final availableWidth = screenWidth - _horizontalMargin * 2;
    final cardWidth = (availableWidth - gap) / _visibleCardsCount;

    if (_measuredHeight == null && !_measureScheduled) {
      _measureScheduled = true;
      WidgetsBinding.instance.addPostFrameCallback((_) => _measureCardHeight());
    }

    final firstItem = widget.items.first;
    final height = _measuredHeight;

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
                          Text(widget.title, style: AppTypography.sectionTitle),
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
        SizedBox(height: _titleToCarouselGap),
        if (height != null && height > 0)
          SizedBox(
            height: height + _shadowPaddingVertical,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: EdgeInsets.only(
                left: _horizontalMargin,
                right: _horizontalMargin,
                top: _shadowPaddingVertical,
              ),
              itemCount: widget.items.length,
              separatorBuilder: (_, __) => const SizedBox(width: gap),
              itemBuilder: (context, index) {
                final item = widget.items[index];
                return SizedBox(
                  key: ValueKey<String>(
                      item.cacheKey ?? (item.imageUrl.isNotEmpty ? item.imageUrl : 'offer-$index')),
                  width: cardWidth,
                  child: _buildCard(item),
                );
              },
            ),
          )
        else
          Offstage(
            child: SizedBox(
              key: _measureKey,
              width: cardWidth,
              child: _buildCard(firstItem),
            ),
          ),
      ],
    );
  }

  Widget _buildCard(ExclusiveOfferCarouselItem item) {
    final description = widget.withDescription
        ? ((item.description ?? '').trim().isNotEmpty
            ? item.description!.trim()
            : 'Cum saepe multa, tum memini domi in hemicyclio sedentem')
        : '';

    final status = item.progress >= 1.0 ? 'Financé' : 'En cours';

    final progressValue = item.targetAmountLabel ??
        _computeTargetAmountLabel(item.raisedAmount, item.progress);

    return InvestmentCard(
      imageUrl: item.imageUrl,
      category: item.category,
      status: status,
      title: item.title,
      description: description,
      amount: '${item.raisedAmount} €',
      investorsCount: item.investorsCount,
      progressLabel: 'Financement total',
      progressValue: progressValue,
      progress: item.progress,
      onTap: item.onTap,
      onInvest: item.onInvestTap,
      onFavorite: item.onLikeTap,
    );
  }

  static String _computeTargetAmountLabel(String raisedAmount, double progress) {
    final clean = raisedAmount
        .replaceAll(RegExp(r'[^0-9,\.]'), '')
        .replaceAll(',', '.');
    final value = double.tryParse(clean);
    if (value == null || value <= 0) return '$raisedAmount €';
    final safeProgress = progress.clamp(0.01, 1.0);
    final target = value / safeProgress;
    if (target >= 1000000) {
      final m = target / 1000000;
      final display = m >= 10 ? m.toStringAsFixed(0) : m.toStringAsFixed(1);
      return '${display.replaceAll('.', ',')}M €';
    }
    if (target >= 1000) {
      final k = target / 1000;
      final display = k >= 10 ? k.toStringAsFixed(0) : k.toStringAsFixed(1);
      return '${display.replaceAll('.', ',')}K €';
    }
    return '${target.round()} €';
  }
}
