import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../core/config.dart';
import '../../../../core/currency_preference.dart';
import '../../../../design_system/design_system.dart';
import '../../../../ui/components/line_chart_module.dart';
import '../../../../ui/components/transaction/transaction_avatar.dart';
import '../../../../ui/components/transaction/transaction_tile.dart';
import '../../../favorites/data/favorites_api.dart';
import '../../data/bundle_api.dart';
import '../../data/wallet_history_api.dart';
import 'bundle_invest_flow/bundle_invest_flow_controller.dart';
import 'bundle_rebalance_flow/rebalance_confirmation_screen.dart';
import 'bundle_statistics_screen.dart';

class BundleWalletDetailScreen extends StatefulWidget {
  const BundleWalletDetailScreen({
    super.key,
    required this.bundle,
  });

  final MyBundleSummary bundle;

  @override
  State<BundleWalletDetailScreen> createState() =>
      _BundleWalletDetailScreenState();
}

class _BundleWalletDetailScreenState extends State<BundleWalletDetailScreen> {
  final BundleApi _bundleApi = const BundleApi();
  final WalletHistoryApi _historyApi = const WalletHistoryApi();
  final FavoritesApi _favoritesApi = FavoritesApi();

  MyBundleSummary? _bundle;
  List<double>? _heroSparkline;
  bool _isFavorite = false;
  String? _favoriteId;

  @override
  void initState() {
    super.initState();
    _bundle = widget.bundle;
    _loadHeroSparkline();
    _loadFavoriteStatus();
    _refresh();
  }

  Future<void> _loadFavoriteStatus() async {
    try {
      final favs = await _favoritesApi.fetchFavorites(entityType: 'bundle');
      if (!mounted) return;
      final match = favs.where((f) => f.entityId == widget.bundle.portfolioId).toList();
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
        entityType: 'bundle',
        entityId: widget.bundle.portfolioId,
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

  Future<void> _loadHeroSparkline() async {
    try {
      final data = await _historyApi.fetchBundleHistory(
        portfolioId: widget.bundle.portfolioId,
        period: 'ALL',
        mode: 'performance_value',
      );
      if (!mounted || data.points.isEmpty) return;
      setState(() => _heroSparkline = data.points.map((p) => p.walletValue).toList());
    } catch (_) {}
  }

  Future<void> _refresh() async {
    try {
      final bundles = await _bundleApi.getMyBundles();
      if (!mounted) return;
      final match = bundles.where((b) => b.portfolioId == widget.bundle.portfolioId);
      if (match.isNotEmpty) {
        setState(() => _bundle = match.first);
      }
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

  NumberFormat get _fmt =>
      CurrencyPreference.instance.currency == ReferenceCurrency.usd
          ? _usdFormatter
          : _eurFormatter;

  @override
  Widget build(BuildContext context) {
    final b = _bundle!;
    final marketValue = b.totalMarketValue ?? b.totalCostBasis;
    final totalLabel = _fmt.format(marketValue);

    final countLabel = '${b.assetsCount} actif${b.assetsCount > 1 ? 's' : ''}';

    return LayoutPageLevel2(
      heroHeightFraction: 0.60,
      heroFallbackColor: const Color(0xFF6366F1),
      heroOverlay: const HeroOverlayConfig(
        tintOpacity: 0,
        gradientBegin: Alignment.bottomLeft,
        gradientEnd: Alignment.topRight,
        gradientStartOpacity: 0.60,
        gradientEndOpacity: 0,
      ),
      title: b.portfolioName,
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
      heroActions: Text(
        countLabel,
        style: AppTypography.bodySmall.copyWith(color: Colors.white70),
        textAlign: TextAlign.center,
      ),
      heroActionsBelowFullBleed: CircleButtonRow(
        items: [
          CircleButtonItem(
            icon: Icons.add_rounded,
            label: 'Investir',
            onTap: _openInvestFlow,
            isPrimary: true,
          ),
          CircleButtonItem(
            icon: Icons.tune_rounded,
            label: 'Rééquilibrer',
            onTap: _openRebalanceFlow,
          ),
        ],
      ),
      leadingType: AppTopNavBarLeading.back,
      onLeadingTap: () => Navigator.of(context).pop(),
      navBarActions: [
        AppTopNavBarAction(
          icon: Icons.bar_chart_rounded,
          onPressed: () {
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => BundleStatisticsScreen(
                  portfolioId: b.portfolioId,
                  portfolioName: b.portfolioName,
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
      ],
      onRefresh: _refresh,
      content: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: _buildKeyInfoModule(b),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: _buildAllocationDonut(b),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: _buildPositionsModule(b),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: _buildTransactionHistoryModule(),
        ),
      ],
    );
  }

  // ── Key info module ──

  Widget _buildKeyInfoModule(MyBundleSummary b) {
    final marketValue = b.totalMarketValue;
    final costBasis = b.totalCostBasis;
    final unrealizedGain = (marketValue != null && costBasis > 0)
        ? marketValue - costBasis
        : null;

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
              'Mon investissement',
              style: AppTypography.sectionTitle.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 14),
            _infoRow('Valeur de marché', marketValue != null
                ? _fmt.format(marketValue)
                : '—'),
            const SizedBox(height: 14),
            _infoRow('Coût total investi', _fmt.format(costBasis)),
            const SizedBox(height: 14),
            _infoRow(
              'Gains en cours',
              unrealizedGain != null ? _formatSigned(unrealizedGain) : '—',
              valueColor: _gainColor(unrealizedGain),
            ),
            const SizedBox(height: 14),
            _infoRow(
              'Performance',
              b.performancePct != null
                  ? '${b.performancePct! >= 0 ? '+' : ''}${b.performancePct!.toStringAsFixed(2)} %'
                  : '—',
              valueColor: _gainColor(b.performancePct),
            ),
            const SizedBox(height: 14),
            _infoRow('Actifs en portefeuille', '${b.assetsCount}'),
            if (_cashLegLabel(b) != null) ...[
              const SizedBox(height: 14),
              _infoRow('Cash leg restant', _cashLegLabel(b)!),
            ],
          ],
        ),
      ),
    );
  }

