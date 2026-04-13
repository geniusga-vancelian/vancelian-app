import 'package:flutter/material.dart';

import '../../../../core/config.dart';
import '../../../../design_system/design_system.dart';

/// Données mockées pour un asset crypto.
class CryptoAssetItem {
  const CryptoAssetItem({
    required this.name,
    required this.ticker,
    required this.price,
    required this.variationPercent,
    this.redirectUrl = '',
    this.icon = Icons.currency_bitcoin,
    this.logoUrl,
  });

  final String name;
  final String ticker;
  final String price;
  final double variationPercent;
  final String redirectUrl;
  final IconData icon;
  final String? logoUrl;
}

enum TopCryptoTab { favoris, populaires, enHausse, enBaisse }

/// Module "Top Crypto" : tabulations + liste d'assets dans un conteneur blanc.
///
/// Utilise [SettingsCard] + [SettingsListItem] du design system.
class TopCryptoAssetsModule extends StatefulWidget {
  const TopCryptoAssetsModule({
    super.key,
    this.onAssetTap,
    this.onSeeMoreTap,
    this.onTabChanged,
    this.seeMoreLabel = 'See more',
    this.popularLabel = 'Populaires',
    this.gainersLabel = 'Gainers',
    this.losersLabel = 'Losers',
    this.favoritesLabel = 'Favoris',
    this.popularAssets,
    this.gainerAssets,
    this.loserAssets,
    this.favoriteAssets,
  });

  final void Function(CryptoAssetItem asset)? onAssetTap;
  final VoidCallback? onSeeMoreTap;
  final void Function(TopCryptoTab tab)? onTabChanged;
  final String seeMoreLabel;
  final String popularLabel;
  final String gainersLabel;
  final String losersLabel;
  final String favoritesLabel;
  final List<CryptoAssetItem>? popularAssets;
  final List<CryptoAssetItem>? gainerAssets;
  final List<CryptoAssetItem>? loserAssets;
  final List<CryptoAssetItem>? favoriteAssets;

  @override
  State<TopCryptoAssetsModule> createState() => _TopCryptoAssetsModuleState();
}

class _TopCryptoAssetsModuleState extends State<TopCryptoAssetsModule> {
  TopCryptoTab _selectedTab = TopCryptoTab.populaires;

  static const List<CryptoAssetItem> _populaires = [
    CryptoAssetItem(name: 'Bitcoin', ticker: 'BTC', price: '59 644 €', variationPercent: 3.25),
    CryptoAssetItem(name: 'Ether', ticker: 'ETH', price: '1 744,19 €', variationPercent: 4.61),
    CryptoAssetItem(name: 'Tether', ticker: 'USDT', price: '0,86 €', variationPercent: 0.22),
    CryptoAssetItem(name: 'XRP', ticker: 'XRP', price: '1,17 €', variationPercent: 1.71),
    CryptoAssetItem(name: 'USDC', ticker: 'USDC', price: '0,86 €', variationPercent: 0.21),
  ];

  static const List<CryptoAssetItem> _enHausse = [
    CryptoAssetItem(name: 'Solana', ticker: 'SOL', price: '178,90 €', variationPercent: 5.12),
    CryptoAssetItem(name: 'Avalanche', ticker: 'AVAX', price: '42,30 €', variationPercent: 4.28),
    CryptoAssetItem(name: 'Bitcoin', ticker: 'BTC', price: '59 644 €', variationPercent: 2.34),
    CryptoAssetItem(name: 'Ether', ticker: 'ETH', price: '1 744,19 €', variationPercent: 1.85),
    CryptoAssetItem(name: 'Cardano', ticker: 'ADA', price: '0,48 €', variationPercent: 1.56),
  ];

  static const List<CryptoAssetItem> _enBaisse = [
    CryptoAssetItem(name: 'XRP', ticker: 'XRP', price: '0,52 €', variationPercent: -1.20),
    CryptoAssetItem(name: 'Dogecoin', ticker: 'DOGE', price: '0,12 €', variationPercent: -2.15),
    CryptoAssetItem(name: 'Binance Coin', ticker: 'BNB', price: '612,40 €', variationPercent: -0.42),
    CryptoAssetItem(name: 'Polkadot', ticker: 'DOT', price: '7,85 €', variationPercent: -0.98),
    CryptoAssetItem(name: 'Chainlink', ticker: 'LINK', price: '14,20 €', variationPercent: -0.65),
  ];

