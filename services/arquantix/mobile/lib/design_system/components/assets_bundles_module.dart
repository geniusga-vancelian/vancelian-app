import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'app_section_title.dart';
import 'app_small_button.dart';
import 'basket_card.dart';
import 'bundle_ticker_avatar_row.dart';

/// Performance mockée quand l'API n'envoie pas de perf (vert/rouge alterné).
double _mockPerformanceForIndex(int index) =>
    index.isEven ? 2.45 : -0.32;

/// Top 2 market cap tickers.
const _top2Tickers = ['BTC', 'ETH'];

/// Top 5 market cap tickers.
const _top5Tickers = ['BTC', 'ETH', 'USDT', 'BNB', 'SOL'];

/// Au-delà de ce nombre d’actifs sur la carte, le surplus est regroupé en **+N**
/// (aligné header détail bundle : [BundleTickerAvatarRow]).
const int _maxVisibleAvatarsOnCard = 10;

/// Résout les tickers effectifs d'un item (tickers dynamiques, sinon fallback sur titre).
List<String> _effectiveTickers(AssetsBundleItem item) {
  if (item.cryptoTickers.isNotEmpty) return item.cryptoTickers;
  final t = item.title.trim().toLowerCase();
  if (t.contains('top 2') || t.contains('top2')) return _top2Tickers;
  if (t.contains('top 5') || t.contains('top5')) return _top5Tickers;
  return [];
}

/// Élément pour [AssetsBundlesModule].
class AssetsBundleItem {
  const AssetsBundleItem({
    required this.imageUrl,
    required this.title,
    this.description,
    this.performance24h,
    required this.cryptoIcons,
    this.cryptoTickers = const [],
    this.themeColor,
    this.onTap,
    this.onInvestTap,
  });

  final String imageUrl;
  final String title;
  final String? description;
  final double? performance24h;
  final List<IconData> cryptoIcons;
  /// Symboles des cryptos pour les avatars (ex. ['BTC', 'ETH', 'SOL']).
  /// Ordre attendu : **poids d’allocation croissant** (faible à gauche, fort à droite),
  /// comme le header détail bundle — le catalogue remplit ainsi via [ProductCatalogItem.toAssetsBundleItem].
  final List<String> cryptoTickers;
  /// Couleur de thème pour l'arrière-plan (dégradé overlay).
  final Color? themeColor;
  final VoidCallback? onTap;
  /// Separate callback for the "Investir" CTA button on the card.
  /// When set, card tap navigates to detail while button tap triggers invest.
  final VoidCallback? onInvestTap;
}

/// Valeur par défaut du nombre de cartes visibles (1,05 = 1 pleine + léger peek).
const double _defaultVisibleCardsCount = 1.05;

/// Marge horizontale (alignée sur Marketing Cards).
const double _horizontalMargin = AppSpacing.xl;

const double _gapBetweenCards = AppSpacing.md;

/// Hauteur carte : image (4/3) + zone blanche (avatars 24, gap 8, titre 20, perf 16, paddings).
double _bundleCardHeightForWidth(double cardWidth) =>
    cardWidth * (3 / 4) + 100;

/// Module "Assets Bundles" (Crypto Bundles) : image + zone blanche style BasketCard
/// (avatars superposés, titre, performance colorée, bouton "Investir" aligné en bas).
class AssetsBundlesModule extends StatelessWidget {
  const AssetsBundlesModule({
    super.key,
    required this.items,
    this.title = 'Thematic investing',
    this.visibleCardsCount,
    this.showImageOverlay = false,
  });

  final String title;
  final List<AssetsBundleItem> items;
  final double? visibleCardsCount;
  final bool showImageOverlay;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const SizedBox.shrink();
    final hasTitle = title.trim().isNotEmpty;
    final count = visibleCardsCount ?? _defaultVisibleCardsCount;

    final screenWidth = MediaQuery.sizeOf(context).width;
    final availableWidth = screenWidth - _horizontalMargin * 2;
    final cardWidth = availableWidth / count;
    final cardHeight = _bundleCardHeightForWidth(cardWidth);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (hasTitle) ...[
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
            child: AppSectionTitle(title),
          ),
          const SizedBox(height: AppSpacing.md),
        ],
        SizedBox(
          height: cardHeight,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
            itemCount: items.length,
            separatorBuilder: (_, __) => const SizedBox(width: _gapBetweenCards),
            itemBuilder: (context, index) {
              final item = items[index];
              final perf = item.performance24h ?? _mockPerformanceForIndex(index);
              final isPositive = perf >= 0;
              final perfText = '${isPositive ? '+' : ''}${perf.toStringAsFixed(2)}%';

              final tickers = _effectiveTickers(item);

              return SizedBox(
                width: cardWidth,
                child: _BundleCard(
                  imageUrl: item.imageUrl,
                  title: item.title,
                  perfText: perfText,
                  perfPositive: isPositive,
                  avatarTickers: tickers,
                  maxAvatarTickersDisplayed: _maxVisibleAvatarsOnCard,
                  showImageOverlay: showImageOverlay,
                  onTap: item.onTap,
                  onInvestTap: item.onInvestTap,
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

/// Carte bundle interne : image + zone blanche avec avatars, titre, perf, bouton.
class _BundleCard extends StatelessWidget {
  const _BundleCard({
    required this.imageUrl,
    required this.title,
    required this.perfText,
    required this.perfPositive,
    required this.avatarTickers,
    required this.maxAvatarTickersDisplayed,
    this.showImageOverlay = false,
    this.onTap,
    this.onInvestTap,
  });

  final String imageUrl;
  final String title;
  final String perfText;
  final bool perfPositive;
  final List<String> avatarTickers;
  final int maxAvatarTickersDisplayed;
  final bool showImageOverlay;
  final VoidCallback? onTap;
  final VoidCallback? onInvestTap;

  static const double _imageAspectRatio = 4 / 3;

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
    return AspectRatio(
      aspectRatio: _imageAspectRatio,
      child: Stack(
        fit: StackFit.expand,
        children: [
          imageUrl.isNotEmpty
              ? CachedNetworkImage(
                  imageUrl: imageUrl,
                  fit: BoxFit.cover,
                  fadeInDuration: Duration.zero,
                  fadeOutDuration: Duration.zero,
                  placeholder: (_, __) => _placeholder(),
                  errorWidget: (_, __, ___) => _placeholder(),
                )
              : _placeholder(),
          if (showImageOverlay)
            const DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [Color(0x12000000), Color(0x55000000), Color(0xCC000000)],
                  stops: [0.3, 0.62, 1],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildBottomSection() {
    return Container(
      color: AppColors.cardBackground,
      padding: const EdgeInsets.all(16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                if (avatarTickers.isNotEmpty)
                  BundleTickerAvatarRow(
                    orderedSymbols: avatarTickers,
                    maxDisplayed: maxAvatarTickersDisplayed,
                  ),
                if (avatarTickers.isNotEmpty) const SizedBox(height: 8),
                Text(
                  title,
                  style: AppTypography.bodyEmphasized.copyWith(
                    fontSize: 15,
                    height: 20 / 15,
                    letterSpacing: -0.23,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                PercentageLabel(value: perfText, positive: perfPositive),
              ],
            ),
          ),
          const SizedBox(width: 12),
          AppSmallButton(label: 'Investir', onPressed: onInvestTap ?? onTap),
        ],
      ),
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