  String? _cashLegLabel(MyBundleSummary b) {
    final cashPositions = b.positions.where((p) => p.isCash).toList();
    if (cashPositions.isEmpty) return null;
    final cash = cashPositions.first;
    if (cash.quantity <= 0.001) return null;
    return '${cash.quantity.toStringAsFixed(4)} ${cash.asset}';
  }

  // ── Allocation donut ──

  Widget _buildAllocationDonut(MyBundleSummary b) {
    final allPositions = <BundlePositionInfo>[];
    allPositions.addAll(b.spotPositions);

    final cashPositions = b.positions.where((p) => p.isCash && p.quantity > 0.001).toList();
    for (final cash in cashPositions) {
      allPositions.add(cash);
    }

    if (allPositions.isEmpty) return const SizedBox.shrink();

    final totalMkt = allPositions.fold<double>(
      0,
      (sum, p) => sum + (p.marketValue ?? p.costBasis),
    );

    final slices = allPositions.map((p) {
      final value = p.marketValue ?? p.costBasis;
      final pct = totalMkt > 0 ? (value / totalMkt) * 100 : 0.0;
      return PortfolioAllocationSlice(
        label: p.asset,
        percentage: pct,
      );
    }).toList();

    const cashLegColor = Color(0xFF94A3B8);

    final colors = allPositions.map((p) {
      if (p.isCash) return cashLegColor;
      return AppColors.cryptoAssetBrand[p.asset] ?? const Color(0xFF6B7280);
    }).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Text(
            'Allocation réelle',
            style: AppTypography.sectionTitle.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        PortfolioAllocationModule(
          slices: slices,
          sliceColors: colors,
        ),
      ],
    );
  }

  // ── Positions list ──

  Widget _buildPositionsModule(MyBundleSummary b) {
    final spotPositions = b.spotPositions;
    final cashPositions = b.positions.where((p) => p.isCash && p.quantity > 0.001).toList();
    if (spotPositions.isEmpty && cashPositions.isEmpty) return const SizedBox.shrink();

    final allTiles = <Widget>[
      ...spotPositions.map(_buildPositionTile),
      ...cashPositions.map(_buildPositionTile),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Text(
            'Détail des positions',
            style: AppTypography.sectionTitle.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        Container(
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
          child: ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Column(children: allTiles),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildPositionTile(BundlePositionInfo pos) {
    final isZero = pos.quantity < 0.000001;

    final valueLabel = isZero
        ? _fmt.format(0)
        : pos.marketValue != null
            ? _fmt.format(pos.marketValue!)
            : _fmt.format(pos.costBasis);

    final volumeStr = isZero ? 'Non investi' : _formatVolume(pos.quantity, pos.asset);

    String? perfLabel;
    Color? perfColor;
    if (!isZero && pos.marketValue != null && pos.costBasis > 0) {
      final gain = pos.marketValue! - pos.costBasis;
      final pct = (gain / pos.costBasis) * 100;
      perfLabel = '${pct >= 0 ? '+' : ''}${pct.toStringAsFixed(2)} %';
      perfColor = pct > 0
          ? const Color(0xFF059669)
          : pct < 0
              ? const Color(0xFFDC2626)
              : AppColors.textSecondary;
    }

    final logoKey = pos.asset.trim().toLowerCase();
    final logoUrl = logoKey.isNotEmpty
        ? Config.resolveLogoUrl('/media/crypto_logos/$logoKey.png')
        : null;

    return Opacity(
      opacity: isZero ? 0.5 : 1.0,
      child: TransactionTile(
        avatar: TransactionAvatar(
          icon: _iconForAsset(pos.asset),
          backgroundColor: AppColors.cryptoAssetBrand[pos.asset] ?? Colors.grey,
          iconColor: Colors.white,
          imageUrl: logoUrl,
        ),
        title: pos.asset,
        subtitle: volumeStr,
        rightPrimary: valueLabel,
        rightSecondary: perfLabel,
        rightSecondaryColor: perfColor,
      ),
    );
  }

  // ── Transaction history CTA ──

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
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: TransactionTile(
          avatar: TransactionAvatar(
            icon: Icons.receipt_long_rounded,
            backgroundColor: AppColors.placeholderBg,
            iconColor: AppColors.textPrimary,
          ),
          title: 'Transactions history',
          subtitle: 'Voir l\'historique complet',
          showChevron: true,
          onTap: () {
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => _BundleTransactionsPage(
                  portfolioId: widget.bundle.portfolioId,
                  bundleName: _bundle?.portfolioName ?? widget.bundle.portfolioName,
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  // ── Rebalance flow ──

  bool _rebalanceLoading = false;

  Future<void> _openRebalanceFlow() async {
    if (_rebalanceLoading) return;
    setState(() => _rebalanceLoading = true);

    try {
      final preview = await _bundleApi.previewRebalance(
        portfolioId: widget.bundle.portfolioId,
      );
      if (!mounted) return;

      if (preview.isNoAction) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Le bundle est déjà équilibré'),
            duration: Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
          ),
        );
        setState(() => _rebalanceLoading = false);
        return;
      }

      if (preview.isInvalid) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(preview.warnings.isNotEmpty
                ? preview.warnings.first
                : 'Rééquilibrage non disponible'),
            duration: const Duration(seconds: 3),
            behavior: SnackBarBehavior.floating,
          ),
        );
        setState(() => _rebalanceLoading = false);
        return;
      }

      final didRebalance = await Navigator.of(context).push<bool>(
        MaterialPageRoute(
          builder: (_) => RebalanceConfirmationScreen(
            portfolioId: widget.bundle.portfolioId,
            bundleName: _bundle?.portfolioName ?? widget.bundle.portfolioName,
            preview: preview,
          ),
        ),
      );

      if (didRebalance == true && mounted) {
        _refresh();
        _loadHeroSparkline();
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Impossible de charger le preview'),
          duration: Duration(seconds: 2),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } finally {
      if (mounted) setState(() => _rebalanceLoading = false);
    }
  }

  // ── Invest flow ──

  void _openInvestFlow() async {
    final b = _bundle!;
    final bundle = BundleItem(
      portfolioId: b.portfolioId,
      productId: b.originProductId ?? '',
      name: b.portfolioName,
      description: '',
    );
    final didInvest = await BundleInvestFlowController.start(
      context,
      bundle: bundle,
    );
    if (didInvest == true && mounted) {
      _refresh();
      _loadHeroSparkline();
    }
  }

  // ── Shared helpers ──

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

  String _formatSigned(double value) {
    final formatted = _fmt.format(value.abs());
    if (value > 0) return '+$formatted';
    if (value < 0) return '-$formatted';
    return formatted;
  }

  Color? _gainColor(double? value) {
    if (value == null || value == 0) return null;
    if (value > 0) return const Color(0xFF059669);
    return const Color(0xFFDC2626);
  }

  String _formatVolume(double balance, String asset) {
    final precision = _assetPrecision(asset);
    return '${balance.toStringAsFixed(precision)} $asset';
  }

  static int _assetPrecision(String asset) {
    switch (asset) {
      case 'BTC':
        return 8;
      case 'ETH':
        return 6;
      case 'SOL':
      case 'XRP':
      case 'ADA':
        return 4;
      default:
        return 6;
    }
  }

  static IconData _iconForAsset(String asset) {
    switch (asset) {
      case 'BTC':
        return Icons.currency_bitcoin_rounded;
      case 'ETH':
        return Icons.diamond_outlined;
      case 'SOL':
        return Icons.wb_sunny_outlined;
      case 'XRP':
        return Icons.water_drop_outlined;
      case 'ADA':
        return Icons.hexagon_outlined;
      default:
        return Icons.token_outlined;
    }
  }
}

// ─────────────── Bundle Transactions Page ───────────────

class _BundleTransactionsPage extends StatefulWidget {
  const _BundleTransactionsPage({
    required this.portfolioId,
    required this.bundleName,
  });

  final String portfolioId;
  final String bundleName;

  @override
  State<_BundleTransactionsPage> createState() =>
      _BundleTransactionsPageState();
}

class _BundleTransactionsPageState extends State<_BundleTransactionsPage> {
  final BundleApi _api = const BundleApi();
  List<BundleTransactionItem>? _transactions;
  bool _isLoading = true;
  String? _error;

  static final _eurFormatter = NumberFormat.currency(
    locale: 'fr_FR',
    symbol: '€',
    decimalDigits: 2,
  );

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final txs = await _api.getBundleTransactions(
        portfolioId: widget.portfolioId,
      );
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppBar(
        title: Text('Transactions ${widget.bundleName}'),
        backgroundColor: Colors.white,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
        scrolledUnderElevation: 1,
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline, size: 48, color: AppColors.textSecondary),
            const SizedBox(height: AppSpacing.md),
            Text(_error!, style: AppTypography.bodyMedium),
            const SizedBox(height: AppSpacing.lg),
            ElevatedButton(onPressed: _load, child: const Text('Réessayer')),
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

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.separated(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        itemCount: txs.length,
        separatorBuilder: (_, __) => const SizedBox(height: 2),
        itemBuilder: (context, index) => _buildTxTile(txs[index]),
      ),
    );
  }

  Widget _buildTxTile(BundleTransactionItem tx) {
    final isBuy = tx.side == 'buy';
    final icon = isBuy ? Icons.add_rounded : Icons.remove_rounded;
    final bgColor = isBuy ? const Color(0xFF059669) : const Color(0xFFDC2626);
    final sign = isBuy ? '+' : '-';
    final amountLabel = '$sign${tx.amountCrypto} ${tx.asset}';
    final fiatLabel = _eurFormatter.format(double.tryParse(tx.amountFiat) ?? 0);

    final now = DateTime.now();
    final diff = now.difference(tx.createdAt);
    String dateLabel;
    if (diff.inDays == 0) {
      dateLabel = "Aujourd'hui";
    } else if (diff.inDays == 1) {
      dateLabel = 'Hier';
    } else if (diff.inDays < 7) {
      dateLabel = 'Il y a ${diff.inDays} j';
    } else {
      dateLabel = DateFormat('dd/MM/yyyy', 'fr_FR').format(tx.createdAt);
    }

    return Container(
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(16),
      ),
      child: TransactionTile(
        avatar: TransactionAvatar(
          icon: icon,
          backgroundColor: bgColor.withValues(alpha: 0.12),
          iconColor: bgColor,
        ),
        title: tx.title,
        subtitle: '$fiatLabel · $dateLabel',
        rightPrimary: amountLabel,
        rightSecondaryColor: isBuy ? const Color(0xFF059669) : const Color(0xFF374151),
        rightSecondary: tx.status == 'completed' ? null : tx.status,
      ),
    );
  }
}
