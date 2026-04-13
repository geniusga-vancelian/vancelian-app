import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'app_small_button.dart';
import 'ds_news_tag.dart';

/// Carte réutilisable : image (optionnel bloc progression) + zone blanche (assets, titre, description ou perf %, bouton optionnel).
/// Utilisable pour Exclusive offers (avec barre de progression) et Crypto Bundles (avec performance % et icônes assets).
class FeaturedOfferCard extends StatelessWidget {
  const FeaturedOfferCard({
    super.key,
    this.imageCacheKey,
    required this.imageUrl,
    this.category,
    this.assetIcons,
    this.assetLogoUrls,
    required this.title,
    this.description,
    this.performancePercent,
    this.actionLabel,
    this.onActionTap,
    required this.onTap,
    this.showProgressBlock = false,
    this.showImageOverlay = true,
    this.progress = 0,
    this.raisedAmount = '',
    this.investorsCount = 0,
    this.targetAmountLabel,
  });

  final String? imageCacheKey;
  final String imageUrl;
  final String? category;
  /// Icônes d'assets (ex. crypto) affichées au-dessus du titre dans la zone blanche.
  final List<IconData>? assetIcons;
  /// URLs des logos crypto affichés au-dessus du titre (prioritaire sur [assetIcons] si non vide).
  final List<String>? assetLogoUrls;
  final String title;
  /// Description texte (zone blanche). Ignoré si [performancePercent] est non null.
  final String? description;
  /// Pourcentage de performance (style crypto détail : vert/rouge + caret). Prioritaire sur [description].
  final double? performancePercent;
  /// Label du bouton (ex. "Investir"). Si null, pas de bouton.
  final String? actionLabel;
  /// Separate callback for the action button. Falls back to [onTap] if null.
  final VoidCallback? onActionTap;
  final VoidCallback onTap;

  /// Afficher le bloc montant / barre de progression / "Financement total" sur l'image.
  final bool showProgressBlock;
  /// Afficher le filtre gris (dégradé) sur l'image. Si false, l'image reste sans overlay (ex. Crypto Bundles).
  final bool showImageOverlay;
  final double progress;
  final String raisedAmount;
  final int investorsCount;
  final String? targetAmountLabel;

