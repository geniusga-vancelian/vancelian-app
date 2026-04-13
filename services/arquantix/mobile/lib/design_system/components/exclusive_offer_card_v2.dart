import 'package:flutter/material.dart';

import 'featured_offer_card.dart';

/// Carte "Exclusive offer" : variante de [FeaturedOfferCard] avec bloc progression et bouton Investir.
class ExclusiveOfferCard extends StatelessWidget {
  final String? imageCacheKey;
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
  final VoidCallback onTap;
  final VoidCallback? onInvestTap;
  final VoidCallback? onLikeTap;

  const ExclusiveOfferCard({
    this.imageCacheKey,
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
    required this.onTap,
    this.onInvestTap,
    this.onLikeTap,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final effectiveDescription = (description ?? '').trim().isNotEmpty
        ? description!.trim()
        : 'Cum saepe multa, tum memini domi in hemicyclio sedentem';

    return FeaturedOfferCard(
      imageCacheKey: imageCacheKey,
      imageUrl: imageUrl,
      category: category,
      title: title,
      description: effectiveDescription,
      actionLabel: 'Investir',
      onTap: onTap,
      onActionTap: onInvestTap,
      showProgressBlock: true,
      progress: progress,
      raisedAmount: raisedAmount,
      investorsCount: investorsCount,
      targetAmountLabel: targetAmountLabel,
    );
  }
}
