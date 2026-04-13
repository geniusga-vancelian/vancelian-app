import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../core/currency_preference.dart';
import '../../../../core/profile_leading_preference.dart';
import '../../../../design_system/design_system.dart';
import '../../../favorites/data/favorites_api.dart';
import '../../../favorites/domain/models/favorite.dart';
import '../../../news/data/blog_api.dart';
import '../../../news/domain/models/article.dart';
import '../../../news/presentation/screens/article_detail_screen.dart';
import '../../../offers/presentation/widgets/vaults_marketing_cards_feed.dart';
import '../widgets/crypto_bundles_widget.dart';
import '../../../profile/presentation/screens/profile_screen.dart';
import '../../../../ui/navigation/bottom_nav_content_inset.dart';
import '../../data/market_data_api.dart';
import '../../data/market_data_ws_service.dart';
import '../../data/market_display_utils.dart';
import '../screens/all_crypto_screen.dart';
import '../screens/crypto_detail_screen.dart';
import '../widgets/top_crypto_assets_module.dart';

/// Page "Crypto Markets" : titre, section Top Crypto (REST), Crypto Bundles, Research, Latest News.
/// Top Crypto : onglets Populaires / Top Gainers / Top Losers branchés sur market-summary et top-movers.
class MarketsScreen extends StatefulWidget {
  const MarketsScreen({super.key});

  @override
  State<MarketsScreen> createState() => _MarketsScreenState();
}

class _MarketsScreenState extends State<MarketsScreen> {
  static const int _latestNewsMaxItems = 5;
  final ScrollController _scrollController = ScrollController();
  final BlogApi _blogApi = BlogApi();
  final MarketDataApi _marketDataApi = MarketDataApi();
  final FavoritesApi _favoritesApi = FavoritesApi();
  int _widgetsRefreshNonce = 0;
  double _navTitleOpacity = 0;
  List<ArticlePreview> _latestNewsArticles = [];
  List<BlogCategory> _latestNewsCategories = [];
  bool _loadingLatestNews = true;

  // Top Crypto (market-summary + top-movers)
  bool _loadingTopCrypto = true;
  String? _errorTopCrypto;
  List<MarketSummaryItem> _popularSummaries = [];
  List<MarketSummaryItem> _topGainers = [];
  List<MarketSummaryItem> _topLosers = [];

  // Favorites
  List<Favorite> _favorites = [];
  Set<String> _favoriteSymbols = {};
  Map<String, String> _favoriteIdBySymbol = {};
  List<MarketSummaryItem> _favoriteSummaries = [];

