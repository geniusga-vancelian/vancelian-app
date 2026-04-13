import 'package:flutter/material.dart';

import '../../../../../core/config.dart';
import '../../../../../core/currency_preference.dart';
import '../../../../../design_system/design_system.dart';
import '../../../../markets/data/all_crypto_api.dart';
import '../../../../markets/data/market_data_ws_service.dart';
import '../../../../markets/data/market_display_utils.dart';
import 'buy_flow_source_selection_screen.dart';

/// STEP 0 — Asset target selection.
///
/// Displayed when the user enters the BUY flow without a pre-selected asset
/// (e.g. from the "Échanger" button on All Crypto).
///
/// Reproduces the All Crypto page content: search bar + full list of cryptos.
/// Navbar title "Investir" appears on scroll (same behavior as Markets / All Crypto).
class BuyFlowAssetSelectionScreen extends StatefulWidget {
  const BuyFlowAssetSelectionScreen({super.key});

  @override
  State<BuyFlowAssetSelectionScreen> createState() =>
      _BuyFlowAssetSelectionScreenState();
}

class _BuyFlowAssetSelectionScreenState
    extends State<BuyFlowAssetSelectionScreen> {
  final AllCryptoApi _api = AllCryptoApi();
  final MarketDataWsService _wsService = MarketDataWsService();
  final ScrollController _scrollController = ScrollController();
  final TextEditingController _searchController = TextEditingController();

  List<AllCryptoItem> _items = const [];
  bool _loading = true;
  String? _error;
  String _query = '';
  double _navTitleOpacity = 0;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    _searchController.addListener(() {
      setState(() => _query = _searchController.text.trim().toLowerCase());
    });
    _load();
  }

  @override
  void dispose() {
    _wsService.disconnect();
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  void _onScroll() {
    final offset = _scrollController.hasClients ? _scrollController.offset : 0.0;
    final next = ((offset - 24) / 40).clamp(0.0, 1.0);
    if ((next - _navTitleOpacity).abs() > 0.02) {
      setState(() => _navTitleOpacity = next);
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = await _api.getAllCryptos();
      if (!mounted) return;
      setState(() {
        _items = items;
        _loading = false;
      });
      _subscribeWs();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e.toString();
      });
    }
  }

  void _subscribeWs() {
    if (!mounted || _items.isEmpty) return;
    final symbols = _items
        .map((it) => it.providerSymbol)
        .where((s) => s != null && s.isNotEmpty)
        .cast<String>()
        .toList();
    if (symbols.isEmpty) return;
    _wsService.subscribe(symbols, _onWsQuotes);
  }

  void _onWsQuotes(List<QuoteUpdate> updates) {
    if (updates.isEmpty || !mounted) return;
    final bySymbol = {for (final u in updates) u.symbol: u};
    final pref = CurrencyPreference.instance;
    bool changed = false;
    final next = _items.map((it) {
      final sym = it.providerSymbol?.trim().toUpperCase();
      if (sym == null || sym.isEmpty) return it;
      final quote = bySymbol[sym];
      if (quote == null) return it;
      final displayPrice = pref.selectValue(eur: quote.priceEur, usd: quote.price);
      if (displayPrice == null) return it;
      changed = true;
      return it.copyWith(price: AllCryptoApi.formatPrice(displayPrice));
    }).toList(growable: false);
    if (changed && mounted) setState(() => _items = next);
  }

  List<AllCryptoItem> get _filteredItems {
    if (_query.isEmpty) return _items;
    return _items
        .where(
          (it) =>
              it.name.toLowerCase().contains(_query) ||
              it.ticker.toLowerCase().contains(_query),
        )
        .toList(growable: false);
  }

  void _selectAsset(AllCryptoItem item) {
    final ticker = (item.providerSymbol != null && item.providerSymbol!.trim().isNotEmpty)
        ? marketShortSymbol(item.providerSymbol!)
        : item.ticker;
    if (ticker.isEmpty || ticker == '—') return;

    Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => BuyFlowSourceSelectionScreen(
          assetSymbol: ticker,
          assetName: item.name,
          assetLogoUrl: Config.resolveLogoUrl(item.logoUrl) ??
              Config.resolveLogoUrl('/media/crypto_logos/${ticker.toLowerCase()}.png'),
        ),
      ),
    ).then((didBuy) {
      if (didBuy == true && mounted) {
        Navigator.of(context).pop(true);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _filteredItems;
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppTopNavBar(
        leadingType: AppTopNavBarLeading.back,
        title: 'Investir',
        onBackTap: () => Navigator.of(context).pop(false),
        centerTitle: false,
        titleOpacity: _navTitleOpacity,
        titleTextStyle: AppTypography.paragraph.copyWith(
          color: AppColors.textPrimary,
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
        actions: const [],
      ),
      body: SafeArea(
        bottom: false,
        child: RefreshIndicator(
          onRefresh: _load,
          child: CustomScrollView(
            controller: _scrollController,
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              const SliverToBoxAdapter(child: SizedBox(height: AppSpacing.md)),
              const SliverToBoxAdapter(
                child: Padding(
                  padding: EdgeInsets.symmetric(horizontal: AppSpacing.xl),
                  child: AppPageTitle('Investir'),
                ),
              ),
              const SliverToBoxAdapter(child: SizedBox(height: 8)),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
                  child: Text(
                    'Que souhaitez-vous acheter ?',
                    style: AppTypography.titleLarge.copyWith(
                      color: AppColors.textPrimary,
                      fontWeight: FontWeight.w700,
                      height: 1.35,
                    ),
                  ),
                ),
              ),
              const SliverToBoxAdapter(child: SizedBox(height: AppSpacing.xl)),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
                  child: _InvestSearchBar(controller: _searchController),
                ),
              ),
              const SliverToBoxAdapter(child: SizedBox(height: AppSpacing.lg)),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
                  child: AppSectionTitle('Cryptos · ${filtered.length}'),
                ),
              ),
              const SliverToBoxAdapter(child: SizedBox(height: AppSpacing.lg)),
              if (_loading)
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
                    child: _InvestLoadingCard(),
                  ),
                )
              else if (_error != null)
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: Center(
                    child: Padding(
                      padding: const EdgeInsets.all(AppSpacing.xl),
                      child: Text(
                        _error!,
                        style: AppTypography.bodyMedium.copyWith(
                          color: AppColors.textSecondary,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ),
                )
              else
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
                    child: _buildCryptoListCard(filtered),
                  ),
                ),
              SliverToBoxAdapter(
                child: SizedBox(
                  height: MediaQuery.paddingOf(context).bottom + AppSpacing.md,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCryptoListCard(List<AllCryptoItem> items) {
    return TransactionListCard(
      itemSpacing: 4,
      items: [
        for (final item in items)
          _buildCryptoItem(item),
      ],
    );
  }

  TransactionListItemData _buildCryptoItem(AllCryptoItem item) {
    final isPositive = item.variationPercent >= 0;
    final variationColor = isPositive
        ? const Color(0xFF059669)
        : const Color(0xFFDC2626);
    final arrow = isPositive ? '▲' : '▼';
    final variationText =
        '$arrow ${isPositive ? '+' : ''}${item.variationPercent.toStringAsFixed(2)} %';

    final resolvedLogoUrl = _resolveAssetLogoUrl(item.ticker, item.logoUrl);

    return TransactionListItemData(
      leadingWidget: CryptoAvatar(
        ticker: item.ticker,
        logoUrl: resolvedLogoUrl,
        size: CryptoAvatarSize.large,
      ),
      title: item.name,
      subtitle: item.ticker,
      amount: item.price,
      secondaryAmount: variationText,
      secondaryAmountColor: variationColor,
      onTap: () => _selectAsset(item),
    );
  }

  static String? _resolveAssetLogoUrl(String ticker, String? apiLogoUrl) {
    final resolved = Config.resolveLogoUrl(apiLogoUrl);
    if (resolved != null && resolved.isNotEmpty) return resolved;
    final t = ticker.trim().toLowerCase();
    if (t.isEmpty) return null;
    final base = t.endsWith('usdt') ? t.substring(0, t.length - 4) : t;
    if (base.isEmpty) return null;
    return Config.resolveLogoUrl('/media/crypto_logos/$base.png');
  }
}

class _InvestSearchBar extends StatelessWidget {
  const _InvestSearchBar({required this.controller});

  final TextEditingController controller;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(999),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.08),
            blurRadius: 14,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(999),
        child: TextField(
          controller: controller,
          style: AppTypography.bodyMedium.copyWith(color: AppColors.textPrimary),
          decoration: InputDecoration(
            prefixIcon: const Icon(Icons.search_rounded),
            prefixIconColor: AppColors.textSecondary,
            hintText: 'Rechercher',
            hintStyle: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary),
            filled: false,
            fillColor: Colors.transparent,
            border: InputBorder.none,
            contentPadding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
          ),
        ),
      ),
    );
  }
}

