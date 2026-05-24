import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../core/config.dart';
import '../../../../core/currency_preference.dart';
import '../../../../design_system/design_system.dart';
import '../../../../ui/components/line_chart_module.dart';
import '../../data/bundle_api.dart';
import 'bundle_wallet_detail_screen.dart';
import '../../data/crypto_positions_api.dart';
import '../../data/wallet_history_api.dart';
import '../../domain/models/crypto_positions_data.dart';
import 'buy_flow/buy_flow_controller.dart';
import 'crypto_wallet_detail_screen.dart';
import 'portfolio_statistics_screen.dart';
import 'lifi_swap_flow/lifi_swap_controller.dart';
import 'sell_all_flow/sell_all_confirmation_screen.dart';

class AllCryptoPositionsScreen extends StatefulWidget {
  const AllCryptoPositionsScreen({super.key});

  @override
  State<AllCryptoPositionsScreen> createState() =>
      _AllCryptoPositionsScreenState();
}

class _AllCryptoPositionsScreenState extends State<AllCryptoPositionsScreen> {
  final CryptoPositionsApi _api = const CryptoPositionsApi();
  final WalletHistoryApi _historyApi = const WalletHistoryApi();
  final BundleApi _bundleApi = const BundleApi();

  CryptoPositionsData? _data;
  List<MyBundleSummary> _myBundles = const [];
  bool _isLoading = true;
  String? _loadError;
  List<double>? _heroSparkline;

  @override
  void initState() {
    super.initState();
    _load();
    _loadHeroSparkline();
  }

  void _openLifiSwap() async {
    final didSwap = await LifiSwapController.start(context);
    if (didSwap == true && mounted) {
      _load(forceRefresh: true);
      _loadHeroSparkline();
    }
  }

  void _openBuyFlow() async {
    final didBuy = await BuyFlowController.startWithoutTarget(context);
    if (didBuy == true && mounted) {
      _load(forceRefresh: true);
      _loadHeroSparkline();
    }
  }

