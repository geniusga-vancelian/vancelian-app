import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Carte "Assets Bundle" : cercles crypto en décalé, titre, description 2 lignes, perf 24h, pas de bouton.
class AssetsBundleCard extends StatelessWidget {
  const AssetsBundleCard({
    super.key,
    required this.imageUrl,
    required this.title,
    this.description,
    this.performance24h,
    required this.cryptoIcons,
    this.themeColor,
    this.onTap,
  });

  final String imageUrl;
  final String title;
  final String? description;
  final double? performance24h;
  /// Icônes des cryptos affichées en cercles décalés en haut à gauche ; **+N** au-delà de 10.
  final List<IconData> cryptoIcons;
  /// Couleur de thème pour l'arrière-plan (dégradé overlay).
  final Color? themeColor;
  final VoidCallback? onTap;

  /// Même taille que TransactionAvatar (lignes de transaction).
  static const double _circleSize = 44;
  static const double _circleOffset = 22;
  static const Color _positiveColor = Color(0xFF059669);
  static const Color _negativeColor = Color(0xFFDC2626);

  @override
  Widget build(BuildContext context) {
    final perf = performance24h;
    final hasPerformance = perf != null;
    final isPositive = hasPerformance ? perf >= 0 : true;
    final perfColor = isPositive ? _positiveColor : _negativeColor;
    final perfText = hasPerformance
        ? '${isPositive ? '+' : ''}${perf.toStringAsFixed(2)} %'
        : '';

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.card),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppRadius.card),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.08),
                blurRadius: 12,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: ClipRRect(
          borderRadius: BorderRadius.circular(AppRadius.card),
          child: Stack(
            fit: StackFit.expand,
            children: [
              imageUrl.isNotEmpty
                  ? Image.network(
                      imageUrl,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => _placeholder(),
                    )
                  : _placeholder(),
              if (themeColor != null)
                DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        themeColor!.withValues(alpha: 0.35),
                        themeColor!.withValues(alpha: 0.2),
                        themeColor!.withValues(alpha: 0.4),
                        themeColor!.withValues(alpha: 0.7),
                      ],
                      stops: const [0.0, 0.3, 0.65, 1.0],
                    ),
                  ),
                ),
              DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Colors.transparent,
                      Colors.black.withValues(alpha: 0.2),
                      Colors.black.withValues(alpha: 0.6),
                      Colors.black.withValues(alpha: 0.8),
                    ],
                    stops: const [0.0, 0.3, 0.65, 1.0],
                  ),
                ),
              ),
              Positioned(
                left: AppSpacing.lg,
                top: AppSpacing.lg,
                child: _buildCryptoIconsStack(),
              ),
              Positioned(
                left: AppSpacing.lg,
                right: AppSpacing.lg,
                bottom: AppSpacing.xl,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      title,
                      style: AppTypography.sectionTitle.copyWith(
                        fontWeight: FontWeight.w800,
                        color: Colors.white,
                        height: 1.2,
                        fontSize: 20,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (description != null && description!.isNotEmpty) ...[
                      const SizedBox(height: AppSpacing.xs),
                      Text(
                        description!,
                        style: AppTypography.bodyMedium.copyWith(
                          fontWeight: FontWeight.w500,
                          color: Colors.white.withValues(alpha: 0.95),
                          height: 1.3,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                    if (hasPerformance) ...[
                      const SizedBox(height: AppSpacing.sm),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.sm,
                          vertical: AppSpacing.xs,
                        ),
                        decoration: BoxDecoration(
                          color: perfColor.withValues(alpha: 0.9),
                          borderRadius: BorderRadius.circular(AppRadius.chip),
                        ),
                        child: Text(
                          perfText,
                          style: AppTypography.meta.copyWith(
                            color: Colors.white,
                            fontWeight: FontWeight.w600,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
        ),
      ),
    );
  }

  static const int _maxVisibleCircles = 10;

  Widget _buildCryptoIconsStack() {
    final icons = cryptoIcons.toList();
    if (icons.isEmpty) return const SizedBox.shrink();

    final displayCount = icons.length <= _maxVisibleCircles
        ? icons.length
        : _maxVisibleCircles;
    final remainder = icons.length - _maxVisibleCircles;
    final showPlusText = remainder > 0;

    final visibleIcons = icons.take(displayCount).toList();

    return SizedBox(
      height: _circleSize,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          SizedBox(
            width: _circleSize + (displayCount - 1) * _circleOffset,
            height: _circleSize,
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                for (var i = 0; i < visibleIcons.length; i++)
                  Positioned(
                    left: i * _circleOffset.toDouble(),
                    child: _buildCircle(visibleIcons[i]),
                  ),
              ],
            ),
          ),
          if (showPlusText) ...[
            const SizedBox(width: AppSpacing.sm),
            Padding(
              padding: const EdgeInsets.only(bottom: 2),
              child: Text(
                '+$remainder',
                style: AppTypography.meta.copyWith(
                  fontWeight: FontWeight.w700,
                  fontSize: 15,
                  color: Colors.white.withValues(alpha: 0.95),
                ),
              ),
            ),
          ],
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
          color: Colors.white.withValues(alpha: 0.45),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.25),
            blurRadius: 6,
            offset: const Offset(0, 2),
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

  Widget _placeholder() => Container(
        color: AppColors.placeholderBg,
        child: Icon(
          Icons.image_not_supported,
          color: AppColors.placeholderIcon,
          size: 32,
        ),
      );
}