  static const double _imageAspectRatio = 4 / 3;
  static const double _progressBarHeight = 8;
  static const Color _positiveColor = Color(0xFF059669);
  static const Color _negativeColor = Color(0xFFDC2626);

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
                color: Colors.black.withValues(alpha: 0.1),
                blurRadius: 18,
                offset: const Offset(0, 6),
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
        if (showImageOverlay)
          const Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [Color(0x12000000), Color(0x55000000), Color(0xCC000000)],
                  stops: [0.3, 0.62, 1],
                ),
              ),
            ),
          ),
        if (category != null && category!.trim().isNotEmpty) _buildCategoryTag(),
        if (showProgressBlock)
          Positioned(
            left: AppSpacing.lg,
            right: AppSpacing.lg,
            bottom: AppSpacing.md,
            child: _buildImageMetrics(),
          ),
      ],
    );
  }

  /// Disques crypto superposés sur l’image (style AssetsBundleCard).
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
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.groups_2_outlined,
                  size: 20,
                  color: Colors.white,
                ),
                const SizedBox(width: 6),
                Text(
                  '$investorsCount Investors',
                  style: AppTypography.bodyMedium.copyWith(
                    color: Colors.white.withValues(alpha: 0.95),
                  ),
                ),
              ],
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        _buildRoundedProgressBar(),
        const SizedBox(height: 2),
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
              targetAmountLabel ?? _computeTargetAmountLabel(),
              style: AppTypography.bodyMedium.copyWith(
                color: Colors.white.withValues(alpha: 0.95),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildBottomSection() {
    final hasPerformance = performancePercent != null;
    final effectiveDescription = !hasPerformance && (description ?? '').trim().isNotEmpty
        ? description!.trim()
        : null;
    final hasAssetLogos = assetLogoUrls != null && assetLogoUrls!.isNotEmpty;
    final hasAssetIcons = !hasAssetLogos && assetIcons != null && assetIcons!.isNotEmpty;

    return Container(
      color: AppColors.cardBackground,
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        14,
        AppSpacing.lg,
        AppSpacing.md,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (hasAssetLogos || hasAssetIcons) ...[
            SizedBox(
              width: double.infinity,
              child: Align(
                alignment: Alignment.centerLeft,
                child: hasAssetLogos
                    ? _AssetLogoUrlsRow(logoUrls: assetLogoUrls!)
                    : _AssetIconsRow(icons: assetIcons!),
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
          ],
          Padding(
            padding: const EdgeInsets.only(bottom: 4),
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
                      style: AppTypography.titleMedium.copyWith(
                        fontWeight: FontWeight.w700,
                        color: AppColors.textPrimary,
                        fontSize: 16,
                        height: 1.2,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (effectiveDescription != null) ...[
                      const SizedBox(height: AppSpacing.xs),
                      Text(
                        effectiveDescription,
                        style: AppTypography.bodyMedium.copyWith(
                          color: AppColors.textSecondary,
                          height: 1.25,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                    if (hasPerformance) ...[
                      const SizedBox(height: 2),
                      _PerformanceRow(percent: performancePercent!),
                    ],
                  ],
                ),
              ),
              if (actionLabel != null && actionLabel!.trim().isNotEmpty) ...[
                const SizedBox(width: AppSpacing.md),
                AppSmallButton(
                  onPressed: onActionTap ?? onTap,
                  label: actionLabel!,
                ),
              ],
            ],
          ),
        ),
        ],
      ),
    );
  }

  Widget _buildCategoryTag() {
    return Positioned(
      top: AppSpacing.lg,
      left: AppSpacing.lg,
      child: DsNewsTag(
        label: category!,
        dotColor: const Color(0xFFFF383C),
      ),
    );
  }

  Widget _buildRoundedProgressBar() {
    final hasInvestment = investorsCount > 0 && progress > 0;
    final effectiveProgress = hasInvestment
        ? progress.clamp(0.01, 1.0)
        : progress.clamp(0.0, 1.0);
    final r = _progressBarHeight / 2;

    return LayoutBuilder(
      builder: (context, constraints) {
        final totalWidth = constraints.maxWidth;
        final rawFill = totalWidth * effectiveProgress;
        // Minimum width = bar height so the capsule shape is always visible.
        final fillWidth = effectiveProgress > 0
            ? rawFill.clamp(_progressBarHeight, totalWidth)
            : 0.0;

        return Container(
          height: _progressBarHeight,
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.35),
            borderRadius: BorderRadius.circular(r),
          ),
          child: fillWidth > 0
              ? Align(
                  alignment: Alignment.centerLeft,
                  child: Container(
                    width: fillWidth,
                    height: _progressBarHeight,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(r),
                    ),
                  ),
                )
              : null,
        );
      },
    );
  }

  String _computeTargetAmountLabel() {
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

  Widget _placeholder() => Container(
        color: AppColors.placeholderBg,
        child: Icon(
          Icons.image_not_supported,
          color: AppColors.placeholderIcon,
          size: 48,
        ),
      );
}

/// Ligne d’icônes assets (ex. crypto) au-dessus du titre : cercles décalés + « +N » si plus de 4.
TextStyle _assetRowTitleStyle() => AppTypography.title2.copyWith(
      color: AppColors.textPrimary,
      fontSize: 16,
      height: 1.2,
    );

/// Ligne d'icônes assets (ex. crypto) au-dessus du titre : cercles décalés + disque "+N" si plus de 4.
class _AssetIconsRow extends StatelessWidget {
  const _AssetIconsRow({required this.icons});

  static const double _circleSize = 24;
  static const double _circleOffset = 17;
  static const int _maxVisible = 4;
  static const Color _circleBorderColor = Colors.white;
  static const Color _plusCircleBackground = Color(0xFFE5E7EB);

  final List<IconData> icons;

  @override
  Widget build(BuildContext context) {
    if (icons.isEmpty) return const SizedBox.shrink();
    final displayCount = icons.length <= _maxVisible ? icons.length : _maxVisible;
    final remainder = icons.length - _maxVisible;
    final showPlusCircle = remainder > 0;
    final visibleIcons = icons.take(displayCount).toList();

    final totalCircles = displayCount + (showPlusCircle ? 1 : 0);
    final stackWidth = _circleSize + (totalCircles - 1) * _circleOffset;

    return SizedBox(
      height: _circleSize,
      width: stackWidth,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          for (var i = 0; i < visibleIcons.length; i++)
            Positioned(
              left: i * _circleOffset,
              child: _buildCircle(visibleIcons[i]),
            ),
          if (showPlusCircle)
            Positioned(
              left: displayCount * _circleOffset,
              child: _buildPlusCircle(remainder),
            ),
        ],
      ),
    );
  }

  Widget _buildCircle(IconData icon) {
    return Container(
      width: _circleSize,
      height: _circleSize,
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        shape: BoxShape.circle,
        border: Border.all(
          color: _circleBorderColor,
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 2,
            offset: const Offset(0, 1),
          ),
        ],
      ),
      child: Icon(
        icon,
        size: _circleSize * 0.5,
        color: AppColors.textPrimary,
      ),
    );
  }

  Widget _buildPlusCircle(int remainder) {
    return Container(
      width: _circleSize,
      height: _circleSize,
      decoration: BoxDecoration(
        color: _plusCircleBackground,
        shape: BoxShape.circle,
        border: Border.all(
          color: _circleBorderColor,
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 4,
            offset: const Offset(0, 1),
          ),
        ],
      ),
      alignment: Alignment.center,
      child: Text(
        '+$remainder',
        style: _assetRowTitleStyle().copyWith(fontSize: 12),
      ),
    );
  }
}

