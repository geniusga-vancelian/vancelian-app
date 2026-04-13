import 'package:flutter/material.dart';

import '../../../../core/config.dart';
import '../../../../core/currency_preference.dart';
import '../../../../design_system/design_system.dart';
import '../../data/all_crypto_api.dart';
import '../../data/market_data_ws_service.dart';
import '../../data/market_display_utils.dart';
import 'crypto_detail_screen.dart';
import '../widgets/top_crypto_assets_module.dart';

enum _AllCryptoSortOption {
  performanceDesc,
  performanceAsc,
  marketCapDesc,
  marketCapAsc,
}

class AllCryptoScreen extends StatefulWidget {
  const AllCryptoScreen({super.key});

  @override
  State<AllCryptoScreen> createState() => _AllCryptoScreenState();
}

class _AllCryptoScreenState extends State<AllCryptoScreen> {
  final AllCryptoApi _api = AllCryptoApi();
  final MarketDataWsService _wsService = MarketDataWsService();
  final ScrollController _scrollController = ScrollController();
  final TextEditingController _searchController = TextEditingController();

  List<AllCryptoItem> _items = const [];
  bool _loading = true;
  String? _error;
  String _query = '';
  double _navTitleOpacity = 0;
  _AllCryptoSortOption _sortOption = _AllCryptoSortOption.marketCapDesc;

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
    final searched = _query.isEmpty
        ? _items
        : _items
            .where(
              (it) =>
                  it.name.toLowerCase().contains(_query) ||
                  it.ticker.toLowerCase().contains(_query),
            )
            .toList(growable: false);

    final sorted = [...searched];
    switch (_sortOption) {
      case _AllCryptoSortOption.performanceDesc:
        sorted.sort((a, b) => b.variationPercent.compareTo(a.variationPercent));
        break;
      case _AllCryptoSortOption.performanceAsc:
        sorted.sort((a, b) => a.variationPercent.compareTo(b.variationPercent));
        break;
      case _AllCryptoSortOption.marketCapDesc:
        sorted.sort((a, b) => a.marketCapRank.compareTo(b.marketCapRank));
        break;
      case _AllCryptoSortOption.marketCapAsc:
        sorted.sort((a, b) => b.marketCapRank.compareTo(a.marketCapRank));
        break;
    }
    return sorted;
  }

  String get _sortLabel {
    switch (_sortOption) {
      case _AllCryptoSortOption.performanceDesc:
        return 'Performance';
      case _AllCryptoSortOption.performanceAsc:
        return 'Performance';
      case _AllCryptoSortOption.marketCapDesc:
        return 'Capitalisation';
      case _AllCryptoSortOption.marketCapAsc:
        return 'Capitalisation';
    }
  }

  IconData get _sortDirectionIcon {
    switch (_sortOption) {
      case _AllCryptoSortOption.performanceDesc:
      case _AllCryptoSortOption.marketCapDesc:
        return Icons.arrow_upward_rounded;
      case _AllCryptoSortOption.performanceAsc:
      case _AllCryptoSortOption.marketCapAsc:
        return Icons.arrow_downward_rounded;
    }
  }

  Future<void> _openSortSheet() async {
    final selected = await showModalBottomSheet<_AllCryptoSortOption>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return BottomSheetContainer(
          toolbar: const SheetTitleBar(title: 'Trier par'),
          children: [
            _SortOptionTile(
              label: 'Performance',
              directionIcon: Icons.arrow_upward_rounded,
              selected: _sortOption == _AllCryptoSortOption.performanceDesc,
              onTap: () =>
                  Navigator.of(context).pop(_AllCryptoSortOption.performanceDesc),
            ),
            _SortOptionTile(
              label: 'Performance',
              directionIcon: Icons.arrow_downward_rounded,
              selected: _sortOption == _AllCryptoSortOption.performanceAsc,
              onTap: () =>
                  Navigator.of(context).pop(_AllCryptoSortOption.performanceAsc),
            ),
            _SortOptionTile(
              label: 'Capitalisation',
              directionIcon: Icons.arrow_upward_rounded,
              selected: _sortOption == _AllCryptoSortOption.marketCapDesc,
              onTap: () =>
                  Navigator.of(context).pop(_AllCryptoSortOption.marketCapDesc),
            ),
            _SortOptionTile(
              label: 'Capitalisation',
              directionIcon: Icons.arrow_downward_rounded,
              selected: _sortOption == _AllCryptoSortOption.marketCapAsc,
              onTap: () =>
                  Navigator.of(context).pop(_AllCryptoSortOption.marketCapAsc),
            ),
          ],
        );
      },
    );
    if (selected != null && mounted) {
      setState(() => _sortOption = selected);
    }
  }

  void _openCrypto(AllCryptoItem item) {
    // Utiliser le provider_symbol pour dériver le ticker court (BTC, ETH…) afin que
    // l’écran détail appelle les API avec le bon symbole (BTCUSDT, ETHUSDT…).
    final ticker = (item.providerSymbol != null && item.providerSymbol!.trim().isNotEmpty)
        ? marketShortSymbol(item.providerSymbol!)
        : item.ticker;
    if (ticker.isEmpty || ticker == '—') return;
    final slug = ticker.toLowerCase();
    final redirectUrl = item.redirectUrl.trim().startsWith('crypto://')
        ? item.redirectUrl.trim()
        : 'crypto://$slug';
    final asset = CryptoAssetItem(
      name: item.name,
      ticker: ticker,
      price: item.price,
      variationPercent: item.variationPercent,
      redirectUrl: redirectUrl,
    );
    if (!context.mounted) return;
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) => CryptoDetailScreen(asset: asset),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _filteredItems;
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppTopNavBar(
        leadingType: AppTopNavBarLeading.back,
        title: 'Cryptos',
        onBackTap: () => Navigator.of(context).pop(),
        centerTitle: false,
        titleOpacity: _navTitleOpacity,
        titleTextStyle: AppTypography.paragraph.copyWith(
          color: AppColors.textPrimary,
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
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
                  child: AppPageTitle('Cryptos'),
                ),
              ),
              const SliverToBoxAdapter(child: SizedBox(height: AppSpacing.xl)),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
                  child: _AllCryptoSearchBar(controller: _searchController),
                ),
              ),
              const SliverToBoxAdapter(child: SizedBox(height: AppSpacing.lg)),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
                  child: Row(
                    children: [
                      AppSectionTitle('Cryptos · ${filtered.length}'),
                      const Spacer(),
                      Material(
                        color: Colors.transparent,
                        child: InkWell(
                          onTap: _openSortSheet,
                          borderRadius: BorderRadius.circular(999),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                              horizontal: AppSpacing.xs,
                              vertical: AppSpacing.xs,
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  _sortLabel,
                                  style: AppTypography.meta.copyWith(
                                    color: AppColors.accent,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                const SizedBox(width: 4),
                                Icon(
                                  _sortDirectionIcon,
                                  size: 14,
                                  color: AppColors.accent,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SliverToBoxAdapter(child: SizedBox(height: AppSpacing.lg)),
              if (_loading)
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
                    child: _AllCryptoLoadingCard(),
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
                    child: _AllCryptoListCard(
                      items: filtered,
                      onTap: _openCrypto,
                    ),
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
}

/// Module de chargement : carte avec lignes skeleton (même structure que la liste cryptos).
class _AllCryptoLoadingCard extends StatefulWidget {
  @override
  State<_AllCryptoLoadingCard> createState() => _AllCryptoLoadingCardState();
}

class _AllCryptoLoadingCardState extends State<_AllCryptoLoadingCard>
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
        return SettingsCard(
          children: List.generate(8, (_) => _buildSkeletonRow()),
        );
      },
    );
  }

  Widget _buildSkeletonRow() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(10),
              color: AppColors.textSecondary.withValues(alpha: _animation.value),
            ),
          ),
          const SizedBox(width: 12),
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