  List<CryptoAssetItem> get _currentAssets {
    final popular = widget.popularAssets ?? _populaires;
    final gainers = widget.gainerAssets ?? _enHausse;
    final losers = widget.loserAssets ?? _enBaisse;
    switch (_selectedTab) {
      case TopCryptoTab.favoris:
        return widget.favoriteAssets ?? [];
      case TopCryptoTab.populaires:
        return popular;
      case TopCryptoTab.enHausse:
        return gainers;
      case TopCryptoTab.enBaisse:
        return losers;
    }
  }

  static String _formatVariation(double value) {
    final abs = value.abs();
    final formatted = abs.toStringAsFixed(2).replaceAll('.', ',');
    if (value >= 0) return '▲ $formatted %';
    return '▼ $formatted %';
  }

  static String? _resolveLogoUrl(String ticker, String? apiLogoUrl) {
    final resolved = Config.resolveLogoUrl(apiLogoUrl);
    if (resolved != null && resolved.isNotEmpty) return resolved;
    final slug = ticker.trim().toLowerCase();
    if (slug.isEmpty) return null;
    return Config.resolveLogoUrl('/media/crypto_logos/$slug.png');
  }

  List<_TabOption> get _tabOptions => [
        _TabOption(id: TopCryptoTab.favoris, label: widget.favoritesLabel),
        _TabOption(id: TopCryptoTab.populaires, label: widget.popularLabel),
        _TabOption(id: TopCryptoTab.enHausse, label: widget.gainersLabel),
        _TabOption(id: TopCryptoTab.enBaisse, label: widget.losersLabel),
      ];

