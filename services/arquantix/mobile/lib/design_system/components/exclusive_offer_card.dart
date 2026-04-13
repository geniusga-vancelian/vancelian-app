import 'dart:ui';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

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
  final bool isLiked;
  final VoidCallback onTap;
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
    required this.isLiked,
    required this.onTap,
    this.onLikeTap,
    super.key,
  });

  static const double _imageAspectRatio = 16 / 11;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.card),
        child: Container(
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(AppRadius.card),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.08),
                blurRadius: 16,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(AppRadius.card),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildImageSection(),
                _buildBottomSection(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildImageSection() {
    return Stack(
      children: [
        AspectRatio(
          aspectRatio: _imageAspectRatio,
          child: imageUrl.isNotEmpty
              ? CachedNetworkImage(
                  imageUrl: imageUrl,
                  cacheKey: imageCacheKey,
                  fit: BoxFit.cover,
                  fadeInDuration: Duration.zero,
                  fadeOutDuration: Duration.zero,
                  placeholder: (_, __) => _placeholder(),
                  errorWidget: (_, __, ___) => _placeholder(),
                )
              : _placeholder(),
        ),
        const Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Colors.transparent, Color(0x22000000), Color(0x88000000)],
                stops: [0.45, 0.7, 1],
              ),
            ),
          ),
        ),
        _buildCategoryTag(),
        _buildLikeButton(),
        Positioned(
          left: AppSpacing.lg,
          right: AppSpacing.lg,
          bottom: AppSpacing.md,
          child: _buildImageMetrics(),
        ),
      ],
    );
  }

  Widget _buildImageMetrics() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                '$raisedAmount €',
                style: AppTypography.sectionTitle.copyWith(
                  color: Colors.white,
                  fontSize: 23,
                  fontWeight: FontWeight.w700,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.groups_rounded, size: 24, color: Colors.white),
                const SizedBox(width: AppSpacing.xs),
                Text(
                  '$investorsCount Investors',
                  style: AppTypography.bodyMedium.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: LinearProgressIndicator(
            value: progress.clamp(0.0, 1.0),
            minHeight: 12,
            backgroundColor: Colors.white.withValues(alpha: 0.35),
            valueColor: const AlwaysStoppedAnimation<Color>(Colors.white),
          ),
        ),
        const SizedBox(height: AppSpacing.xs),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Financement total',
              style: AppTypography.bodyMedium.copyWith(
                color: Colors.white.withValues(alpha: 0.95),
              ),
            ),
            Text(
              _computeTargetAmountLabel(),
              style: AppTypography.sectionTitle.copyWith(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildBottomSection() {
    final subtitle = annualizedReturnPercent != null
        ? '+${annualizedReturnPercent!.toStringAsFixed(2)}%'
        : (description?.trim().isNotEmpty == true ? description!.trim() : null);
    return Container(
      color: AppColors.cardBackground,
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        AppSpacing.lg,
        AppSpacing.lg,
        AppSpacing.xl,
      ),
      child: Row(
        children: [
          Container(
            width: 58,
            height: 58,
            decoration: BoxDecoration(
              color: AppColors.placeholderBg,
              borderRadius: BorderRadius.circular(18),
            ),
            child: Icon(
              Icons.business_center_rounded,
              color: AppColors.textSecondary.withValues(alpha: 0.6),
              size: 30,
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: AppTypography.titleMedium.copyWith(
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                    fontSize: 19,
                    height: 1.2,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    subtitle,
                    style: AppTypography.titleMedium.copyWith(
                      color: const Color(0xFF22C55E),
                      fontWeight: FontWeight.w600,
                      fontSize: 16,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          FilledButton(
            onPressed: onTap,
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.accent,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(999),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            ),
            child: Text(
              'Investir',
              style: AppTypography.bodyMedium.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCategoryTag() {
    return Positioned(
      top: AppSpacing.sm,
      left: AppSpacing.sm,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(AppRadius.chip),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.sm,
              vertical: AppSpacing.xs,
            ),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.35),
              borderRadius: BorderRadius.circular(AppRadius.chip),
              border: Border.all(color: Colors.black.withValues(alpha: 0.5), width: 0.5),
            ),
            child: Text(
              category,
              style: AppTypography.meta.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w600,
                fontSize: 11,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildLikeButton() {
    return Positioned(
      top: AppSpacing.sm,
      right: AppSpacing.sm,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onLikeTap,
          borderRadius: BorderRadius.circular(20),
          child: Container(
            padding: const EdgeInsets.all(AppSpacing.xs),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.35),
              shape: BoxShape.circle,
            ),
            child: Icon(
              isLiked ? Icons.favorite : Icons.favorite_border,
              size: 22,
              color: isLiked ? Colors.red.shade400 : Colors.white,
            ),
          ),
        ),
      ),
    );
  }

  String _computeTargetAmountLabel() {
    final clean = raisedAmount.replaceAll(RegExp(r'[^0-9,\.]'), '').replaceAll(',', '.');
    final value = double.tryParse(clean);
    if (value == null || value <= 0) return '${raisedAmount} €';
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

  Widget _placeholder() => Container(
        color: AppColors.placeholderBg,
        child: Icon(
          Icons.image_not_supported,
          color: AppColors.placeholderIcon,
          size: 48,
        ),
      );
}
*/
/*
import 'dart:ui';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Carte "Exclusive Offer" au style hero:
/// image full width + overlay data + bloc infos en bas.
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
  final bool isLiked;
  final VoidCallback onTap;
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
    required this.isLiked,
    required this.onTap,
    this.onLikeTap,
    super.key,
  });

  static const double _imageAspectRatio = 16 / 11;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.card),
        child: Container(
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(AppRadius.card),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.08),
                blurRadius: 16,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(AppRadius.card),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildImageSection(),
                _buildBottomSection(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildImageSection() {
    return Stack(
      children: [
        AspectRatio(
          aspectRatio: _imageAspectRatio,
          child: imageUrl.isNotEmpty
              ? CachedNetworkImage(
                  imageUrl: imageUrl,
                  cacheKey: imageCacheKey,
                  fit: BoxFit.cover,
                  fadeInDuration: Duration.zero,
                  fadeOutDuration: Duration.zero,
                  placeholder: (_, __) => _placeholder(),
                  errorWidget: (_, __, ___) => _placeholder(),
                )
              : _placeholder(),
        ),
        const Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Colors.transparent,
                  Color(0x22000000),
                  Color(0x88000000),
                ],
                stops: [0.45, 0.7, 1],
              ),
            ),
          ),
        ),
        _buildCategoryTag(),
        _buildLikeButton(),
        Positioned(
          left: AppSpacing.lg,
          right: AppSpacing.lg,
          bottom: AppSpacing.md,
          child: _buildImageMetrics(),
        ),
      ],
    );
  }

  Widget _buildImageMetrics() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                '$raisedAmount €',
                style: AppTypography.sectionTitle.copyWith(
                  color: Colors.white,
                  fontSize: 23,
                  fontWeight: FontWeight.w700,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.groups_rounded, size: 24, color: Colors.white),
                const SizedBox(width: AppSpacing.xs),
                Text(
                  '$investorsCount Investors',
                  style: AppTypography.bodyMedium.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: LinearProgressIndicator(
            value: progress.clamp(0.0, 1.0),
            minHeight: 12,
            backgroundColor: Colors.white.withValues(alpha: 0.35),
            valueColor: const AlwaysStoppedAnimation<Color>(Colors.white),
          ),
        ),
        const SizedBox(height: AppSpacing.xs),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Financement total',
              style: AppTypography.bodyMedium.copyWith(
                color: Colors.white.withValues(alpha: 0.95),
              ),
            ),
            Text(
              _computeTargetAmountLabel(),
              style: AppTypography.sectionTitle.copyWith(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildBottomSection() {
    final subtitle = annualizedReturnPercent != null
        ? '+${annualizedReturnPercent!.toStringAsFixed(2)}%'
        : (description?.trim().isNotEmpty == true ? description!.trim() : null);
    return Container(
      color: AppColors.cardBackground,
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        AppSpacing.lg,
        AppSpacing.lg,
        AppSpacing.xl,
      ),
      child: Row(
        children: [
          Container(
            width: 58,
            height: 58,
            decoration: BoxDecoration(
              color: AppColors.placeholderBg,
              borderRadius: BorderRadius.circular(18),
            ),
            child: Icon(
              Icons.business_center_rounded,
              color: AppColors.textSecondary.withValues(alpha: 0.6),
              size: 30,
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: AppTypography.titleMedium.copyWith(
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                    fontSize: 19,
                    height: 1.2,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    subtitle,
                    style: AppTypography.titleMedium.copyWith(
                      color: const Color(0xFF22C55E),
                      fontWeight: FontWeight.w600,
                      fontSize: 16,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          FilledButton(
            onPressed: onTap,
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.accent,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(999),
              ),
              padding: const EdgeInsets.symmetric(
                horizontal: 24,
                vertical: 12,
              ),
            ),
            child: Text(
              'Investir',
              style: AppTypography.bodyMedium.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCategoryTag() {
    return Positioned(
      top: AppSpacing.sm,
      left: AppSpacing.sm,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(AppRadius.chip),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.sm,
              vertical: AppSpacing.xs,
            ),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.35),
              borderRadius: BorderRadius.circular(AppRadius.chip),
              border: Border.all(
                color: Colors.black.withValues(alpha: 0.5),
                width: 0.5,
              ),
            ),
            child: Text(
              category,
              style: AppTypography.meta.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w600,
                fontSize: 11,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildLikeButton() {
    return Positioned(
      top: AppSpacing.sm,
      right: AppSpacing.sm,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onLikeTap,
          borderRadius: BorderRadius.circular(20),
          child: Container(
            padding: const EdgeInsets.all(AppSpacing.xs),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.35),
              shape: BoxShape.circle,
            ),
            child: Icon(
              isLiked ? Icons.favorite : Icons.favorite_border,
              size: 22,
              color: isLiked ? Colors.red.shade400 : Colors.white,
            ),
          ),
        ),
      ),
    );
  }

  String _computeTargetAmountLabel() {
    final clean = raisedAmount.replaceAll(RegExp(r'[^0-9,\.]'), '').replaceAll(',', '.');
    final value = double.tryParse(clean);
    if (value == null || value <= 0) return '${raisedAmount} €';
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

  Widget _placeholder() => Container(
        color: AppColors.placeholderBg,
        child: Icon(
          Icons.image_not_supported,
          color: AppColors.placeholderIcon,
          size: 48,
        ),
      );
}
import 'dart:ui';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Carte "Exclusive Offer" au style hero:
/// image full width + overlay data + bloc infos en bas.
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
  final bool isLiked;
  final VoidCallback onTap;
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
    required this.isLiked,
    required this.onTap,
    this.onLikeTap,
    super.key,
  });

  static const double _imageAspectRatio = 16 / 11;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.card),
        child: Container(
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(AppRadius.card),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.08),
                blurRadius: 16,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(AppRadius.card),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildImageSection(),
                _buildBottomSection(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildImageSection() {
    return Stack(
      children: [
        AspectRatio(
          aspectRatio: _imageAspectRatio,
          child: imageUrl.isNotEmpty
              ? CachedNetworkImage(
                  imageUrl: imageUrl,
                  cacheKey: imageCacheKey,
                  fit: BoxFit.cover,
                  fadeInDuration: Duration.zero,
                  fadeOutDuration: Duration.zero,
                  placeholder: (_, __) => _placeholder(),
                  errorWidget: (_, __, ___) => _placeholder(),
                )
              : _placeholder(),
        ),
        const Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Colors.transparent,
                  Color(0x22000000),
                  Color(0x88000000),
                ],
                stops: [0.45, 0.7, 1],
              ),
            ),
          ),
        ),
        _buildCategoryTag(),
        _buildLikeButton(),
        Positioned(
          left: AppSpacing.lg,
          right: AppSpacing.lg,
          bottom: AppSpacing.md,
          child: _buildImageMetrics(),
        ),
      ],
    );
  }

  Widget _buildImageMetrics() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                '$raisedAmount €',
                style: AppTypography.sectionTitle.copyWith(
                  color: Colors.white,
                  fontSize: 23,
                  fontWeight: FontWeight.w700,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.groups_rounded, size: 24, color: Colors.white),
                const SizedBox(width: AppSpacing.xs),
                Text(
                  '$investorsCount Investors',
                  style: AppTypography.bodyMedium.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: LinearProgressIndicator(
            value: progress.clamp(0.0, 1.0),
            minHeight: 12,
            backgroundColor: Colors.white.withValues(alpha: 0.35),
            valueColor: const AlwaysStoppedAnimation<Color>(Colors.white),
          ),
        ),
        const SizedBox(height: AppSpacing.xs),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Financement total',
              style: AppTypography.bodyMedium.copyWith(
                color: Colors.white.withValues(alpha: 0.95),
              ),
            ),
            Text(
              _computeTargetAmountLabel(),
              style: AppTypography.sectionTitle.copyWith(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildBottomSection() {
    final subtitle = annualizedReturnPercent != null
        ? '+${annualizedReturnPercent!.toStringAsFixed(2)}%'
        : (description?.trim().isNotEmpty == true ? description!.trim() : null);
    return Container(
      color: AppColors.cardBackground,
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        AppSpacing.lg,
        AppSpacing.lg,
        AppSpacing.xl,
      ),
      child: Row(
        children: [
          Container(
            width: 58,
            height: 58,
            decoration: BoxDecoration(
              color: AppColors.placeholderBg,
              borderRadius: BorderRadius.circular(18),
            ),
            child: Icon(
              Icons.business_center_rounded,
              color: AppColors.textSecondary.withValues(alpha: 0.6),
              size: 30,
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: AppTypography.titleMedium.copyWith(
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                    fontSize: 19,
                    height: 1.2,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    subtitle,
                    style: AppTypography.titleMedium.copyWith(
                      color: const Color(0xFF22C55E),
                      fontWeight: FontWeight.w600,
                      fontSize: 16,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          FilledButton(
            onPressed: onTap,
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.accent,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(999),
              ),
              padding: const EdgeInsets.symmetric(
                horizontal: 24,
                vertical: 12,
              ),
            ),
            child: Text(
              'Investir',
              style: AppTypography.bodyMedium.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCategoryTag() {
    return Positioned(
      top: AppSpacing.sm,
      left: AppSpacing.sm,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(AppRadius.chip),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.sm,
              vertical: AppSpacing.xs,
            ),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.35),
              borderRadius: BorderRadius.circular(AppRadius.chip),
              border: Border.all(
                color: Colors.black.withValues(alpha: 0.5),
                width: 0.5,
              ),
            ),
            child: Text(
              category,
              style: AppTypography.meta.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w600,
                fontSize: 11,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildLikeButton() {
    return Positioned(
      top: AppSpacing.sm,
      right: AppSpacing.sm,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onLikeTap,
          borderRadius: BorderRadius.circular(20),
          child: Container(
            padding: const EdgeInsets.all(AppSpacing.xs),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.35),
              shape: BoxShape.circle,
            ),
            child: Icon(
              isLiked ? Icons.favorite : Icons.favorite_border,
              size: 22,
              color: isLiked ? Colors.red.shade400 : Colors.white,
            ),
          ),
        ),
      ),
    );
  }

  String _computeTargetAmountLabel() {
    final clean = raisedAmount.replaceAll(RegExp(r'[^0-9,\.]'), '').replaceAll(',', '.');
    final value = double.tryParse(clean);
    if (value == null || value <= 0) return '${raisedAmount} €';
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

  Widget _placeholder() => Container(
        color: AppColors.placeholderBg,
        child: Icon(
          Icons.image_not_supported,
          color: AppColors.placeholderIcon,
          size: 48,
        ),
      );
}
import 'dart:ui';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Carte "Exclusive Offer" : dérivée portrait (image + contenu), avec barre de progression,
/// performance, nombre de participants et like.
class ExclusiveOfferCard extends StatelessWidget {
  /// Clé de cache stable (ex. id projet) pour éviter rechargement au changement d'onglet.
  final String? imageCacheKey;
  /// URL de l'image.
  final String imageUrl;

  /// Catégorie d'investissement (ex. Real estate, Energy, Commodity, Art).
  final String category;

  /// Titre de l'offre (max 2 lignes).
  final String title;

  /// Description courte optionnelle (max 2 lignes si présente).
  final String? description;

  /// Progression de la collecte (0.0 à 1.0).
  final double progress;

  /// Montant déjà levé (partie numérique, ex. "813 700") ; affiché avec " EUR" en plus gros.
  final String raisedAmount;

  /// Nombre d'investisseurs.
  final int investorsCount;

  /// Rendement annualisé en % (ex. 10.86).
  final double? annualizedReturnPercent;

  /// Durée cible d'investissement en mois (ex. 24).
  final int? targetDurationMonths;

  /// Offre mise en favori (cœur plein ou vide).
  final bool isLiked;

  /// Callback au tap sur la carte.
  final VoidCallback onTap;

  /// Callback au tap sur le cœur (like).
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
    required this.isLiked,
    required this.onTap,
    this.onLikeTap,
    super.key,
  });

  /// 16/9 avec hauteur augmentée de 20 % (ratio plus bas = image plus haute).
  static const double _imageAspectRatio = 16 / (9 * 1.2);

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.card),
        child: Container(
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(AppRadius.card),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.08),
                blurRadius: 16,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              _buildImageSection(),
              Padding(
                padding: const EdgeInsets.all(AppSpacing.lg),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: AppTypography.titleMedium.copyWith(
                        fontWeight: FontWeight.w700,
                        color: AppColors.textPrimary,
                        height: 1.25,
                        letterSpacing: -0.3,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (description != null && description!.isNotEmpty) ...[
                      const SizedBox(height: AppSpacing.sm),
                      Text(
                        description!,
                        style: AppTypography.meta.copyWith(height: 1.35),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                    const SizedBox(height: AppSpacing.md),
                    _buildProgressSection(),
                    if (annualizedReturnPercent != null || targetDurationMonths != null) ...[
                      const SizedBox(height: AppSpacing.md),
                      _buildReturnAndDuration(),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildImageSection() {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(AppRadius.image),
        child: Stack(
          alignment: Alignment.center,
          children: [
            AspectRatio(
              aspectRatio: _imageAspectRatio,
              child: imageUrl.isNotEmpty
                  ? CachedNetworkImage(
                      imageUrl: imageUrl,
                      cacheKey: imageCacheKey,
                      fit: BoxFit.cover,
                      fadeInDuration: Duration.zero,
                      fadeOutDuration: Duration.zero,
                      placeholder: (_, __) => _placeholder(),
                      errorWidget: (_, __, ___) => _placeholder(),
                    )
                  : _placeholder(),
            ),
            _buildCategoryTag(),
            _buildLikeButton(),
          ],
        ),
      ),
    );
  }

  Widget _buildCategoryTag() {
    return Positioned(
      top: AppSpacing.sm,
      left: AppSpacing.sm,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(AppRadius.chip),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.sm,
              vertical: AppSpacing.xs,
            ),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.35),
              borderRadius: BorderRadius.circular(AppRadius.chip),
              border: Border.all(
                color: Colors.black.withValues(alpha: 0.5),
                width: 0.5,
              ),
            ),
            child: Text(
              category,
              style: AppTypography.meta.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w600,
                fontSize: 11,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildLikeButton() {
    return Positioned(
      top: AppSpacing.sm,
      right: AppSpacing.sm,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onLikeTap,
          borderRadius: BorderRadius.circular(20),
          child: Container(
            padding: const EdgeInsets.all(AppSpacing.xs),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.35),
              shape: BoxShape.circle,
            ),
            child: Icon(
              isLiked ? Icons.favorite : Icons.favorite_border,
              size: 22,
              color: isLiked ? Colors.red.shade400 : Colors.white,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildProgressSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          crossAxisAlignment: CrossAxisAlignment.baseline,
          textBaseline: TextBaseline.alphabetic,
          children: [
            Row(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: [
                Text(
                  raisedAmount,
                  style: AppTypography.sectionTitle.copyWith(fontSize: 22),
                ),
                const SizedBox(width: AppSpacing.xs),
                Text(
                  'EUR',
                  style: AppTypography.meta.copyWith(
                    color: AppColors.textSecondary,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
            Text(
              '$investorsCount investisseur${investorsCount > 1 ? 's' : ''}',
              style: AppTypography.meta,
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: progress.clamp(0.0, 1.0),
            minHeight: 6,
            backgroundColor: AppColors.placeholderBg,
            valueColor: const AlwaysStoppedAnimation<Color>(AppColors.textPrimary),
          ),
        ),
      ],
    );
  }

  Widget _buildReturnAndDuration() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (annualizedReturnPercent != null)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.xs),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Rendement annualisé', style: AppTypography.meta),
                Text(
                  '${annualizedReturnPercent!.toStringAsFixed(2)} %',
                  style: AppTypography.meta.copyWith(
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                  ),
                ),
              ],
            ),
          ),
        if (targetDurationMonths != null)
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Durée cible', style: AppTypography.meta),
              Text(
                '$targetDurationMonths mois',
                style: AppTypography.meta.copyWith(
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
      ],
    );
  }

  Widget _placeholder() => Container(
        color: AppColors.placeholderBg,
        child: Icon(
          Icons.image_not_supported,
          color: AppColors.placeholderIcon,
          size: 48,
        ),
      );
}
