import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../core/config.dart';
import '../../../../core/currency_preference.dart';
import '../../../../design_system/design_system.dart';
import '../../../../ui/components/line_chart_module.dart';
import '../../../../ui/theme/app_colors.dart' as ui_theme;
import '../../../markets/data/market_data_api.dart';
import '../../../markets/data/market_data_ws_service.dart';
import '../../../markets/data/market_display_utils.dart';
import '../../../markets/presentation/screens/crypto_detail_screen.dart';
import '../../../markets/presentation/widgets/top_crypto_assets_module.dart';
import '../../data/crypto_positions_api.dart';
import '../../data/wallet_history_api.dart';
import '../../domain/models/crypto_wallet_detail.dart';
import '../../../deposit/presentation/screens/deposit_crypto_screen.dart';
import '../../../alerts/presentation/screens/alerts_list_screen.dart';
import '../../../alerts/presentation/screens/orders_list_screen.dart';
import 'buy_flow/buy_flow_controller.dart';
import 'sell_flow/sell_flow_controller.dart';
import 'transaction_screen.dart';
import 'wallet_statistics_screen.dart';

class CryptoWalletDetailScreen extends StatefulWidget {
  const CryptoWalletDetailScreen({
    super.key,
    required this.asset,
    required this.assetName,
  });

  final String asset;
  final String assetName;

  @override
  State<CryptoWalletDetailScreen> createState() =>
      _CryptoWalletDetailScreenState();
}

class _CryptoWalletDetailScreenState extends State<CryptoWalletDetailScreen> {
  final CryptoPositionsApi _api = const CryptoPositionsApi();
  final WalletHistoryApi _historyApi = const WalletHistoryApi();
  final MarketDataApi _marketDataApi = MarketDataApi();
  final MarketDataWsService _wsService = MarketDataWsService();

  CryptoWalletDetail? _detail;
  bool _isLoading = true;
  String? _loadError;
  double? _livePrice;
  double? _livePriceUsd;
  double? _change24hPct;
  String? _logoUrl;
  List<double>? _heroSparkline;

  String get _providerSymbol => tickerToProviderSymbol(widget.asset);

  @override
  void initState() {
    super.initState();
    _load();
    _loadHeroSparkline();
    _subscribeWs();
  }

  @override
  void dispose() {
    _wsService.disconnect();
    super.dispose();
  }

  void _subscribeWs() {
    _wsService.subscribe([_providerSymbol], _onWsQuotes);
  }