class _InvestLoadingCard extends StatefulWidget {
  @override
  State<_InvestLoadingCard> createState() => _InvestLoadingCardState();
}

class _InvestLoadingCardState extends State<_InvestLoadingCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    )..repeat(reverse: true);
    _animation = Tween<double>(begin: 0.35, end: 0.65).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        return Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(16),
            boxShadow: AppShadow.defaultShadowList,
          ),
          child: Column(
            children: List.generate(8, (_) => _buildSkeletonRow()),
          ),
        );
      },
    );
  }

  Widget _buildSkeletonRow() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.textSecondary.withValues(alpha: _animation.value),
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  height: 14,
                  width: 120,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(4),
                    color: AppColors.textSecondary.withValues(alpha: _animation.value),
                  ),
                ),
                const SizedBox(height: 6),
                Container(
                  height: 12,
                  width: 60,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(4),
                    color: AppColors.textSecondary.withValues(alpha: _animation.value * 0.8),
                  ),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Container(
                height: 14,
                width: 70,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(4),
                  color: AppColors.textSecondary.withValues(alpha: _animation.value),
                ),
              ),
              const SizedBox(height: 6),
              Container(
                height: 12,
                width: 50,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(4),
                  color: AppColors.textSecondary.withValues(alpha: _animation.value * 0.8),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
