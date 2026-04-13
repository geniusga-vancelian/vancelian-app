import 'package:flutter/material.dart';

import '../../../../core/config.dart';
import '../../../../core/currency_formatter.dart';
import '../../../../design_system/design_system.dart';
import '../../../favorites/data/favorites_api.dart';
import '../../../alerts/presentation/screens/alerts_list_screen.dart';
import '../../../alerts/presentation/screens/orders_list_screen.dart';
import '../../../wallet/presentation/screens/buy_flow/buy_flow_controller.dart';
import '../../data/market_data_api.dart';
import '../../data/market_data_ws_service.dart';
import '../../data/market_display_utils.dart';
import '../../../offers/presentation/widgets/vaults_marketing_cards_feed.dart';
import '../widgets/chart_asset_module.dart';
import '../widgets/top_crypto_assets_module.dart';

/// Page détail instrument (marchés, achat) : fond gris, header clair, graphique dans le hero
/// ([LayoutPageInstrumentDetail]).
class CryptoDetailScreen extends StatefulWidget {
  const CryptoDetailScreen({
    super.key,
    required this.asset,
    this.heroImageUrl,
  });

  final CryptoAssetItem asset;

  /// Optional hero background image URL for the detail page.
  final String? heroImageUrl;

  static CryptoAssetItem assetFromSlug(String slug) {
    switch (slug.trim().toLowerCase()) {
      case 'btc':
        return const CryptoAssetItem(
          name: 'Bitcoin',
          ticker: 'BTC',
          price: '59 644 €',
          variationPercent: 3.25,
          redirectUrl: 'crypto://btc',
        );
      case 'eth':
        return const CryptoAssetItem(
          name: 'Ether',
          ticker: 'ETH',
          price: '1 744,19 €',
          variationPercent: 4.61,
          redirectUrl: 'crypto://eth',
        );
      case 'usdt':
        return const CryptoAssetItem(
          name: 'Tether',
          ticker: 'USDT',
          price: '0,86 €',
          variationPercent: 0.22,
          redirectUrl: 'crypto://usdt',
        );
      case 'xrp':
        return const CryptoAssetItem(
          name: 'XRP',
          ticker: 'XRP',
          price: '1,17 €',
          variationPercent: 1.71,
          redirectUrl: 'crypto://xrp',
        );
      case 'usdc':
        return const CryptoAssetItem(
          name: 'USD Coin',
          ticker: 'USDC',
          price: '0,86 €',
          variationPercent: 0.21,
          redirectUrl: 'crypto://usdc',
        );
      case 'sol':
        return const CryptoAssetItem(
          name: 'Solana',
          ticker: 'SOL',
          price: '178,90 €',
          variationPercent: 5.12,
          redirectUrl: 'crypto://sol',
        );
      case 'avax':
        return const CryptoAssetItem(
          name: 'Avalanche',
          ticker: 'AVAX',
          price: '42,30 €',
          variationPercent: 4.28,
          redirectUrl: 'crypto://avax',
        );
      case 'ada':
        return const CryptoAssetItem(
          name: 'Cardano',
          ticker: 'ADA',
          price: '0,48 €',
          variationPercent: 1.56,
          redirectUrl: 'crypto://ada',
        );
      case 'doge':
        return const CryptoAssetItem(
          name: 'Dogecoin',
          ticker: 'DOGE',
          price: '0,12 €',
          variationPercent: -2.15,
          redirectUrl: 'crypto://doge',
        );
      case 'trx':
        return const CryptoAssetItem(
          name: 'Tron',
          ticker: 'TRX',
          price: '0,24 €',
          variationPercent: 1.38,
          redirectUrl: 'crypto://trx',
        );
      case 'dot':
        return const CryptoAssetItem(
          name: 'Polkadot',
          ticker: 'DOT',
          price: '7,85 €',
          variationPercent: -0.98,
          redirectUrl: 'crypto://dot',
        );
      case 'link':
        return const CryptoAssetItem(
          name: 'Chainlink',
          ticker: 'LINK',
          price: '14,20 €',
          variationPercent: -0.65,
          redirectUrl: 'crypto://link',
        );
      case 'bnb':
        return const CryptoAssetItem(
          name: 'Binance Coin',
          ticker: 'BNB',
          price: '612,40 €',
          variationPercent: -0.42,
          redirectUrl: 'crypto://bnb',
        );
      default:
        final normalized = slug.trim().toUpperCase();
        return CryptoAssetItem(
          name: normalized.isEmpty ? 'Crypto' : normalized,
          ticker: normalized.isEmpty ? '---' : normalized,
          price: '-',
          variationPercent: 0,
          redirectUrl: normalized.isEmpty ? '' : 'crypto://${normalized.toLowerCase()}',
        );
    }
  }