  void _openSellAllFlow() async {
    final didSell = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => const SellAllConfirmationScreen(),
      ),
    );
    if (didSell == true && mounted) {
      _load(forceRefresh: true);
      _loadHeroSparkline();
    }
  }

  Future<void> _loadHeroSparkline() async {
    try {
      final data = await _historyApi.fetchHistory(
        period: 'ALL',
        mode: 'performance_value',
        scope: 'crypto',
      );
      if (!mounted || data.points.isEmpty) return;
      final values = data.points.map((p) => p.walletValue).toList();
      setState(() => _heroSparkline = values);
    } catch (_) {}
  }

  Future<void> _load({bool forceRefresh = false}) async {
    setState(() {
      _isLoading = true;
      _loadError = null;
    });
    try {
      final results = await Future.wait([
        _api.fetchDirectPositions().catchError((_) => _api.fetchPositions()),
        _bundleApi.getMyBundles().catchError((_) => <MyBundleSummary>[]),
      ]);
      if (!mounted) return;
      setState(() {
        _data = results[0] as CryptoPositionsData;
        _myBundles = results[1] as List<MyBundleSummary>;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _loadError = 'Impossible de charger les positions crypto';
      });
    }
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
    if (_isLoading) return const _CryptoShimmer();

    if (_loadError != null) {
      return Scaffold(
        backgroundColor: AppColors.pageBackground,
        appBar: AppBar(
          title: const Text('Crypto'),
          backgroundColor: const Color(0xFF0D1B2A),
          foregroundColor: Colors.white,
        ),
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, size: 48, color: AppColors.textSecondary),
              const SizedBox(height: AppSpacing.md),
              Text(_loadError!, style: AppTypography.bodyMedium),
              const SizedBox(height: AppSpacing.lg),
              AppPrimaryButton(
                label: 'Réessayer',
                variant: AppPrimaryButtonVariant.black,
                size: AppPrimaryButtonSize.medium,
                shrinkWrap: true,
                onPressed: _load,
              ),
            ],
          ),
        ),
      );
    }

    return _buildPage();
  }

  Widget _buildPage() {
    final data = _data!;
    final pref = CurrencyPreference.instance;
    final directValue = pref.selectValue(eur: data.totalValueEur, usd: data.totalValueUsd) ?? 0;
    final bundleValue = _myBundles
        .where((b) => b.hasHoldings && b.totalMarketValue != null)
        .fold<double>(0, (sum, b) => sum + (b.totalMarketValue ?? 0));
    final totalValue = directValue + bundleValue;
    final totalLabel = _activeFormatter.format(totalValue);
    final activeBundleCount = _myBundles.where((b) => b.hasHoldings).length;
    final countLabel = activeBundleCount > 0
        ? '${data.positionsCount} crypto${data.positionsCount > 1 ? 's' : ''} · $activeBundleCount bundle${activeBundleCount > 1 ? 's' : ''}'
        : '${data.positionsCount} crypto-actif${data.positionsCount > 1 ? 's' : ''}';

    final activeBundles = _myBundles.where((b) => b.hasHoldings).toList();

    // Build a unified list of wallet rows sorted by value (descending)
    final List<_WalletRow> rows = [];
    for (final pos in data.positions) {
      final v = pref.selectValue(eur: pos.estimatedValueEur, usd: pos.estimatedValueUsd) ?? 0;
      rows.add(_WalletRow(value: v, cryptoPosition: pos));
    }
    for (final b in activeBundles) {
      final v = b.totalMarketValue ?? b.totalCostBasis;
      rows.add(_WalletRow(value: v, bundle: b));
    }
    rows.sort((a, b) => b.value.compareTo(a.value));

    final List<Widget> contentModules = [];

    if (rows.isEmpty) {
      contentModules.add(
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: AppSpacing.xxl * 1.5),
            decoration: BoxDecoration(
              color: AppColors.cardBackground,
              borderRadius: BorderRadius.circular(AppRadius.lg),
              boxShadow: AppShadow.defaultShadowList,
            ),
            child: Center(
              child: Text(
                'Aucune position crypto pour le moment',
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.textSecondary,
                ),
                textAlign: TextAlign.center,
              ),
            ),
          ),
        ),
      );
    } else {
      contentModules.add(
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: TransactionListCard(
            items: rows.map((row) {
              if (row.bundle != null) return _buildBundleItem(row.bundle!);
              return _buildPositionItem(row.cryptoPosition!);
            }).toList(),
          ),
        ),
      );
    }

    return LayoutPageLevel1(
      heroHeightFraction: 0.65,
      heroFallbackColor: const Color(0xFF0D1B2A),
      heroOverlay: const HeroOverlayConfig(
        tintOpacity: 0,
        gradientStartOpacity: 0.60,
        gradientEndOpacity: 0,
      ),
      title: 'Crypto',
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
      heroActionsBelowFullBleed: CircleButtonRow(
        items: [
          CircleButtonItem(
            icon: Icons.swap_horiz_rounded,
            label: 'Echanger',
            onTap: _openLifiSwap,
            isPrimary: true,
          ),
          CircleButtonItem(
            icon: Icons.add,
            label: 'Déposer',
            onTap: () {},
          ),
          CircleButtonItem(
            icon: Icons.arrow_forward_rounded,
            label: 'Transférer',
            onTap: () {},
          ),
          CircleButtonItem(
            icon: Icons.sell_rounded,
            label: 'Tout vendre',
            onTap: _openSellAllFlow,
          ),
        ],
      ),
      heroActions: Text(
        countLabel,
        style: AppTypography.bodySmall.copyWith(
          color: Colors.white70,
        ),
        textAlign: TextAlign.center,
      ),
      leadingType: AppTopNavBarLeading.back,
      onLeadingTap: () => Navigator.of(context).pop(),
      navBarActions: [
        AppTopNavBarAction(
          icon: Icons.bar_chart_rounded,
          onPressed: () {
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => const PortfolioStatisticsScreen(),
              ),
            );
          },
        ),
      ],
      onRefresh: () {
        _loadHeroSparkline();
        return _load(forceRefresh: true);
      },
      content: contentModules,
    );
  }

  TransactionListItemData _buildBundleItem(MyBundleSummary bundle) {
    final fmt = _activeFormatter;
    final marketValue = bundle.totalMarketValue;
    final valueLabel = marketValue != null ? fmt.format(marketValue) : fmt.format(bundle.totalCostBasis);

    String? perfLabel;
    Color? perfColor;
    if (bundle.performancePct != null) {
      final pct = bundle.performancePct!;
      perfLabel = '${pct >= 0 ? '+' : ''}${pct.toStringAsFixed(2)} %';
      perfColor = pct > 0 ? AppColors.green : pct < 0 ? AppColors.red : AppColors.textSecondary;
    }

    final spotAssets = bundle.spotPositions;
    final subtitle = '${spotAssets.length} actif${spotAssets.length > 1 ? 's' : ''}';

    return TransactionListItemData(
      leadingWidget: const IconContainer(
        size: IconContainerSize.md,
        backgroundColor: Color(0xFF6366F1),
        child: Icon(Icons.pie_chart_rounded, size: 20, color: Colors.white),
      ),
      title: bundle.portfolioName,
      subtitle: subtitle,
      amount: valueLabel,
      secondaryAmount: perfLabel,
      secondaryAmountColor: perfColor,
      onTap: () => _openBundleDetail(bundle),
    );
  }

  void _openBundleDetail(MyBundleSummary bundle) {
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) => BundleWalletDetailScreen(bundle: bundle),
      ),
    ).then((_) {
      if (mounted) _load(forceRefresh: true);
    });
  }

  // ── Crypto position item ──

  TransactionListItemData _buildPositionItem(CryptoPositionItem pos) {
    final pref = CurrencyPreference.instance;
    final value = pref.selectValue(eur: pos.estimatedValueEur, usd: pos.estimatedValueUsd);
    final valueLabel = value != null ? _activeFormatter.format(value) : '—';

    final volumeStr = _formatVolume(pos.balance, pos.asset);
    final privyHint = pos.isPrivyOnly
        ? 'Wallet Privy · $volumeStr'
        : pos.portfolioScope == 'merged'
            ? '$volumeStr · incl. Privy'
            : volumeStr;

    String? perfLabel;
    Color? perfColor;
    if (pos.performance1dPct != null) {
      final pct = pos.performance1dPct!;
      perfLabel = '${pct >= 0 ? '+' : ''}${pct.toStringAsFixed(2)} %';
      perfColor = pct > 0 ? AppColors.green : pct < 0 ? AppColors.red : AppColors.textSecondary;
    }

    final logoKey = pos.iconKey.trim().isNotEmpty
        ? pos.iconKey.trim().toLowerCase()
        : pos.asset.trim().toLowerCase();
    final logoUrl = logoKey.isNotEmpty
        ? Config.resolveLogoUrl('/media/crypto_logos/$logoKey.png')
        : null;

    return TransactionListItemData(
      leadingWidget: CryptoAvatar(
        ticker: pos.asset,
        logoUrl: logoUrl,
        fallbackIcon: _iconForAsset(pos.asset),
      ),
      title: pos.name,
      subtitle: privyHint,
      amount: valueLabel,
      secondaryAmount: perfLabel,
      secondaryAmountColor: perfColor,
      onTap: () {
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => CryptoWalletDetailScreen(
              asset: pos.asset,
              assetName: pos.name,
            ),
          ),
        );
      },
    );
  }

  String _formatVolume(double balance, String asset) {
    final precision = _assetPrecisionDisplay(asset);
    return '${balance.toStringAsFixed(precision)} $asset';
  }

  static int _assetPrecisionDisplay(String asset) {
    switch (asset) {
      case 'BTC':
        return 8;
      case 'ETH':
        return 6;
      case 'SOL':
        return 4;
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


class _WalletRow {
  const _WalletRow({required this.value, this.cryptoPosition, this.bundle});
  final double value;
  final CryptoPositionItem? cryptoPosition;
  final MyBundleSummary? bundle;
}

// ─────────────── Shimmer Loading ───────────────

class _CryptoShimmer extends StatefulWidget {
  const _CryptoShimmer();

  @override
  State<_CryptoShimmer> createState() => _CryptoShimmerState();
}

class _CryptoShimmerState extends State<_CryptoShimmer>
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
    final topPad = MediaQuery.paddingOf(context).top;
    final heroHeight = screen.height * 0.65;

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      body: AnimatedBuilder(
        animation: _animation,
        builder: (context, _) {
          return SingleChildScrollView(
            physics: const NeverScrollableScrollPhysics(),
            child: Column(
              children: [
                _buildHeroShimmer(heroHeight, topPad, screen.width),
                Transform.translate(
                  offset: const Offset(0, -AppSpacing.lg),
                  child: _buildContentShimmer(),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildHeroShimmer(double height, double topPad, double width) {
    return Container(
      width: width,
      height: height,
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
            _shimmerRect(width: 80, height: 28, light: true, radius: 8),
            const SizedBox(height: AppSpacing.md),
            _shimmerRect(width: 200, height: 32, light: true, radius: 8),
            const SizedBox(height: AppSpacing.lg),
            _shimmerRect(width: 120, height: 14, light: true, radius: 6),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }

  Widget _buildContentShimmer() {
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
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          children: List.generate(4, (i) => _buildRowShimmer(i)),
        ),
      ),
    );
  }

  Widget _buildRowShimmer(int index) {
    final widths = [100.0, 90.0, 110.0, 95.0];
    final subWidths = [140.0, 120.0, 130.0, 110.0];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          _shimmerCircle(44, light: false),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _shimmerRect(
                  width: widths[index % widths.length],
                  height: 14,
                  light: false,
                  radius: 4,
                ),
                const SizedBox(height: 6),
                _shimmerRect(
                  width: subWidths[index % subWidths.length],
                  height: 12,
                  light: false,
                  radius: 4,
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              _shimmerRect(width: 72, height: 14, light: false, radius: 4),
              const SizedBox(height: 6),
              _shimmerRect(width: 60, height: 12, light: false, radius: 4),
            ],
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