  // Live updates: onglet actif pour souscription WS
  TopCryptoTab _selectedTopCryptoTab = TopCryptoTab.populaires;
  final MarketDataWsService _wsService = MarketDataWsService();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    _loadLatestNews(maxItems: _latestNewsMaxItems);
    _loadTopCrypto();
    _loadFavorites();
  }

  @override
  void dispose() {
    _wsService.disconnect();
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    final offset = _scrollController.hasClients ? _scrollController.offset : 0.0;
    final next = ((offset - 24) / 40).clamp(0.0, 1.0);
    if ((next - _navTitleOpacity).abs() > 0.02) {
      setState(() => _navTitleOpacity = next);
    }
  }

  Future<void> _onRefresh() async {
    setState(() => _widgetsRefreshNonce++);
    await Future.wait([
      _loadLatestNews(maxItems: _latestNewsMaxItems),
      _loadTopCrypto(),
      _loadFavorites(),
      Future<void>.delayed(const Duration(milliseconds: 300)),
    ]);
  }

  Future<void> _loadTopCrypto() async {
    setState(() {
      _loadingTopCrypto = true;
      _errorTopCrypto = null;
    });
    try {
      final popularFuture = _marketDataApi.getMarketSummary(
        symbols: defaultPopularSymbols,
      );
      final moversFuture = _marketDataApi.getTopMovers(limit: 10);
      final results = await Future.wait([popularFuture, moversFuture]);
      if (!mounted) return;
      setState(() {
        _popularSummaries = results[0] as List<MarketSummaryItem>;
        final movers = results[1] as TopMoversResponse;
        _topGainers = movers.topGainers;
        _topLosers = movers.topLosers;
        _loadingTopCrypto = false;
        _errorTopCrypto = null;
      });
      WidgetsBinding.instance.addPostFrameCallback((_) => _subscribeWsForCurrentTab());
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _popularSummaries = [];
        _topGainers = [];
        _topLosers = [];
        _loadingTopCrypto = false;
        _errorTopCrypto = _userFriendlyError(e);
      });
    }
  }

  Future<void> _loadFavorites() async {
    try {
      final favs = await _favoritesApi.fetchFavorites(entityType: 'instrument');
      if (!mounted) return;
      final symbols = <String>{};
      final idMap = <String, String>{};
      for (final fav in favs) {
        final ticker = _entityIdToTicker(fav.entityId);
        symbols.add(ticker);
        idMap[ticker] = fav.id;
      }
      setState(() {
        _favorites = favs;
        _favoriteSymbols = symbols;
        _favoriteIdBySymbol = idMap;
      });
      await _loadFavoriteMarketData();
    } catch (e) {
      debugPrint('[MarketsScreen] _loadFavorites error: $e');
    }
  }

  Future<void> _loadFavoriteMarketData() async {
    if (_favoriteSymbols.isEmpty) {
      if (mounted) setState(() => _favoriteSummaries = []);
      return;
    }
    try {
      final apiSymbols = _favoriteSymbols
          .map((t) => '${t.toUpperCase()}USDT')
          .toList(growable: false);
      final summaries = await _marketDataApi.getMarketSummary(symbols: apiSymbols);
      if (!mounted) return;
      setState(() => _favoriteSummaries = summaries);
    } catch (e) {
      debugPrint('[MarketsScreen] _loadFavoriteMarketData error: $e');
      if (mounted) setState(() => _favoriteSummaries = []);
    }
  }

  static String _entityIdToTicker(String entityId) {
    final upper = entityId.toUpperCase();
    if (upper.endsWith('USDT')) return upper.substring(0, upper.length - 4);
    return upper;
  }

  /// Message d'erreur lisible ; en debug on garde la cause technique pour le sous-titre.
  static String _userFriendlyError(Object e) {
    final s = e.toString().toLowerCase();
    if (s.contains('connection refused') || s.contains('connection reset') || s.contains('failed host lookup')) {
      return 'Impossible de joindre l\'API. Vérifiez que le serveur tourne sur le port 8000.';
    }
    if (s.contains('timeout') || s.contains('timed out')) {
      return 'Délai dépassé. Vérifiez votre connexion.';
    }
    if (e is MarketDataApiException) {
      if (e.statusCode == 401) return 'Authentification requise.';
      if (e.statusCode >= 500) return 'Service temporairement indisponible.';
      if (e.statusCode >= 400) return 'Erreur serveur. Réessayez.';
    }
    return 'Données indisponibles. Réessayez.';
  }

  static CryptoAssetItem _summaryToAsset(MarketSummaryItem s) {
    final pref = CurrencyPreference.instance;
    final displayPrice = pref.selectValue(eur: s.priceEur, usd: s.price) ?? s.price;
    final sym = pref.currency.symbol;
    return CryptoAssetItem(
      name: marketDisplayName(s.symbol),
      ticker: marketShortSymbol(s.symbol),
      price: '${formatPrice(displayPrice)} $sym',
      variationPercent: s.change24hPct ?? 0.0,
      redirectUrl: 'crypto://${marketShortSymbol(s.symbol).toLowerCase()}',
      logoUrl: s.logoUrl,
    );
  }

  List<CryptoAssetItem> get _popularAssets =>
      _popularSummaries.map(_summaryToAsset).toList(growable: false);
  List<CryptoAssetItem> get _gainerAssets =>
      _topGainers.map(_summaryToAsset).toList(growable: false);
  List<CryptoAssetItem> get _loserAssets =>
      _topLosers.map(_summaryToAsset).toList(growable: false);
  /// Préfère les cours marché ; si l’API marché échoue mais des favoris existent en base,
  /// on affiche quand même les lignes (prix « — ») pour éviter un onglet vide + erreur « max 10 ».
  List<CryptoAssetItem> get _favoriteAssets {
    if (_favoriteSummaries.isNotEmpty) {
      return _favoriteSummaries.map(_summaryToAsset).toList(growable: false);
    }
    if (_favorites.isEmpty) return [];
    final pref = CurrencyPreference.instance;
    final sym = pref.currency.symbol;
    return _favorites.map((f) {
      final ticker = _entityIdToTicker(f.entityId);
      final pair = '${ticker.toUpperCase()}USDT';
      return CryptoAssetItem(
        name: marketDisplayName(pair),
        ticker: marketShortSymbol(pair),
        price: '— $sym',
        variationPercent: 0,
        redirectUrl: 'crypto://${ticker.toLowerCase()}',
        logoUrl: null,
      );
    }).toList(growable: false);
  }

  List<String> _symbolsForTab(TopCryptoTab tab) {
    switch (tab) {
      case TopCryptoTab.favoris:
        if (_favoriteSummaries.isNotEmpty) {
          return _favoriteSummaries.map((s) => s.symbol).toList();
        }
        return _favoriteSymbols.map((t) => '${t.toUpperCase()}USDT').toList();
      case TopCryptoTab.populaires:
        return _popularSummaries.map((s) => s.symbol).toList();
      case TopCryptoTab.enHausse:
        return _topGainers.map((s) => s.symbol).toList();
      case TopCryptoTab.enBaisse:
        return _topLosers.map((s) => s.symbol).toList();
    }
  }

  void _subscribeWsForCurrentTab() {
    if (!mounted) return;
    final symbols = _symbolsForTab(_selectedTopCryptoTab);
    if (symbols.isEmpty) return;
    _wsService.subscribe(symbols, _onWsQuotes);
  }

  void _onWsQuotes(List<QuoteUpdate> updates) {
    if (updates.isEmpty || !mounted) return;
    final tab = _selectedTopCryptoTab;
    late List<MarketSummaryItem> list;
    switch (tab) {
      case TopCryptoTab.favoris:
        list = List.from(_favoriteSummaries);
        break;
      case TopCryptoTab.populaires:
        list = List.from(_popularSummaries);
        break;
      case TopCryptoTab.enHausse:
        list = List.from(_topGainers);
        break;
      case TopCryptoTab.enBaisse:
        list = List.from(_topLosers);
        break;
    }
    var changed = false;
    for (final u in updates) {
      final i = list.indexWhere((s) => s.symbol == u.symbol);
      if (i >= 0) {
        final old = list[i];
        list[i] = MarketSummaryItem(
          instrumentId: old.instrumentId,
          symbol: old.symbol,
          price: u.price,
          priceEur: u.priceEur ?? old.priceEur,
          change24hAbs: old.change24hAbs,
          change24hPct: old.change24hPct,
          volume24h: old.volume24h,
          sparkline24h: old.sparkline24h,
          logoUrl: old.logoUrl,
        );
        changed = true;
      }
    }
    if (!changed || !mounted) return;
    final newFavorites = tab == TopCryptoTab.favoris ? list : null;
    final newPopular = tab == TopCryptoTab.populaires ? list : null;
    final newGainers = tab == TopCryptoTab.enHausse ? list : null;
    final newLosers = tab == TopCryptoTab.enBaisse ? list : null;
    if (kDebugMode) {
      final sample = updates.take(3).map((u) => '${u.symbol}=${u.price}').join(', ') + (updates.length > 3 ? '...' : '');
      print('[MarketsScreen] UI update with ${updates.length} quote(s) → $sample');
    }
    setState(() {
      if (newFavorites != null) _favoriteSummaries = newFavorites;
      if (newPopular != null) _popularSummaries = newPopular;
      if (newGainers != null) _topGainers = newGainers;
      if (newLosers != null) _topLosers = newLosers;
    });
  }

  void _onTopCryptoTabChanged(TopCryptoTab tab) {
    setState(() => _selectedTopCryptoTab = tab);
    WidgetsBinding.instance.addPostFrameCallback((_) => _subscribeWsForCurrentTab());
  }

  void _onSeeMoreTopCrypto() {
    Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => const AllCryptoScreen()),
    );
  }

  void _onAssetTap(CryptoAssetItem asset) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => CryptoDetailScreen(asset: asset),
      ),
    ).then((_) {
      if (mounted) _loadFavorites();
    });
  }

  Future<void> _loadLatestNews({int maxItems = 10}) async {
    final effectiveMax = maxItems.clamp(1, 10);
    setState(() => _loadingLatestNews = true);
    try {
      final data = await _blogApi.getFeed(
        locale: 'fr',
        articleType: 'NEWS',
        page: 1,
        pageSize: effectiveMax,
      );
      final ordered = <ArticlePreview>[
        if (data.featured != null) data.featured!,
        ...data.highlighted,
        ...data.articles,
      ].where((a) => a.articleType.toUpperCase() == 'NEWS').toList(growable: false);
      final byId = <String, ArticlePreview>{};
      for (final article in ordered) {
        byId.putIfAbsent(article.id, () => article);
      }
      setState(() {
        _latestNewsArticles = byId.values.take(effectiveMax).toList(growable: false);
        _latestNewsCategories = data.categories;
        _loadingLatestNews = false;
      });
    } catch (_) {
      setState(() {
        _latestNewsArticles = [];
        _latestNewsCategories = [];
        _loadingLatestNews = false;
      });
    }
  }

  String _formatNewsDate(DateTime? value) {
    if (value == null) return '';
    final formatted = DateFormat('d MMMM', 'fr_FR').format(value);
    if (formatted.isEmpty) return '';
    return '${formatted[0].toUpperCase()}${formatted.substring(1)}';
  }

  List<String> _newsTagsForArticle(ArticlePreview article) {
    final slugs = article.categorySlugs;
    if (slugs == null || slugs.isEmpty) return const [];
    final labels = slugs
        .map((slug) {
          for (final category in _latestNewsCategories) {
            if (category.slug == slug) return category.label.trim();
          }
          return slug.trim();
        })
        .where((label) => label.isNotEmpty)
        .toSet()
        .toList(growable: false);
    return labels;
  }

  void _openArticle(ArticlePreview article) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => ArticleDetailScreen(slug: article.slug),
      ),
    );
  }

  Widget _buildTopCryptoSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (_loadingTopCrypto && _popularSummaries.isEmpty && _topGainers.isEmpty && _topLosers.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
            child: _TopCryptoLoadingCard(),
          )
        else if (_errorTopCrypto != null && _popularSummaries.isEmpty && _topGainers.isEmpty && _topLosers.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
            child: _TopCryptoErrorCard(
              message: _errorTopCrypto!,
              onRetry: _loadTopCrypto,
            ),
          )
        else
          TopCryptoAssetsModule(
            popularLabel: 'Populaires',
            gainersLabel: 'Top Gainers',
            losersLabel: 'Top Losers',
            favoritesLabel: 'Favoris',
            seeMoreLabel: 'See more',
            onSeeMoreTap: _onSeeMoreTopCrypto,
            onTabChanged: _onTopCryptoTabChanged,
            onAssetTap: _onAssetTap,
            popularAssets: _popularAssets,
            gainerAssets: _gainerAssets,
            loserAssets: _loserAssets,
            favoriteAssets: _favoriteAssets,
          ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: ProfileLeadingPreference.instance,
      builder: (context, _) {
        return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppTopNavBar(
        leadingType: AppTopNavBarLeading.profile,
        profileInitials: ProfileLeadingPreference.instance.initials,
        title: 'Crypto Markets',
        titleOpacity: _navTitleOpacity,
        centerTitle: false,
        titleTextStyle: AppTypography.paragraph.copyWith(
          color: AppColors.textPrimary,
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
        onProfileTap: () {
          Navigator.of(context).push(
            MaterialPageRoute<void>(builder: (_) => const ProfileScreen()),
          );
        },
        actions: const [
          AppTopNavBarAction(icon: Icons.bar_chart_rounded),
          AppTopNavBarAction(icon: Icons.notifications_outlined),
        ],
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _onRefresh,
          child: CustomScrollView(
            controller: _scrollController,
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              const SliverToBoxAdapter(child: SizedBox(height: AppSpacing.md)),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
                  child: AppPageTitle('Crypto Markets'),
                ),
              ),
            const SliverToBoxAdapter(child: SizedBox(height: AppSpacing.xl)),
            SliverToBoxAdapter(
              child: Column(
                children: [
                    _buildTopCryptoSection(),
                    const SizedBox(height: AppSpacing.xxl),
                    CryptoBundlesWidget(
                      title: 'Crypto Bundles',
                      refreshNonce: _widgetsRefreshNonce,
                    ),
                    const SizedBox(height: AppSpacing.xl),
                    if (_loadingLatestNews && _latestNewsArticles.isEmpty)
                      const Padding(
                        padding: EdgeInsets.all(AppSpacing.xxl),
                        child: Center(child: CircularProgressIndicator()),
                      )
                    else if (_latestNewsArticles.isNotEmpty) ...[
                      NewsTransactionsListModule(
                        title: 'Latest News',
                        maxItems: _latestNewsMaxItems,
                        items: _latestNewsArticles
                            .map(
                              (article) => NewsTransactionsListItem(
                                title: article.title,
                                dateLabel: _formatNewsDate(article.publishedAt),
                                authorName: article.authorName,
                                tags: _newsTagsForArticle(article),
                                onTap: () => _openArticle(article),
                              ),
                            )
                            .toList(growable: false),
                      ),
                      const SizedBox(height: AppSpacing.xl),
                    ],
                    const SizedBox(height: AppSpacing.xl),
                    VaultsMarketingCardsFeed(
                      widgetSlug: 'top10research',
                      title: 'Research',
                      refreshNonce: _widgetsRefreshNonce,
                    ),
                  ],
                ),
              ),
              SliverToBoxAdapter(
                child: SizedBox(height: BottomNavContentInset.level1(context)),
              ),
            ],
          ),
        ),
      ),
    );
      },
    );
  }
}