  @override
  State<CryptoDetailScreen> createState() => _CryptoDetailScreenState();
}

class _CryptoDetailScreenState extends State<CryptoDetailScreen> {
  final MarketDataApi _marketDataApi = MarketDataApi();
  final MarketDataWsService _wsService = MarketDataWsService();
  final FavoritesApi _favoritesApi = FavoritesApi();

  bool _loadingSummary = true;
  String? _summaryError;
  MarketSummaryItem? _summary;

  double? _livePriceUsd;

  int _chartTimeframeIndex = 0;
  /// Dernière période pour laquelle [_candles] a été chargée (libellé + perf alignés).
  int _displayTimeframeIndex = 0;
  bool _isLineChart = true;
  List<CandleItem> _candles = [];
  bool _candlesLoading = false;
  String? _candlesError;

  bool _isFavorite = false;
  String? _favoriteId;

  String get _providerSymbol => tickerToProviderSymbol(widget.asset.ticker);
  String get _favoriteEntityId => '${widget.asset.ticker.toUpperCase()}USDT';

  Future<void> _loadFavoriteStatus() async {
    try {
      final favs = await _favoritesApi.fetchFavorites(entityType: 'instrument');
      if (!mounted) return;
      final match = favs.where((f) => f.entityId == _favoriteEntityId).toList();
      setState(() {
        _isFavorite = match.isNotEmpty;
        _favoriteId = match.isNotEmpty ? match.first.id : null;
      });
    } catch (_) {}
  }