  void _onWsQuotes(List<QuoteUpdate> updates) {
    if (updates.isEmpty || !mounted) return;
    final pref = CurrencyPreference.instance;
    for (final u in updates) {
      if (u.symbol == _providerSymbol) {
        final price = pref.selectValue(eur: u.priceEur, usd: u.price);
        if (price != null) {
          setState(() {
            _livePrice = price;
            _livePriceUsd = u.price;
          });
        }
        break;
      }
    }
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _loadError = null;
    });
    try {
      final results = await Future.wait([
        _api.fetchDetail(widget.asset),
        _marketDataApi.getMarketSummary(symbols: [_providerSymbol]),
      ]);
      if (!mounted) return;
      final data = results[0] as CryptoWalletDetail;
      final summaries = results[1] as List<MarketSummaryItem>;
      setState(() {
        _detail = data;
        if (summaries.isNotEmpty) {
          final s = summaries.first;
          _change24hPct = s.change24hPct;
          _logoUrl = s.logoUrl;
          final pref = CurrencyPreference.instance;
          _livePrice ??= pref.selectValue(eur: s.priceEur, usd: s.price);
          _livePriceUsd ??= s.price;
        }
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _loadError = 'Impossible de charger les détails';
      });
    }
  }

  Future<void> _loadHeroSparkline() async {
    try {
      final data = await _historyApi.fetchHistory(
        period: 'ALL',
        asset: widget.asset,
        mode: 'performance_value',
      );
      if (!mounted || data.points.isEmpty) return;
      final values = data.points.map((p) => p.walletValue).toList();
      setState(() => _heroSparkline = values);
    } catch (_) {}
  }

  static final _eurFormatter = NumberFormat.currency(
    locale: 'fr_FR',
    symbol: '€',
    decimalDigits: 2,
  );

  static final _usdFormatter = NumberFormat.currency(
    locale: 'en_US',
    symbol: '\$',
    decimalDigits: 2,
  );

  NumberFormat get _activeFormatter =>
      CurrencyPreference.instance.currency == ReferenceCurrency.usd
          ? _usdFormatter
          : _eurFormatter;

  @override
  Widget build(BuildContext context) {
    if (_isLoading) return _CryptoDetailShimmer(assetName: widget.assetName);

    if (_loadError != null) {
      return Scaffold(
        backgroundColor: AppColors.pageBackground,
        appBar: AppBar(
          title: Text(widget.assetName),
          backgroundColor: const Color(0xFF0D1B2A),
          foregroundColor: Colors.white,
        ),
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline, size: 48, color: AppColors.textSecondary),
              const SizedBox(height: AppSpacing.md),
              Text(_loadError!, style: AppTypography.bodyMedium),
              const SizedBox(height: AppSpacing.lg),
              ElevatedButton(onPressed: _load, child: const Text('Réessayer')),
            ],
          ),
        ),
      );
    }

    return _buildPage();
  }

  static const Color _defaultAssetColor = Color(0xFF0D1B2A);

  static const HeroOverlayConfig _assetOverlay = HeroOverlayConfig(
    tintOpacity: 0,
    gradientBegin: Alignment.bottomLeft,
    gradientEnd: Alignment.topRight,
    gradientStartOpacity: 0.60,
    gradientEndOpacity: 0,
  );

  Widget _buildPage() {
    final d = _detail!;
    final pref = CurrencyPreference.instance;
    final totalValue = pref.selectValue(eur: d.totalValueEur, usd: d.totalValueUsd) ?? 0;
    final totalLabel = _activeFormatter.format(totalValue);
    final brandColor = AppColors.cryptoAssetBrand[widget.asset] ?? _defaultAssetColor;

    return LayoutPageLevel2(
      heroHeightFraction: 0.65,
      heroFallbackColor: brandColor,
      heroOverlay: _assetOverlay,
      title: d.name,
      subtitle: totalLabel,
      subtitleStyle: AppTypography.heroAmount.copyWith(color: Colors.white),
      heroFullBleed: _heroSparkline != null
          ? LineChartModule(
              data: _heroSparkline,
              height: 80,
              strokeWidth: 3,
              lineColor: Colors.white,
              paddingTop: 8,
              paddingBottom: 8,
            )
          : const SizedBox(height: 80),
      heroActions: _buildHeroSubtitle(d),
      heroActionsBelowFullBleed: _buildHeroActionButtons(),
      leadingType: AppTopNavBarLeading.back,
      onLeadingTap: () => Navigator.of(context).pop(),
      navBarActions: [
        AppTopNavBarAction(
          icon: Icons.swap_vert_rounded,
          onPressed: () {
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => OrdersListScreen(
                  asset: widget.asset,
                  currentPrice: _livePriceUsd,
                ),
              ),
            );
          },
        ),
        AppTopNavBarAction(
          icon: Icons.add_alert_rounded,
          onPressed: () {
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => AlertsListScreen(
                  asset: widget.asset,
                  currentPrice: _livePrice,
                ),
              ),
            );
          },
        ),
        AppTopNavBarAction(
          icon: Icons.bar_chart_rounded,
          onPressed: () {
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => WalletStatisticsScreen(
                  asset: widget.asset,
                  assetName: widget.assetName,
                  portfolioScope: 'direct',
                ),
              ),
            );
          },
        ),
      ],
      onRefresh: _load,
      content: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: _buildInstrumentModule(),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: _buildKeyInfoModule(d),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: _buildTransactionHistoryModule(),
        ),
      ],
    );
  }

  Widget _buildHeroSubtitle(CryptoWalletDetail d) {
    final suffix = d.includesPrivy && !d.isPrivyOnly
        ? ' · incl. wallet Privy'
        : d.isPrivyOnly
            ? ' · wallet Privy'
            : '';
    return Text(
      '${d.volume} ${d.asset}$suffix',
      style: AppTypography.bodySmall.copyWith(color: Colors.white70),
      textAlign: TextAlign.center,
    );
  }

  Widget _buildHeroActionButtons() {
    final detail = _detail;
    if (detail != null && detail.isPrivyOnly) {
      return CircleButtonRow(
        items: [
          CircleButtonItem(
            icon: Icons.arrow_downward_rounded,
            label: 'Dépôt',
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => const DepositCryptoScreen(),
                ),
              );
            },
            isPrimary: true,
          ),
        ],
      );
    }

    return CircleButtonRow(
      items: [
        CircleButtonItem(
          icon: Icons.add_rounded,
          label: 'Acheter',
          onTap: _openBuyModal,
          isPrimary: true,
        ),
        CircleButtonItem(
          icon: Icons.remove_rounded,
          label: 'Vendre',
          onTap: _openSellModal,
        ),
      ],
    );
  }

  void _openBuyModal() async {
    final didBuy = await BuyFlowController.start(
      context,
      assetSymbol: widget.asset,
      assetName: widget.assetName,
      assetLogoUrl: Config.resolveLogoUrl(_logoUrl),
    );
    if (didBuy == true && mounted) {
      _load();
      _loadHeroSparkline();
    }
  }

  void _openSellModal() async {
    final detail = _detail;
    if (detail == null) return;
    final balance = double.tryParse(detail.volume) ?? 0;

    final didSell = await SellFlowController.start(
      context,
      assetSymbol: widget.asset,
      assetName: widget.assetName,
      assetLogoUrl: Config.resolveLogoUrl(_logoUrl),
      cryptoBalance: balance,
    );
    if (didSell == true && mounted) {
      _load();
      _loadHeroSparkline();
    }
  }

  Widget _buildInstrumentModule() {
    final pref = CurrencyPreference.instance;
    final sym = pref.currency.symbol;
    final priceLabel = _livePrice != null
        ? '${formatPrice(_livePrice!)} $sym'
        : '—';
    final variation = _change24hPct ?? 0.0;
    final isPositive = variation >= 0;
    final variationLabel = isPositive
        ? '▲ ${variation.abs().toStringAsFixed(2).replaceAll('.', ',')} %'
        : '▼ ${variation.abs().toStringAsFixed(2).replaceAll('.', ',')} %';
    final resolvedLogo = Config.resolveLogoUrl(_logoUrl);

    return TransactionListCard(
      items: [
        TransactionListItemData(
          leadingWidget: CryptoAvatar(
            ticker: widget.asset,
            logoUrl: resolvedLogo,
            size: CryptoAvatarSize.medium,
          ),
          title: widget.assetName,
          subtitle: widget.asset,
          amount: priceLabel,
          secondaryAmount: variationLabel,
          secondaryAmountColor: isPositive
              ? ui_theme.AppColors.positive
              : ui_theme.AppColors.negative,
          showChevron: true,
          onTap: () {
            final asset = CryptoAssetItem(
              name: widget.assetName,
              ticker: widget.asset,
              price: priceLabel,
              variationPercent: variation,
              redirectUrl: 'crypto://${widget.asset.toLowerCase()}',
              logoUrl: _logoUrl,
            );
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => CryptoDetailScreen(asset: asset),
              ),
            );
          },
        ),
      ],
    );
  }

  Widget _buildKeyInfoModule(CryptoWalletDetail d) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'My position',
              style: AppTypography.sectionTitle.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 14),
            _infoRow('Volume', '${d.volume} ${d.asset}'),
            const SizedBox(height: 14),
            _infoRow('Solde total', _activeFormatter.format(
              CurrencyPreference.instance.selectValue(eur: d.totalValueEur, usd: d.totalValueUsd) ?? 0,
            )),
            const SizedBox(height: 14),
            _infoRow(
              'Gains en cours',
              _selectGain(d.unrealizedGainEur, d.unrealizedGainUsd) != null
                  ? _formatSignedAmount(_selectGain(d.unrealizedGainEur, d.unrealizedGainUsd)!)
                  : '—',
              valueColor: _gainColor(_selectGain(d.unrealizedGainEur, d.unrealizedGainUsd)),
            ),
            const SizedBox(height: 14),
            _infoRow(
              "Prix moyen d'achat",
              _selectGain(d.avgBuyPriceEur, d.avgBuyPriceUsd) != null
                  ? _activeFormatter.format(_selectGain(d.avgBuyPriceEur, d.avgBuyPriceUsd)!)
                  : '—',
            ),
            const SizedBox(height: 14),
            _infoRow(
              'Prix actuel',
              _livePrice != null
                  ? _activeFormatter.format(_livePrice!)
                  : _selectGain(d.currentPriceEur, d.currentPriceUsd) != null
                      ? _activeFormatter.format(_selectGain(d.currentPriceEur, d.currentPriceUsd)!)
                      : '—',
              valueColor: AppColors.accent,
            ),
            const SizedBox(height: 14),
            _infoRow(
              'Gains encaissés',
              _formatSignedAmount(
                CurrencyPreference.instance.selectValue(
                  eur: d.realizedGainEur,
                  usd: d.realizedGainUsd,
                ) ?? 0,
              ),
              valueColor: _gainColor(
                CurrencyPreference.instance.selectValue(
                  eur: d.realizedGainEur,
                  usd: d.realizedGainUsd,
                ),
              ),
            ),
            const SizedBox(height: 14),
            _infoRow(
              'Total des gains',
              _selectGain(d.totalGainEur, d.totalGainUsd) != null
                  ? _formatSignedAmount(_selectGain(d.totalGainEur, d.totalGainUsd)!)
                  : '—',
              valueColor: _gainColor(_selectGain(d.totalGainEur, d.totalGainUsd)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTransactionHistoryModule() {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: TransactionListCard(
        showShadow: false,
        items: [
          TransactionListItemData(
            icon: Icons.receipt_long_rounded,
            iconColor: AppColors.textPrimary,
            avatarBackgroundColor: AppColors.placeholderBg,
            title: 'Transactions history',
            subtitle: 'Voir l\'historique complet',
            amount: '',
            showChevron: true,
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => _CryptoTransactionsPage(
                    asset: widget.asset,
                    assetName: widget.assetName,
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _infoRow(String label, String value, {Color? valueColor}) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Text(
            label,
            style: AppTypography.bodyMedium.copyWith(
              color: AppColors.textPrimary,
            ),
          ),
        ),
        const SizedBox(width: 12),
        Text(
          value,
          style: AppTypography.bodyMedium.copyWith(
            color: valueColor ?? AppColors.textPrimary,
          ),
          textAlign: TextAlign.right,
        ),
      ],
    );
  }

  double? _selectGain(double? eur, double? usd) {
    return CurrencyPreference.instance.selectValue(eur: eur, usd: usd);
  }

  String _formatSignedAmount(double value) {
    final formatted = _activeFormatter.format(value.abs());
    if (value > 0) return '+$formatted';
    if (value < 0) return '-$formatted';
    return formatted;
  }

  Color? _gainColor(double? value) {
    if (value == null || value == 0) return null;
    if (value > 0) return const Color(0xFF059669);
    return const Color(0xFFDC2626);
  }

}

// ─────────────── Crypto Transactions Page ───────────────

class _CryptoTransactionsPage extends StatefulWidget {
  const _CryptoTransactionsPage({
    required this.asset,
    required this.assetName,
  });

  final String asset;
  final String assetName;

  @override
  State<_CryptoTransactionsPage> createState() => _CryptoTransactionsPageState();
}

class _CryptoTransactionsPageState extends State<_CryptoTransactionsPage> {
  final CryptoPositionsApi _api = const CryptoPositionsApi();
  final ScrollController _scrollController = ScrollController();
  List<CryptoTransactionItem>? _transactions;
  bool _isLoading = true;
  String? _error;
  double _navTitleOpacity = 0;
  String? _selectedMonth;

  static final _eurFormatter = NumberFormat.currency(
    locale: 'fr_FR',
    symbol: '€',
    decimalDigits: 2,
  );

  static const _frenchMonths = [
    'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
    'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre',
  ];

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    _load();
  }

  @override
  void dispose() {
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

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final txs = await _api.fetchTransactions(widget.asset);
      if (!mounted) return;
      setState(() {
        _transactions = txs;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _error = 'Impossible de charger les transactions';
      });
    }
  }

  List<String> get _availableMonths {
    final txs = _transactions;
    if (txs == null || txs.isEmpty) return [];
    final seen = <String>{};
    final result = <String>[];
    for (final tx in txs) {
      final key = _monthKey(tx.createdAt);
      if (seen.add(key)) result.add(key);
    }
    return result;
  }

  static String _monthKey(DateTime dt) {
    return '${_frenchMonths[dt.month - 1]} ${dt.year}';
  }

  static String _monthKeyShort(DateTime dt) {
    final m = _frenchMonths[dt.month - 1];
    return '${m[0].toUpperCase()}${m.substring(1, 3)}. ${dt.year}';
  }

  List<CryptoTransactionItem> get _filteredTransactions {
    final txs = _transactions ?? [];
    if (_selectedMonth == null) return txs;
    return txs.where((tx) => _monthKey(tx.createdAt) == _selectedMonth).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppTopNavBar(
        leadingType: AppTopNavBarLeading.back,
        title: 'Transactions ${widget.assetName}',
        titleOpacity: _navTitleOpacity,
        centerTitle: false,
        titleTextStyle: AppTypography.paragraph.copyWith(
          color: AppColors.textPrimary,
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
        onBackTap: () => Navigator.of(context).pop(),
      ),
      body: SafeArea(
        bottom: false,
        child: _buildBody(),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator.adaptive());
    }
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline_rounded, size: 48, color: AppColors.textSecondary),
            const SizedBox(height: AppSpacing.md),
            Text(_error!, style: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary)),
            const SizedBox(height: AppSpacing.lg),
            TextButton(onPressed: _load, child: const Text('Réessayer')),
          ],
        ),
      );
    }

    final txs = _transactions ?? [];
    if (txs.isEmpty) {
      return Center(
        child: Text(
          'Aucune transaction pour le moment',
          style: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary),
        ),
      );
    }

    final filtered = _filteredTransactions;
    final sections = _groupByDay(filtered);
    final months = _availableMonths;

    return RefreshIndicator(
      onRefresh: _load,
      child: CustomScrollView(
        controller: _scrollController,
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.only(
                left: AppSpacing.pageEdge,
                top: AppSpacing.md,
                bottom: AppSpacing.sm,
              ),
              child: AppPageTitle('Transactions ${widget.assetName}'),
            ),
          ),
          if (months.length > 1)
            SliverToBoxAdapter(
              child: _buildMonthTabs(months),
            ),
          if (filtered.isEmpty)
            SliverFillRemaining(
              hasScrollBody: false,
              child: Center(
                child: Text(
                  'Aucune transaction ce mois',
                  style: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary),
                ),
              ),
            )
          else
            SliverPadding(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.pageEdge,
                vertical: AppSpacing.sm,
              ),
              sliver: SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, i) {
                    final section = sections[i];
                    return Padding(
                      padding: EdgeInsets.only(
                        bottom: i < sections.length - 1 ? AppSpacing.xl : 0,
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Padding(
                            padding: const EdgeInsets.only(left: 4, bottom: AppSpacing.sm),
                            child: Text(section.$1, style: AppTypography.title2),
                          ),
                          TransactionListCard(
                            items: section.$2.map(_mapTxToItem).toList(),
                          ),
                        ],
                      ),
                    );
                  },
                  childCount: sections.length,
                ),
              ),
            ),
          SliverToBoxAdapter(
            child: SizedBox(height: MediaQuery.paddingOf(context).bottom + AppSpacing.xl),
          ),
        ],
      ),
    );
  }

  Widget _buildMonthTabs(List<String> months) {
    return SizedBox(
      height: 40,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
        itemCount: months.length + 1,
        separatorBuilder: (_, __) => const SizedBox(width: AppSpacing.sm),
        itemBuilder: (context, i) {
          if (i == 0) {
            final isSelected = _selectedMonth == null;
            return _MonthChip(
              label: 'Tout',
              isSelected: isSelected,
              onTap: () => setState(() => _selectedMonth = null),
            );
          }
          final month = months[i - 1];
          final parts = month.split(' ');
          final shortLabel = '${parts[0][0].toUpperCase()}${parts[0].substring(1, 3)}. ${parts[1]}';
          final isSelected = _selectedMonth == month;
          return _MonthChip(
            label: shortLabel,
            isSelected: isSelected,
            onTap: () => setState(() => _selectedMonth = month),
          );
        },
      ),
    );
  }

  List<(String, List<CryptoTransactionItem>)> _groupByDay(List<CryptoTransactionItem> txs) {
    final groups = <String, List<CryptoTransactionItem>>{};
    for (final tx in txs) {
      final label = _dayLabel(tx.createdAt);
      (groups[label] ??= []).add(tx);
    }
    return groups.entries.map((e) => (e.key, e.value)).toList();
  }

  static String _dayLabel(DateTime dt) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final txDay = DateTime(dt.year, dt.month, dt.day);
    final diff = today.difference(txDay).inDays;
    if (diff == 0) return "Aujourd'hui";
    if (diff == 1) return 'Hier';
    return '${dt.day} ${_frenchMonths[dt.month - 1]} ${dt.year}';
  }

  TransactionListItemData _mapTxToItem(CryptoTransactionItem tx) {
    final hh = tx.createdAt.hour.toString().padLeft(2, '0');
    final mm = tx.createdAt.minute.toString().padLeft(2, '0');
    final timeLabel = '$hh:$mm';

    if (tx.isPrivyDeposit) {
      final cryptoFormatted = _formatCryptoAmount(tx.amountCrypto);
      final amountLabel = '+$cryptoFormatted ${tx.asset}';
      return TransactionListItemData(
        leadingWidget: CircleAvatar(
          radius: 20,
          backgroundColor: const Color(0xFF22C55E).withValues(alpha: 0.12),
          child: const Icon(Icons.arrow_downward_rounded, color: Color(0xFF22C55E), size: 20),
        ),
        title: tx.title.isNotEmpty ? tx.title : 'Dépôt ${tx.asset}',
        subtitle: tx.subtitle.isNotEmpty ? tx.subtitle : timeLabel,
        amount: amountLabel,
        secondaryAmount: timeLabel,
        onTap: () => _openTransactionDetail(
          tx,
          tx.asset,
          tx.asset,
          amountLabel,
          isDeposit: true,
        ),
      );
    }

    final isBuy = tx.side == 'buy';
    final sign = isBuy ? '+' : '-';
    final cryptoFormatted = _formatCryptoAmount(tx.amountCrypto);
    final amountLabel = '$sign$cryptoFormatted ${tx.asset}';
    final fiatLabel = _eurFormatter.format(double.tryParse(tx.amountFiat) ?? 0);
    final fiatSign = isBuy ? '-' : '+';

    final assetUpper = tx.asset.toUpperCase();

    final fromAsset = (tx.fromAsset ?? (isBuy ? tx.currency : assetUpper)).toUpperCase();
    final toAsset = (tx.toAsset ?? (isBuy ? assetUpper : tx.currency)).toUpperCase();

    final fromLogo = Config.resolveLogoUrl(
      '/media/crypto_logos/${fromAsset.toLowerCase()}.png',
    );
    final toLogo = Config.resolveLogoUrl(
      '/media/crypto_logos/${toAsset.toLowerCase()}.png',
    );

    final isFromFiat = fromAsset == 'EUR' || fromAsset == 'EURC' || fromAsset == 'EURT';
    final isToFiat = toAsset == 'EUR' || toAsset == 'EURC' || toAsset == 'EURT';

    final leading = TransactionSwapAvatar(
      fromTicker: fromAsset,
      toTicker: toAsset,
      fromLogoUrl: isFromFiat ? null : fromLogo,
      toLogoUrl: isToFiat ? null : toLogo,
      fromIcon: isFromFiat ? Icons.euro_rounded : null,
      toIcon: isToFiat ? Icons.euro_rounded : null,
    );

    return TransactionListItemData(
      leadingWidget: leading,
      title: '$fromAsset → $toAsset',
      subtitle: timeLabel,
      amount: amountLabel,
      secondaryAmount: '$fiatSign$fiatLabel',
      onTap: () => _openTransactionDetail(tx, fromAsset, toAsset, amountLabel),
    );
  }

  void _openTransactionDetail(
    CryptoTransactionItem tx,
    String fromAsset,
    String toAsset,
    String formattedAmount, {
    bool isDeposit = false,
  }) {
    final hh = tx.createdAt.hour.toString().padLeft(2, '0');
    final mm = tx.createdAt.minute.toString().padLeft(2, '0');
    final dateStr = '${tx.createdAt.day} ${_frenchMonths[tx.createdAt.month - 1]} ${tx.createdAt.year} \u2022 $hh:$mm';

    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => TransactionScreen(
          transactionId: tx.id,
          merchant: isDeposit
              ? (tx.title.isNotEmpty ? tx.title : 'Dépôt $fromAsset')
              : '$fromAsset → $toAsset',
          dateTime: dateStr,
          amount: formattedAmount,
          icon: isDeposit ? Icons.arrow_downward_rounded : Icons.swap_horiz_rounded,
          iconColor: isDeposit
              ? const Color(0xFF22C55E)
              : (tx.side == 'buy' ? const Color(0xFF22C55E) : const Color(0xFFF97316)),
        ),
      ),
    );
  }

  static String _formatCryptoAmount(String raw) {
    final v = double.tryParse(raw);
    if (v == null) return raw;
    if (v == 0) return '0';
    final abs = v.abs();
    String s;
    if (abs < 0.0001) {
      s = v.toStringAsFixed(8);
    } else if (abs < 1) {
      s = v.toStringAsFixed(6);
    } else if (abs < 1000) {
      s = v.toStringAsFixed(4);
    } else {
      s = v.toStringAsFixed(2);
    }
    if (s.contains('.')) {
      s = s.replaceAll(RegExp(r'0+$'), '');
      s = s.replaceAll(RegExp(r'\.$'), '');
    }
    return s;
  }
}

