import 'dart:ui';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../atoms/atoms.dart';
import 'app_back_button.dart';
import 'app_small_button.dart';
import 'ds_news_tag.dart';

/// Carte d'investissement immersive avec image, overlay gradient, badges,
/// informations financières, barre de progression et section de contenu blanche.
///
/// Spécifications Figma :
/// - Image section : 242px, gradient overlay transparent→noir 0.5 à 45.66%
/// - Badges : [DsNewsTag] (même pastilles que [NewsCard] — point + libellé)
/// - Bouton favori : [AppBackButton] 29px
/// - Montant : bodyEmphasized / blanc
/// - Investisseurs : bodySmRegular / blanc avec icône
/// - Barre de progression : 8px, backdrop blur, fill blanc
/// - Contenu : fond blanc, shadow, titre + description + bouton "Investir"
class InvestmentCard extends StatelessWidget {
  const InvestmentCard({
    super.key,
    required this.imageUrl,
    required this.category,
    required this.status,
    required this.title,
    required this.description,
    required this.amount,
    required this.investorsCount,
    required this.progressLabel,
    required this.progressValue,
    required this.progress,
    this.onTap,
    this.onInvest,
    this.onFavorite,
  });

  final String imageUrl;
  final String category;
  final String status;
  final String title;
  final String description;
  final String amount;
  final int investorsCount;
  final String progressLabel;
  final String progressValue;
  final double progress;
  final VoidCallback? onTap;
  final VoidCallback? onInvest;
  final VoidCallback? onFavorite;

  static const double _imageHeight = 242;
  static const double _progressTrackHeight = 8;
  static const double _progressTrackRadius = 10;
  static const double _blur = 12;
  static const double _favoriteButtonSize = 29;

  /// Même pastille que [NewsCard] / [DsNewsTag] ; vert si offre financée.
  static Color _statusTagDotColor(String status) {
    final s = status.trim().toLowerCase();
    if (s.contains('financ')) {
      return const Color(0xFF059669);
    }
    return const Color(0xFFFF383C);
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(AppRadius.lg),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _buildImageSection(),
            _buildContentSection(),
          ],
        ),
      ),
    );
  }

  // ─────────────── Image section ───────────────

  Widget _buildImageSection() {
    return SizedBox(
      height: _imageHeight,
      child: Stack(
        fit: StackFit.expand,
        children: [
          _buildBackground(),
          _buildGradientOverlay(),
          _buildOverlayContent(),
        ],
      ),
    );
  }

  Widget _buildBackground() {
    final url = imageUrl.trim();
    if (url.isEmpty) {
      return Container(color: AppColors.gray6);
    }
    return CachedNetworkImage(
      imageUrl: url,
      fit: BoxFit.cover,
      placeholder: (_, __) => Container(color: AppColors.gray6),
      errorWidget: (_, __, ___) => Container(color: AppColors.gray6),
    );
  }

  Widget _buildGradientOverlay() {
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Colors.transparent,
            AppColors.black.withValues(alpha: 0.5),
          ],
          stops: const [0.4566, 1.0],
        ),
      ),
    );
  }

  Widget _buildOverlayContent() {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.s4),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          _buildTopRow(),
          _buildBottomInfo(),
        ],
      ),
    );
  }

  // ─────────────── Top row : badges + favorite ───────────────

  Widget _buildTopRow() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Flexible(
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              DsNewsTag(
                label: category,
                dotColor: const Color(0xFFFF383C),
              ),
              const SizedBox(width: 6),
              DsNewsTag(
                label: status,
                dotColor: _statusTagDotColor(status),
              ),
            ],
          ),
        ),
        AppBackButton(
          size: _favoriteButtonSize,
          variant: AppBackButtonVariant.glassDark,
          onPressed: onFavorite,
          child: const Icon(
            Icons.diamond_outlined,
            color: AppColors.white,
            size: 13,
          ),
        ),
      ],
    );
  }

  // ─────────────── Bottom info : amount + investors + progress ───────────────

  Widget _buildBottomInfo() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildAmountRow(),
        const SizedBox(height: AppSpacing.s2),
        _buildProgressBar(),
      ],
    );
  }

  Widget _buildAmountRow() {
    return Row(
      children: [
        Expanded(
          child: Text(
            amount,
            style: AppTypography.bodyEmphasized.copyWith(
              color: AppColors.white,
            ),
          ),
        ),
        const SizedBox(width: 10),
        _buildInvestorCount(),
      ],
    );
  }

  Widget _buildInvestorCount() {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(
          Icons.people_outline_rounded,
          color: AppColors.white,
          size: 15,
        ),
        const SizedBox(width: AppSpacing.s1),
        Text(
          '$investorsCount Investers',
          style: AppTypography.bodySmRegular.copyWith(
            color: AppColors.white,
          ),
        ),
      ],
    );
  }

  // ─────────────── Progress bar ───────────────

  Widget _buildProgressBar() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(_progressTrackRadius),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: _blur, sigmaY: _blur),
            child: Container(
              height: _progressTrackHeight,
              decoration: BoxDecoration(
                color: AppColors.darkOpacity30,
                borderRadius: BorderRadius.circular(_progressTrackRadius),
              ),
              alignment: Alignment.centerLeft,
              child: FractionallySizedBox(
                widthFactor: progress.clamp(0.0, 1.0),
                child: Container(
                  decoration: BoxDecoration(
                    color: AppColors.white,
                    borderRadius: BorderRadius.circular(_progressTrackRadius),
                  ),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.s1),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              progressLabel,
              style: AppTypography.bodySmRegular.copyWith(
                color: AppColors.white,
              ),
            ),
            Text(
              progressValue,
              style: AppTypography.bodySmRegular.copyWith(
                color: AppColors.white,
              ),
            ),
          ],
        ),
      ],
    );
  }

  // ─────────────── Content section (blanc) ───────────────

  Widget _buildContentSection() {
    return Container(
      decoration: const BoxDecoration(
        color: AppColors.white,
        boxShadow: [
          BoxShadow(
            blurRadius: 20,
            spreadRadius: -10,
            color: Color(0x1F000000),
          ),
        ],
      ),
      padding: const EdgeInsets.all(AppSpacing.s4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: AppTypography.itemPrimary.copyWith(
                    color: AppColors.black,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  description,
                  style: AppTypography.itemSupporting.copyWith(
                    color: AppColors.gray,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.s5),
          AppSmallButton(label: 'Investir', onPressed: onInvest),
        ],
      ),
    );
  }
}