  Future<void> _toggleFavorite() async {
    if (_isFavorite && _favoriteId != null) {
      final ok = await _favoritesApi.removeFavorite(_favoriteId!);
      if (ok && mounted) {
        setState(() {
          _isFavorite = false;
          _favoriteId = null;
        });
      }
    } else {
      final result = await _favoritesApi.addFavorite(
        entityType: 'instrument',
        entityId: _favoriteEntityId,
      );
      if (result.isSuccess && result.favorite != null && mounted) {
        setState(() {
          _isFavorite = true;
          _favoriteId = result.favorite!.id;
        });
      } else if (!result.isSuccess && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result.messageForUser()),
            duration: const Duration(seconds: 3),
          ),
        );
      }
    }
  }

  void _openBuyFlow() async {
    final didBuy = await BuyFlowController.start(
      context,
      assetSymbol: widget.asset.ticker,
      assetName: widget.asset.name,
    );
    if (didBuy == true && mounted) {
      _loadInitial();
    }
  }

  /// Prix affiché en **USD** (cours USDT), sans conversion EUR.
  String get _displayPriceUsd {
    final v = _livePriceUsd ?? _summary?.price;
    if (v != null) return CurrencyFormatter.priceUsd(v);
    return '—';
  }

  /// Performance sur la période du graphique : premier close → prix courant USDT
  /// (même logique que [ChartAssetModule] hors mode instrument).
  ({double absUsd, double pct})? get _periodPerformanceUsd {
    if (_candles.isEmpty) return null;
    final entry = _candles.first.close;
    if (entry <= 0) return null;
    final current = _livePriceUsd ?? _summary?.price;
    if (current == null) return null;
    final absUsd = current - entry;
    final pct = absUsd / entry * 100;
    return (absUsd: absUsd, pct: pct);
  }

  static const List<String> _periodLabels = [
    '1 jour',
    '1 semaine',
    '1 mois',
    '1 an',
    '5 ans',
  ];

  /// Libellé aligné sur les chandelles réellement affichées (évite libellé ≠ valeurs pendant le chargement).
  String get _periodLabelForDisplayedData {
    var i = _displayTimeframeIndex;
    if (i < 0) i = 0;
    if (i >= _periodLabels.length) i = _periodLabels.length - 1;
    return _periodLabels[i];
  }

  @override
  void initState() {
    super.initState();
    _loadInitial();
    _subscribeWs();
    _loadFavoriteStatus();
  }

  @override
  void dispose() {
    _wsService.disconnect();
    super.dispose();
  }

  Future<void> _loadInitial() async {
    setState(() {
      _loadingSummary = true;
      _summaryError = null;
      _summary = null;
    });
    try {
      final list = await _marketDataApi.getMarketSummary(symbols: [_providerSymbol]);
      if (!mounted) return;
      setState(() {
        _loadingSummary = false;
        _summary = list.isNotEmpty ? list.first : null;
        _livePriceUsd ??= _summary?.price;
      });
      _loadCandlesForCurrentTimeframe();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loadingSummary = false;
        _summaryError = _userFriendlyErrorMessage(e);
      });
    }
  }

  /// Pull-to-refresh : met à jour marché + chandelles **sans** écran de chargement ni remise à zéro de [_summary],
  /// pour ne pas démonter [LayoutPageInstrumentDetail] (hauteur hero mesurée stable, même espacement qu’à l’ouverture).
  Future<void> _refreshWhileKeepingLayout() async {
    try {
      final list = await _marketDataApi.getMarketSummary(symbols: [_providerSymbol]);
      if (!mounted) return;
      setState(() {
        _summaryError = null;
        _summary = list.isNotEmpty ? list.first : null;
        _livePriceUsd ??= _summary?.price;
      });
      await _loadCandlesForCurrentTimeframe();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_userFriendlyErrorMessage(e))),
      );
    }
  }

  static const List<String> _chartPeriods = ['1j', '1s', '1m', '1a', '5a'];

  Future<void> _loadCandlesForCurrentTimeframe() async {
    final requestedIndex = _chartTimeframeIndex;
    final period = requestedIndex >= 0 && requestedIndex < _chartPeriods.length
        ? _chartPeriods[requestedIndex]
        : '1j';
    setState(() {
      _candlesLoading = true;
      _candlesError = null;
      // Ne pas vider [_candles] : les puces perf et la courbe gardent les valeurs
      // jusqu’à réception des nouvelles bougies (pas de flash layout).
    });
    try {
      final list = await _marketDataApi.getChartHistory(
        symbol: _providerSymbol,
        period: period,
      );
      if (!mounted) return;
      if (requestedIndex != _chartTimeframeIndex) return;
      setState(() {
        _candlesLoading = false;
        _candles = list;
        _displayTimeframeIndex = _chartTimeframeIndex;
      });
    } catch (e) {
      if (!mounted) return;
      if (requestedIndex != _chartTimeframeIndex) return;
      setState(() {
        _candlesLoading = false;
        _candlesError = _userFriendlyErrorMessage(e);
      });
    }
  }

  /// Même résolution que [TopCryptoAssetsModule] : API marché, asset, puis `/media/crypto_logos/{slug}.png`.
  String? _resolveInstrumentLogoUrl() {
    final fromApi = _summary?.logoUrl ?? widget.asset.logoUrl;
    final resolved = Config.resolveLogoUrl(fromApi);
    if (resolved != null && resolved.isNotEmpty) return resolved;
    final slug = widget.asset.ticker.trim().toLowerCase();
    if (slug.isEmpty) return null;
    return Config.resolveLogoUrl('/media/crypto_logos/$slug.png');
  }

  static String _userFriendlyErrorMessage(Object e) {
    if (e is MarketDataApiException) {
      if (e.statusCode == 401) {
        return 'Données du graphique indisponibles. Connexion requise.';
      }
      if (e.statusCode >= 500) {
        return 'Service temporairement indisponible. Réessayez plus tard.';
      }
      if (e.statusCode >= 400) {
        return 'Impossible de charger les données. Réessayez.';
      }
    }
    return 'Une erreur est survenue. Réessayez.';
  }

  void _subscribeWs() {
    _wsService.subscribe([_providerSymbol], _onWsQuotes);
  }

  void _onWsQuotes(List<QuoteUpdate> updates) {
    if (updates.isEmpty || !mounted) return;
    for (final u in updates) {
      if (u.symbol == _providerSymbol) {
        setState(() => _livePriceUsd = u.price);
        break;
      }
    }
  }

  // ─────────────── Ligne variation (header clair) ───────────────

  Widget? _buildInstrumentPerformanceRowLight() {
    final period = _periodPerformanceUsd;
    if (period == null) return null;

    final changeAbs = period.absUsd;
    final changePct = period.pct;
    final isPositive = changeAbs >= 0;
    final sign = isPositive ? '+' : '-';
    final perfColor =
        isPositive ? AppColors.semanticPositive : AppColors.semanticNegative;
    final absChipColor = instrumentHeroAbsChipColor(
      changeAbs: changeAbs,
      changePct: changePct,
      perfColor: perfColor,
    );
    final absChipText =
        '$sign${CurrencyFormatter.priceUsdRaw(changeAbs.abs())} \$';

    return InstrumentDetailHeroPerformanceRow(
      absChipText: absChipText,
      percentChipText: '$sign${changePct.abs().toStringAsFixed(2)} %',
      periodLabel: _periodLabelForDisplayedData,
      absChipColor: absChipColor,
      percentColor: perfColor,
      percentIsPositive: isPositive,
    );
  }

  // ─────────────── Build ───────────────

  @override
  Widget build(BuildContext context) {
    final asset = widget.asset;

    if (_loadingSummary && _summary == null) return _buildInitialLoading();
    if (_summaryError != null && _summary == null) return _buildInitialError();

    final navActions = <AppTopNavBarAction>[
      AppTopNavBarAction(
        icon: Icons.swap_vert_rounded,
        onPressed: () {
          Navigator.of(context).push(
            MaterialPageRoute<void>(
              builder: (_) => OrdersListScreen(
                asset: asset.ticker,
                currentPrice: _livePriceUsd ?? _summary?.price,
              ),
            ),
          );
        },
      ),
      AppTopNavBarAction(
        icon: Icons.add_alert_rounded,
        onPressed: () {
          Navigator.of(context).push(
            MaterialPageRoute<void>(
              builder: (_) => AlertsListScreen(
                asset: asset.ticker,
                currentPrice: _livePriceUsd ?? _summary?.price,
              ),
            ),
          );
        },
      ),
      AppTopNavBarAction(
        icon: _isFavorite ? Icons.star_rounded : Icons.star_outline,
        iconColor: _isFavorite ? const Color(0xFFFFB800) : null,
        onPressed: _toggleFavorite,
      ),
    ];

    final chartModule = ChartAssetModule(
      asset: asset,
      displayPrice: _displayPriceUsd,
      instrumentDetailStyle: true,
      currentPrice: _livePriceUsd ?? _summary?.price,
      change24hPct: _summary?.change24hPct,
      change24hAbs: _summary?.change24hAbs,
      periodLabel: _periodLabelForDisplayedData,
      candles: _candles.isEmpty ? null : _candles,
      chartLoading: _candlesLoading && _candles.isEmpty,
      chartError: _candlesError,
      selectedTimeframeIndex: _chartTimeframeIndex,
      onTimeframeChanged: (index) {
        if (index != _chartTimeframeIndex &&
            index >= 0 &&
            index < _chartPeriods.length) {
          setState(() => _chartTimeframeIndex = index);
          _loadCandlesForCurrentTimeframe();
        }
      },
      onRefresh: _loadCandlesForCurrentTimeframe,
      isLineChart: _isLineChart,
      onChartTypeChanged: (isLine) {
        setState(() => _isLineChart = isLine);
      },
    );

    return LayoutPageInstrumentDetail(
      categoryBadges: const [
        ArticleCategoryBadgeData(
          label: 'Crypto',
          dotColor: AppColors.accent,
        ),
      ],
      titleLeading: CryptoAvatar(
        ticker: asset.ticker,
        logoUrl: _resolveInstrumentLogoUrl(),
        size: CryptoAvatarSize.small,
        fallbackIcon: asset.icon,
      ),
      title: asset.name,
      subtitle: _displayPriceUsd,
      subtitleStyle: AppTypography.amountPrimary.copyWith(
        color: AppColors.textPrimary,
      ),
      heroActions: _buildInstrumentPerformanceRowLight(),
      heroFullBleed: chartModule,
      heroActionsBelowFullBleed: InstrumentDetailHeroCtaRow(
        children: [
          AppPrimaryButton(
            label: 'Acheter',
            size: AppPrimaryButtonSize.medium,
            variant: AppPrimaryButtonVariant.primary,
            horizontalPadding: AppSpacing.s4,
            leading: const Icon(Icons.arrow_upward, size: 20),
            onPressed: _openBuyFlow,
          ),
          AppPrimaryButton(
            label: 'Vendre',
            size: AppPrimaryButtonSize.medium,
            variant: AppPrimaryButtonVariant.secondary,
            horizontalPadding: AppSpacing.s4,
            leading: const Icon(Icons.arrow_downward, size: 20),
            onPressed: () {},
          ),
        ],
      ),
      navBarActions: navActions,
      onLeadingTap: () => Navigator.of(context).pop(),
      content: [
        VaultsMarketingCardsFeed(
          widgetSlug: 'blog-a-la-une',
          title: 'À la une',
          assetSlug: asset.ticker.trim().toLowerCase(),
          useBlogNewsLayout: true,
        ),
        VaultsMarketingCardsFeed(
          widgetSlug: 'research-a-la-une',
          title: 'Recherche à la une',
          assetSlug: asset.ticker.trim().toLowerCase(),
        ),
      ],
      onRefresh: _refreshWhileKeepingLayout,
    );
  }

  Widget _buildInitialLoading() {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const SizedBox(
              width: 36,
              height: 36,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: AppColors.accent,
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(
              'Chargement…',
              style: AppTypography.bodyMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInitialError() {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.xl),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.error_outline_rounded,
                size: 48,
                color: AppColors.textSecondary.withValues(alpha: 0.8),
              ),
              const SizedBox(height: AppSpacing.lg),
              Text(
                _summaryError ?? 'Erreur de chargement',
                textAlign: TextAlign.center,
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.textSecondary,
                ),
                maxLines: 5,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: AppSpacing.xl),
              TextButton.icon(
                onPressed: _loadInitial,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Réessayer'),
                style: TextButton.styleFrom(
                  foregroundColor: AppColors.accent,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