class _MonthChip extends StatelessWidget {
  const _MonthChip({
    required this.label,
    required this.isSelected,
    required this.onTap,
  });

  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: AppMotion.fast,
        curve: AppMotion.standard,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.textPrimary : AppColors.cardBackground,
          borderRadius: BorderRadius.circular(AppRadius.full),
          border: isSelected
              ? null
              : Border.all(color: AppColors.textSecondary.withValues(alpha: 0.2)),
        ),
        child: Text(
          label,
          style: AppTypography.labelEmphasized.copyWith(
            color: isSelected ? Colors.white : AppColors.textPrimary,
          ),
        ),
      ),
    );
  }
}

// ─────────────── Shimmer ───────────────

class _CryptoDetailShimmer extends StatefulWidget {
  const _CryptoDetailShimmer({required this.assetName});
  final String assetName;

  @override
  State<_CryptoDetailShimmer> createState() => _CryptoDetailShimmerState();
}

class _CryptoDetailShimmerState extends State<_CryptoDetailShimmer>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat(reverse: true);
    _animation = CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final screen = MediaQuery.sizeOf(context);
    final heroHeight = screen.height * 0.60;

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      body: AnimatedBuilder(
        animation: _animation,
        builder: (context, _) {
          return SingleChildScrollView(
            physics: const NeverScrollableScrollPhysics(),
            child: Column(
              children: [
                Container(
                  width: screen.width,
                  height: heroHeight,
                  decoration: const BoxDecoration(color: Color(0xFF0D1B2A)),
                  child: SafeArea(
                    bottom: false,
                    child: Column(
                      children: [
                        Padding(
                          padding: const EdgeInsets.symmetric(
                            horizontal: AppSpacing.lg,
                            vertical: AppSpacing.sm,
                          ),
                          child: Row(
                            children: [
                              _shimmerCircle(40, light: true),
                              const Spacer(),
                              _shimmerCircle(40, light: true),
                            ],
                          ),
                        ),
                        const Spacer(),
                        _shimmerRect(width: 100, height: 28, light: true, radius: 8),
                        const SizedBox(height: AppSpacing.md),
                        _shimmerRect(width: 180, height: 32, light: true, radius: 8),
                        const SizedBox(height: AppSpacing.lg),
                        _shimmerRect(width: 140, height: 14, light: true, radius: 6),
                        const SizedBox(height: AppSpacing.xl),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            _shimmerCircle(52, light: true),
                            const SizedBox(width: 24),
                            _shimmerCircle(52, light: true),
                          ],
                        ),
                        const SizedBox(height: 40),
                      ],
                    ),
                  ),
                ),
                Transform.translate(
                  offset: const Offset(0, -AppSpacing.lg),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Container(
                      decoration: BoxDecoration(
                        color: AppColors.cardBackground,
                        borderRadius: BorderRadius.circular(24),
                        boxShadow: [
                          BoxShadow(
                            color: AppColors.textPrimary.withValues(alpha: 0.06),
                            blurRadius: 8,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 20),
                        child: Column(
                          children: List.generate(6, (i) => _buildInfoRowShimmer(i)),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildInfoRowShimmer(int index) {
    final labelWidths = [80.0, 100.0, 120.0, 140.0, 120.0, 110.0];
    final valueWidths = [100.0, 90.0, 110.0, 95.0, 85.0, 105.0];
    return Padding(
      padding: EdgeInsets.only(top: index > 0 ? 14 : 0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          _shimmerRect(
            width: labelWidths[index % labelWidths.length],
            height: 14,
            light: false,
            radius: 4,
          ),
          _shimmerRect(
            width: valueWidths[index % valueWidths.length],
            height: 14,
            light: false,
            radius: 4,
          ),
        ],
      ),
    );
  }

  Widget _shimmerRect({
    required double width,
    required double height,
    required bool light,
    double radius = 4,
  }) {
    final t = _animation.value;
    final baseAlpha = light ? 0.08 : 0.04;
    final peakAlpha = light ? 0.22 : 0.10;
    final alpha = baseAlpha + (peakAlpha - baseAlpha) * t;
    final color = light
        ? Colors.white.withValues(alpha: alpha)
        : AppColors.textSecondary.withValues(alpha: alpha);
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(radius),
      ),
    );
  }

  Widget _shimmerCircle(double size, {required bool light}) {
    final t = _animation.value;
    final baseAlpha = light ? 0.08 : 0.04;
    final peakAlpha = light ? 0.22 : 0.10;
    final alpha = baseAlpha + (peakAlpha - baseAlpha) * t;
    final color = light
        ? Colors.white.withValues(alpha: alpha)
        : AppColors.textSecondary.withValues(alpha: alpha);
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(shape: BoxShape.circle, color: color),
    );
  }
}