class _AllCryptoSearchBar extends StatelessWidget {
  const _AllCryptoSearchBar({required this.controller});

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

class _AllCryptoListCard extends StatelessWidget {
  const _AllCryptoListCard({
    required this.items,
    required this.onTap,
  });

  final List<AllCryptoItem> items;
  final void Function(AllCryptoItem item) onTap;

  static String _formatVariation(double value) {
    final abs = value.abs();
    final formatted = abs.toStringAsFixed(2).replaceAll('.', ',');
    if (value >= 0) return '▲ $formatted %';
    return '▼ $formatted %';
  }

  static String? _resolveLogoUrl(String ticker, String? apiLogoUrl) {
    final resolved = Config.resolveLogoUrl(apiLogoUrl);
    if (resolved != null && resolved.isNotEmpty) return resolved;
    final t = ticker.trim().toLowerCase();
    if (t.isEmpty) return null;
    final base = t.endsWith('usdt') ? t.substring(0, t.length - 4) : t;
    if (base.isEmpty) return null;
    return Config.resolveLogoUrl('/media/crypto_logos/$base.png');
  }

  @override
  Widget build(BuildContext context) {
    return SettingsCard(
      children: [
        for (final item in items)
          _buildRow(item),
      ],
    );
  }

  Widget _buildRow(AllCryptoItem item) {
    final isPositive = item.variationPercent >= 0;
    final variationColor = isPositive ? AppColors.green : AppColors.red;
    final resolvedUrl = _resolveLogoUrl(item.ticker, item.logoUrl);

    return SettingsListItem(
      leading: CryptoAvatar(
        ticker: item.ticker,
        logoUrl: resolvedUrl,
      ),
      title: item.name,
      subtitle: item.ticker,
      value: item.price,
      valueSubtext: _formatVariation(item.variationPercent),
      valueSubtextColor: variationColor,
      onTap: () => onTap(item),
    );
  }
}

class _SortOptionTile extends StatelessWidget {
  const _SortOptionTile({
    required this.label,
    required this.directionIcon,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final IconData directionIcon;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.xl,
          vertical: AppSpacing.md,
        ),
        child: Row(
          children: [
            Icon(
              directionIcon,
              color: AppColors.textSecondary,
              size: 16,
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: Text(
                label,
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.textPrimary,
                  fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                ),
              ),
            ),
            if (selected)
              const Icon(
                Icons.check_rounded,
                color: AppColors.accent,
                size: 18,
              ),
          ],
        ),
      ),
    );
  }
}