/// Ligne de logos crypto (URLs) : cercles 24px, décalage 17px, max 4 visibles + disque "+N".
class _AssetLogoUrlsRow extends StatelessWidget {
  const _AssetLogoUrlsRow({required this.logoUrls});

  static const double _circleSize = 24;
  static const double _circleOffset = 17;
  static const int _maxVisible = 4;
  static const Color _circleBorderColor = Colors.white;
  static const Color _plusCircleBackground = Color(0xFFE5E7EB);

  final List<String> logoUrls;

  @override
  Widget build(BuildContext context) {
    if (logoUrls.isEmpty) return const SizedBox.shrink();
    final displayCount = logoUrls.length <= _maxVisible ? logoUrls.length : _maxVisible;
    final remainder = logoUrls.length - _maxVisible;
    final showPlusCircle = remainder > 0;
    final visibleUrls = logoUrls.take(displayCount).toList();

    final totalCircles = displayCount + (showPlusCircle ? 1 : 0);
    final stackWidth = _circleSize + (totalCircles - 1) * _circleOffset;

    return SizedBox(
      height: _circleSize,
      width: stackWidth,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          for (var i = 0; i < visibleUrls.length; i++)
            Positioned(
              left: i * _circleOffset,
              child: _buildLogoCircle(visibleUrls[i]),
            ),
          if (showPlusCircle)
            Positioned(
              left: displayCount * _circleOffset,
              child: _buildPlusCircle(remainder),
            ),
        ],
      ),
    );
  }

  Widget _buildLogoCircle(String url) {
    return Container(
      width: _circleSize,
      height: _circleSize,
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        shape: BoxShape.circle,
        border: Border.all(
          color: _circleBorderColor,
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 2,
            offset: const Offset(0, 1),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: CachedNetworkImage(
        imageUrl: url,
        fit: BoxFit.cover,
        placeholder: (_, __) => Icon(
          Icons.currency_bitcoin,
          size: _circleSize * 0.5,
          color: AppColors.textSecondary,
        ),
        errorWidget: (_, __, ___) => Icon(
          Icons.currency_bitcoin,
          size: _circleSize * 0.5,
          color: AppColors.textSecondary,
        ),
      ),
    );
  }

  Widget _buildPlusCircle(int remainder) {
    return Container(
      width: _circleSize,
      height: _circleSize,
      decoration: BoxDecoration(
        color: _plusCircleBackground,
        shape: BoxShape.circle,
        border: Border.all(
          color: _circleBorderColor,
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 2,
            offset: const Offset(0, 1),
          ),
        ],
      ),
      alignment: Alignment.center,
      child: Text(
        '+$remainder',
        style: _assetRowTitleStyle().copyWith(fontSize: 12),
      ),
    );
  }
}

/// Ligne de performance type crypto détail : pourcentage vert/rouge + caret.
/// Taille de police alignée sur transaction / top crypto (13px).
class _PerformanceRow extends StatelessWidget {
  const _PerformanceRow({required this.percent});

  static const Color _positiveColor = Color(0xFF059669);
  static const Color _negativeColor = Color(0xFFDC2626);
  static const double _fontSize = 13;
  static const double _caretSize = 18;

  final double percent;

  @override
  Widget build(BuildContext context) {
    final isPositive = percent >= 0;
    final color = isPositive ? _positiveColor : _negativeColor;
    final caret = isPositive ? Icons.arrow_drop_up : Icons.arrow_drop_down;
    final text = '${isPositive ? '+' : ''}${percent.toStringAsFixed(2)} %';

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(caret, color: color, size: _caretSize),
        const SizedBox(width: 2),
        Text(
          text,
          style: AppTypography.bodyMedium.copyWith(
            color: color,
            fontWeight: FontWeight.w600,
            fontSize: _fontSize,
            height: 1.0,
          ),
        ),
      ],
    );
  }
}