class _TopCryptoLoadingCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(
          color: AppColors.textPrimary.withValues(alpha: 0.06),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.04),
            blurRadius: 12,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.md,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _SkeletonRow(),
          _SkeletonDivider(),
          _SkeletonRow(),
          _SkeletonDivider(),
          _SkeletonRow(),
          _SkeletonDivider(),
          _SkeletonRow(),
          _SkeletonDivider(),
          _SkeletonRow(),
          const SizedBox(height: AppSpacing.md),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: AppColors.textSecondary.withValues(alpha: 0.6),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Text(
                'Chargement…',
                style: AppTypography.meta.copyWith(
                  color: AppColors.textSecondary,
                  fontSize: 13,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SkeletonRow extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.lg),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: AppColors.textSecondary.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(22),
            ),
          ),
          const SizedBox(width: AppSpacing.lg),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  height: 14,
                  width: 100,
                  decoration: BoxDecoration(
                    color: AppColors.textSecondary.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
                const SizedBox(height: 8),
                Container(
                  height: 12,
                  width: 50,
                  decoration: BoxDecoration(
                    color: AppColors.textSecondary.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Container(
                height: 14,
                width: 70,
                decoration: BoxDecoration(
                  color: AppColors.textSecondary.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
              const SizedBox(height: 8),
              Container(
                height: 12,
                width: 55,
                decoration: BoxDecoration(
                  color: AppColors.textSecondary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SkeletonDivider extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Divider(
      height: 1,
      thickness: 1,
      color: AppColors.border.withValues(alpha: 0.4),
      indent: 56,
      endIndent: 0,
    );
  }
}

class _TopCryptoErrorCard extends StatelessWidget {
  const _TopCryptoErrorCard({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(
          color: AppColors.textPrimary.withValues(alpha: 0.06),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.04),
            blurRadius: 12,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.xl,
        vertical: AppSpacing.xxl,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.cloud_off_rounded,
            size: 40,
            color: AppColors.textSecondary.withValues(alpha: 0.6),
          ),
          const SizedBox(height: AppSpacing.lg),
          Text(
            'Données indisponibles',
            style: AppTypography.titleSmall.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w600,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            message,
            style: AppTypography.meta.copyWith(
              color: AppColors.textSecondary,
              fontSize: 14,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppSpacing.lg),
          FilledButton.icon(
            onPressed: onRetry,
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.accent,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.lg,
                vertical: AppSpacing.sm,
              ),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(AppRadius.button),
              ),
            ),
            icon: const Icon(Icons.refresh_rounded, size: 18),
            label: const Text('Réessayer'),
          ),
        ],
      ),
    );
  }
}