  @override
  Widget build(BuildContext context) {
    final assets = _currentAssets;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: Row(
            children: [
              const Expanded(child: AppSectionTitle('Top Crypto')),
              SizedBox(
                height: 32,
                child: Center(
                  child: GestureDetector(
                    onTap: widget.onSeeMoreTap,
                    behavior: HitTestBehavior.opaque,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.sm,
                        vertical: AppSpacing.xs,
                      ),
                      child: Text(
                        widget.seeMoreLabel,
                        style: AppTypography.title2.copyWith(
                          color: AppColors.accent,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: SettingsCard(
            children: [
              _CryptoPillTabBar(
                options: _tabOptions,
                selectedTab: _selectedTab,
                onChanged: (tab) {
                  setState(() => _selectedTab = tab);
                  widget.onTabChanged?.call(tab);
                },
              ),
              if (assets.isEmpty)
                _EmptyStatePlaceholder(
                  message: _selectedTab == TopCryptoTab.favoris
                      ? 'Appuyez sur ★ pour ajouter des favoris'
                      : 'Aucune donnée pour cette catégorie',
                  icon: _selectedTab == TopCryptoTab.favoris
                      ? Icons.star_border_rounded
                      : Icons.show_chart_rounded,
                )
              else
                ...assets.map(_buildAssetRow),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildAssetRow(CryptoAssetItem asset) {
    final isPositive = asset.variationPercent >= 0;
    final variationColor = isPositive ? AppColors.green : AppColors.red;
    final resolvedUrl = _resolveLogoUrl(asset.ticker, asset.logoUrl);

    return SettingsListItem(
      leading: CryptoAvatar(
        ticker: asset.ticker,
        logoUrl: resolvedUrl,
        fallbackIcon: asset.icon,
      ),
      title: asset.name,
      subtitle: asset.ticker,
      value: asset.price,
      valueSubtext: _formatVariation(asset.variationPercent),
      valueSubtextColor: variationColor,
      onTap: widget.onAssetTap != null ? () => widget.onAssetTap!(asset) : null,
    );
  }
}


class _EmptyStatePlaceholder extends StatelessWidget {
  const _EmptyStatePlaceholder({
    this.message = 'Aucune donnée pour cette catégorie',
    this.icon = Icons.show_chart_rounded,
  });

  final String message;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xxl * 1.5),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 40,
            color: AppColors.textSecondary.withValues(alpha: 0.5),
          ),
          const SizedBox(height: AppSpacing.md),
          Text(
            message,
            style: AppTypography.meta.copyWith(
              color: AppColors.textSecondary,
              fontSize: 14,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

// ─────────────── Tab model ───────────────

class _TabOption {
  const _TabOption({required this.id, required this.label});
  final TopCryptoTab id;
  final String label;
}

// ─────────────── Pill Tab Bar (sliding animation) ───────────────

class _CryptoPillTabBar extends StatefulWidget {
  const _CryptoPillTabBar({
    required this.options,
    required this.selectedTab,
    required this.onChanged,
  });

  final List<_TabOption> options;
  final TopCryptoTab selectedTab;
  final ValueChanged<TopCryptoTab> onChanged;

  @override
  State<_CryptoPillTabBar> createState() => _CryptoPillTabBarState();
}

class _CryptoPillTabBarState extends State<_CryptoPillTabBar> {
  static const double _height = 32;
  static const double _outerPad = 2;
  static const double _innerH = _height - _outerPad * 2;
  static const double _pillRadius = 9999;

  static const _labelStyle = TextStyle(
    fontFamily: 'Inter',
    fontSize: 13,
    fontWeight: FontWeight.w600,
    letterSpacing: -0.08,
    height: 1.0,
  );

  final List<GlobalKey> _keys = [];
  final Map<int, _TabMetrics> _metrics = {};

  @override
  void initState() {
    super.initState();
    _syncKeys();
    WidgetsBinding.instance.addPostFrameCallback((_) => _measure());
  }

  @override
  void didUpdateWidget(covariant _CryptoPillTabBar old) {
    super.didUpdateWidget(old);
    if (old.options.length != widget.options.length) {
      _syncKeys();
      WidgetsBinding.instance.addPostFrameCallback((_) => _measure());
    }
  }

  void _syncKeys() {
    while (_keys.length < widget.options.length) {
      _keys.add(GlobalKey());
    }
  }

  void _measure() {
    final parentBox = context.findRenderObject() as RenderBox?;
    if (parentBox == null) return;
    final parentOffset = parentBox.localToGlobal(Offset.zero);

    for (var i = 0; i < widget.options.length; i++) {
      final box =
          _keys[i].currentContext?.findRenderObject() as RenderBox?;
      if (box == null) continue;
      final pos = box.localToGlobal(Offset.zero);
      _metrics[i] = _TabMetrics(
        left: pos.dx - parentOffset.dx,
        width: box.size.width,
      );
    }
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final selectedIdx = widget.options
        .indexWhere((o) => o.id == widget.selectedTab)
        .clamp(0, widget.options.length - 1);

    final activeMetrics = _metrics[selectedIdx];

    return Container(
      height: _height,
      decoration: BoxDecoration(
        color: const Color(0xFFF2F2F7),
        borderRadius: BorderRadius.circular(_pillRadius),
      ),
      padding: const EdgeInsets.all(_outerPad),
      child: Stack(
        children: [
          if (activeMetrics != null)
            AnimatedPositioned(
              duration: const Duration(milliseconds: 250),
              curve: Curves.easeInOut,
              left: activeMetrics.left - _outerPad,
              width: activeMetrics.width,
              top: 0,
              bottom: 0,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(_pillRadius),
                  boxShadow: const [
                    BoxShadow(
                      color: Color(0x0D000000),
                      blurRadius: 4,
                      offset: Offset(0, 1),
                    ),
                  ],
                ),
              ),
            ),
          Row(
            children: [
              for (var i = 0; i < widget.options.length; i++)
                Expanded(
                  child: GestureDetector(
                    key: _keys[i],
                    onTap: () {
                      widget.onChanged(widget.options[i].id);
                      WidgetsBinding.instance
                          .addPostFrameCallback((_) => _measure());
                    },
                    behavior: HitTestBehavior.opaque,
                    child: SizedBox(
                      height: _innerH,
                      child: Center(
                        child: TweenAnimationBuilder<Color?>(
                          tween: ColorTween(
                            end: i == selectedIdx
                                ? AppColors.textPrimary
                                : const Color(0xFF8E8E93),
                          ),
                          duration: const Duration(milliseconds: 250),
                          curve: Curves.easeInOut,
                          builder: (_, color, __) => Text(
                            widget.options[i].label,
                            style: _labelStyle.copyWith(color: color),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _TabMetrics {
  const _TabMetrics({required this.left, required this.width});
  final double left;
  final double width;
}
