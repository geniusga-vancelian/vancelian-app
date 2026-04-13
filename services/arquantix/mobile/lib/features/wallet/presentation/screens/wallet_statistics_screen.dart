import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../core/currency_preference.dart';
import '../../../../design_system/design_system.dart';
import '../../../markets/presentation/widgets/chart_asset_module.dart';
import '../../data/wallet_history_api.dart';
import '../../data/wallet_statistics_api.dart';
import '../../domain/models/wallet_statistics.dart';

class WalletStatisticsScreen extends StatefulWidget {
  const WalletStatisticsScreen({
    super.key,
    required this.asset,
    required this.assetName,
    this.portfolioScope,
    this.portfolioId,
  });

  final String asset;
  final String assetName;
  final String? portfolioScope;
  final String? portfolioId;

  @override
  State<WalletStatisticsScreen> createState() => _WalletStatisticsScreenState();
}

class _WalletStatisticsScreenState extends State<WalletStatisticsScreen> {
  final WalletStatisticsApi _statsApi = const WalletStatisticsApi();
  final WalletHistoryApi _historyApi = const WalletHistoryApi();
  final ScrollController _scrollController = ScrollController();
  double _navTitleOpacity = 0;

  WalletStatistics? _stats;
  bool _isLoading = true;
  String? _error;

  // Chart state
  List<WalletHistoryPoint> _chartPoints = [];
  List<WalletHistoryPoint> _weeklyPoints = [];
  String _selectedPeriod = 'ALL';
  bool _chartLoading = false;

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

  String get _sym => CurrencyPreference.instance.currency.symbol;

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
      final results = await Future.wait([
        _statsApi.fetchStatistics(
          widget.asset,
          portfolioScope: widget.portfolioScope,
          portfolioId: widget.portfolioId,
        ),
        _historyApi.fetchHistory(
          period: _selectedPeriod,
          asset: widget.asset,
          mode: 'performance_value',
          portfolioScope: widget.portfolioScope,
          portfolioId: widget.portfolioId,
        ),
        _historyApi.fetchHistory(
          period: '1W',
          asset: widget.asset,
          mode: 'performance_value',
          portfolioScope: widget.portfolioScope,
          portfolioId: widget.portfolioId,
        ),
      ]);
      if (!mounted) return;
      setState(() {
        _stats = results[0] as WalletStatistics;
        _chartPoints = (results[1] as WalletHistoryData).points;
        _weeklyPoints = (results[2] as WalletHistoryData).points;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _error = 'Impossible de charger les statistiques';
      });
    }
  }

  Future<void> _loadChart(String period) async {
    setState(() {
      _selectedPeriod = period;
      _chartLoading = true;
    });
    try {
      final data = await _historyApi.fetchHistory(
        period: period,
        asset: widget.asset,
        mode: 'performance_value',
        portfolioScope: widget.portfolioScope,
        portfolioId: widget.portfolioId,
      );
      if (!mounted) return;
      setState(() {
        _chartPoints = data.points;
        _chartLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _chartLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppTopNavBar(
        leadingType: AppTopNavBarLeading.back,
        title: 'Statistics',
        titleOpacity: _navTitleOpacity,
        centerTitle: false,
        titleTextStyle: AppTypography.paragraph.copyWith(
          color: AppColors.textPrimary,
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
      ),
      body: SafeArea(child: _buildBody()),
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

    final s = _stats!;
    return RefreshIndicator(
      onRefresh: _load,
      child: CustomScrollView(
        controller: _scrollController,
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          const SliverToBoxAdapter(child: SizedBox(height: AppSpacing.md)),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
              child: AppPageTitle('Statistics'),
            ),
          ),
          const SliverToBoxAdapter(child: SizedBox(height: AppSpacing.xl)),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (_weeklyPoints.length >= 2) ...[
                    _buildWeeklyGainModule(s),
                    const SizedBox(height: 16),
                  ],
                  _buildPerformanceOverview(s),
                  const SizedBox(height: 16),
                  _buildChartModule(),
                  const SizedBox(height: 16),
                  _buildTradingActivity(s),
                  const SizedBox(height: 16),
                  _buildRiskMetrics(s),
                  const SizedBox(height: 32),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ─── Weekly Gain Module ─────────────────────────────────────────

  static const _dayLabels = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];

  Widget _buildWeeklyGainModule(WalletStatistics s) {
    final pts = _weeklyPoints;
    final weekPnl = pts.last.walletValue - pts.first.walletValue;
    final isPositive = weekPnl >= 0;
    final brandColor = isPositive ? AppColors.green : AppColors.red;
    final sign = isPositive ? '+' : '';
    final amountText = '$sign${_fmt.format(weekPnl.abs())}';

    final barData = <BarChartData>[];
    for (var i = 0; i < pts.length; i++) {
      final label = i < _dayLabels.length
          ? _dayLabels[pts[i].timestamp.weekday - 1]
          : '${i + 1}';
      barData.add(BarChartData(label: label, value: pts[i].walletValue));
    }

    return ModuleGain(
      title: 'Weekly P&L',
      actionText: null,
      chartData: barData,
      amount: amountText,
      amountColor: brandColor,
      period: 'cette semaine',
      description: '${widget.assetName} — performance hebdomadaire',
      backgroundColor: brandColor,
      icon: Icon(
        isPositive ? Icons.trending_up : Icons.trending_down,
        size: 20,
        color: const Color(0xFF636366),
      ),
      valueFormatter: (v) => '${v.toStringAsFixed(2)} $_sym',
    );
  }

  // ─── Section 1: Performance Overview ────────────────────────────

  Widget _buildPerformanceOverview(WalletStatistics s) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Performance Overview'),
        const SizedBox(height: 10),
        _ModuleCard(
          child: Column(
            children: [
              _infoRow('Current Value', _fmt.format(s.currentValue)),
              _infoRow('Position', '${_fmtCrypto(s.positionSize)} ${s.asset}'),
              _infoRow('Current Price', _fmt.format(s.currentPrice)),
              _infoRow('Avg Entry (PRU)', _fmt.format(s.averageEntryPrice)),
              _infoRow(
                'Unrealized P&L',
                _fmtSigned(s.unrealizedPnl),
                valueColor: _pnlColor(s.unrealizedPnl),
              ),
              _infoRow(
                'Realized P&L',
                _fmtSigned(s.realizedPnl),
                valueColor: _pnlColor(s.realizedPnl),
              ),
              _infoRow(
                'Total P&L',
                _fmtSigned(s.totalPnl),
                valueColor: _pnlColor(s.totalPnl),
                isLast: true,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _infoRow(String label, String value, {Color? valueColor, bool isLast = false}) {
    return Padding(
      padding: EdgeInsets.only(bottom: isLast ? 0 : 14),
      child: Row(
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
      ),
    );
  }

  // ─── Section 2: Chart (aligned with instrument ChartAssetModule) ──

  static const double _chartRightMargin = 24.0;
  static const double _chartBottomMargin = 24.0;
  static const double _chartHeightBase = 212.0;
  static const double _chartTotalHeight = _chartHeightBase + _chartBottomMargin;
  static const double _periodChipHeight = 36.0;
  static const List<String> _periodLabels = ['1D', '1W', '1M', 'ALL'];
  static const List<String> _periodCaptions = [
    '1 jour', '1 semaine', '1 mois', 'Tout',
  ];

  int get _periodIndex => _periodLabels.indexOf(_selectedPeriod).clamp(0, 3);

  List<double> get _chartValues {
    if (_chartPoints.isEmpty) return [];
    return _chartPoints.map((p) => p.walletValue).toList();
  }

  Widget _buildChartModule() {
    final values = _chartValues;
    final brandColor =
        AppColors.cryptoAssetBrand[widget.asset] ?? AppColors.accent;

    final lastVal = values.isNotEmpty ? values.last : 0.0;
    final isPositive = lastVal >= 0;
    final perfColor = isPositive
        ? const Color(0xFF059669)
        : const Color(0xFFDC2626);

    final headerValue = _fmtSigned(lastVal);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Historical Performance'),
        const SizedBox(height: 10),

        _ModuleCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (values.isNotEmpty) ...[
                Text(
                  headerValue,
                  style: AppTypography.amountLarge.copyWith(
                    color: perfColor,
                    fontWeight: FontWeight.w900,
                    fontSize: 24,
                    height: 1.0,
                  ),
                ),
                const SizedBox(height: 2),
                Row(
                  children: [
                    Icon(
                      isPositive ? Icons.arrow_drop_up : Icons.arrow_drop_down,
                      color: perfColor,
                      size: 20,
                    ),
                    Text(
                      _periodCaptions[_periodIndex],
                      style: AppTypography.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.md),
              ],

              // Chart area
              SizedBox(
                height: _chartTotalHeight,
                child: _chartLoading
                    ? const SizedBox.expand()
                    : values.length < 2
                        ? Center(
                            child: Text(
                              'No data',
                              style: AppTypography.bodySmall.copyWith(
                                color: AppColors.textSecondary,
                              ),
                            ),
                          )
                        : _WalletChartEntranceAnimation(
                            key: ValueKey('wsc-$_selectedPeriod'),
                            child: LayoutBuilder(
                              builder: (context, constraints) {
                                final size = Size(
                                  constraints.maxWidth,
                                  constraints.maxHeight,
                                );
                                final geo = _computeChartGeometry(values, size);
                                return Stack(
                                  clipBehavior: Clip.none,
                                  children: [
                                    Positioned.fill(
                                      child: CustomPaint(
                                        painter: _WalletLinePainter(
                                          accent: brandColor,
                                          points: geo.points,
                                          startY: geo.startY,
                                        ),
                                      ),
                                    ),
                                    Positioned(
                                      left: 0,
                                      top: geo.startY + 6,
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(
                                          horizontal: AppSpacing.sm,
                                          vertical: AppSpacing.xs,
                                        ),
                                        decoration: BoxDecoration(
                                          color: AppColors.pageBackground,
                                          borderRadius: BorderRadius.circular(12),
                                        ),
                                        child: Text(
                                          geo.startLabel,
                                          style: AppTypography.meta.copyWith(
                                            color: AppColors.textPrimary,
                                            fontWeight: FontWeight.w500,
                                          ),
                                        ),
                                      ),
                                    ),
                                    Positioned(
                                      left: geo.lastPoint.dx -
                                          ChartSonarPoint.size / 2,
                                      top: geo.lastPoint.dy -
                                          ChartSonarPoint.size / 2,
                                      child: ChartSonarPoint(color: brandColor),
                                    ),
                                  ],
                                );
                              },
                            ),
                          ),
              ),
              const SizedBox(height: AppSpacing.md),

              // Period chips inside card
              _buildPeriodChips(),
            ],
          ),
        ),
      ],
    );
  }

  _WalletChartGeo _computeChartGeometry(List<double> values, Size size) {
    if (values.isEmpty) {
      return const _WalletChartGeo(
        points: [],
        startY: 0,
        lastPoint: Offset.zero,
        startLabel: '—',
      );
    }
    final mn = values.reduce(math.min);
    final mx = values.reduce(math.max);
    final range = (mx - mn).abs() < 1e-9 ? 1.0 : (mx - mn);
    const paddingTop = 16.0;
    final paddingBottom = 16.0 + _chartBottomMargin;
    final usableHeight = math.max(1.0, size.height - paddingTop - paddingBottom);
    final usableWidth = math.max(1.0, size.width - _chartRightMargin);

    final points = <Offset>[];
    for (var i = 0; i < values.length; i++) {
      final x =
          values.length == 1 ? 0.0 : usableWidth * (i / (values.length - 1));
      final normalized = (values[i] - mn) / range;
      final y = paddingTop + (1 - normalized) * usableHeight;
      points.add(Offset(x, y));
    }

    final first = values.first;
    final startLabel = first.abs() < 1
        ? '${first.toStringAsFixed(4).replaceAll('.', ',')} $_sym'
        : '${first.toStringAsFixed(2).replaceAll('.', ',')} $_sym';
    return _WalletChartGeo(
      points: points,
      startY: points.first.dy,
      lastPoint: points.last,
      startLabel: startLabel,
    );
  }

  Widget _buildPeriodChips() {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.xs),
      decoration: BoxDecoration(
        color: AppColors.pageBackground,
        borderRadius: BorderRadius.circular(999),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final segmentWidth = constraints.maxWidth / _periodLabels.length;
          return SizedBox(
            height: _periodChipHeight,
            child: Stack(
              children: [
                AnimatedPositioned(
                  duration: const Duration(milliseconds: 220),
                  curve: Curves.easeOutCubic,
                  left: _periodIndex * segmentWidth,
                  top: 0,
                  width: segmentWidth,
                  height: _periodChipHeight,
                  child: Container(
                    decoration: BoxDecoration(
                      color: AppColors.cardBackground,
                      borderRadius: BorderRadius.circular(999),
                    ),
                  ),
                ),
                Row(
                  children: [
                    for (int i = 0; i < _periodLabels.length; i++)
                      Expanded(
                        child: GestureDetector(
                          behavior: HitTestBehavior.opaque,
                          onTap: () => _loadChart(_periodLabels[i]),
                          child: Center(
                            child: Text(
                              _periodLabels[i],
                              style: AppTypography.bodyMedium.copyWith(
                                color: AppColors.textPrimary,
                                fontWeight: _periodIndex == i
                                    ? FontWeight.w700
                                    : FontWeight.w500,
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
        },
      ),
    );
  }

  // ─── Section 3: Trading Activity ────────────────────────────────

  Widget _buildTradingActivity(WalletStatistics s) {
    final dateFormat = DateFormat('dd MMM yyyy', 'fr_FR');
    String firstTrade = '—';
    String lastTrade = '—';
    if (s.firstTradeAt != null) {
      firstTrade = dateFormat.format(s.firstTradeAt!);
    }
    if (s.lastTradeAt != null) {
      final diff = DateTime.now().difference(s.lastTradeAt!);
      if (diff.inDays == 0) {
        lastTrade = "Aujourd'hui";
      } else if (diff.inDays == 1) {
        lastTrade = 'Hier';
      } else {
        lastTrade = dateFormat.format(s.lastTradeAt!);
      }
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Trading Activity'),
        const SizedBox(height: 10),
        _ModuleCard(
          child: Column(
            children: [
              _infoRow('First Trade', firstTrade),
              _infoRow('Last Trade', lastTrade),
              _infoRow('Total Trades', '${s.tradeCount}'),
              _infoRow('Buys / Sells', '${s.buyCount} / ${s.sellCount}'),
              _infoRow('Total Bought', '${_fmtCrypto(s.totalBought)} ${s.asset}'),
              _infoRow('Total Sold', '${_fmtCrypto(s.totalSold)} ${s.asset}'),
              _infoRow('Avg Buy Price', _fmt.format(s.avgBuyPrice)),
              _infoRow(
                'Avg Sell Price',
                s.avgSellPrice != null ? _fmt.format(s.avgSellPrice!) : '—',
                isLast: true,
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ─── Section 4: Risk Metrics ────────────────────────────────────

  Widget _buildRiskMetrics(WalletStatistics s) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Position Quality & Risk'),
        const SizedBox(height: 10),
        _ModuleCard(
          child: Column(
            children: [
              _infoRow('Position Age', '${s.positionAgeDays} days'),
              _infoRow(
                'Break-even Distance',
                s.breakEvenDistancePct != null
                    ? '${s.breakEvenDistancePct! >= 0 ? '+' : ''}${s.breakEvenDistancePct!.toStringAsFixed(1)}%'
                    : '—',
                valueColor: s.breakEvenDistancePct != null
                    ? _pnlColor(s.breakEvenDistancePct!)
                    : null,
              ),
              _infoRow(
                '30d Volatility',
                s.volatility30d != null
                    ? '${(s.volatility30d! * 100).toStringAsFixed(1)}%'
                    : '—',
              ),
              _infoRow(
                'Max Drawdown',
                s.maxDrawdown != null
                    ? '${(s.maxDrawdown! * 100).toStringAsFixed(1)}%'
                    : '—',
                valueColor:
                    s.maxDrawdown != null ? const Color(0xFFDC2626) : null,
              ),
              _infoRow(
                'Portfolio Weight',
                s.portfolioWeight != null
                    ? '${(s.portfolioWeight! * 100).toStringAsFixed(1)}%'
                    : '—',
                isLast: true,
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ─── Helpers ────────────────────────────────────────────────────

  String _fmtSigned(double v) {
    final formatted = _fmt.format(v.abs());
    if (v > 0) return '+$formatted';
    if (v < 0) return '-$formatted';
    return formatted;
  }

  String _fmtCrypto(double v) {
    if (v >= 1) return v.toStringAsFixed(4);
    if (v >= 0.001) return v.toStringAsFixed(6);
    return v.toStringAsFixed(8);
  }

  Color? _pnlColor(double v) {
    if (v > 0) return const Color(0xFF059669);
    if (v < 0) return const Color(0xFFDC2626);
    return null;
  }
}

// ─── Reusable sub-widgets ──────────────────────────────────────────

class _ModuleCard extends StatelessWidget {
  const _ModuleCard({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
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
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
        child: child,
      ),
    );
  }
}

// ─── Chart geometry & painters (matching instrument ChartAssetModule) ───

class _WalletChartGeo {
  const _WalletChartGeo({
    required this.points,
    required this.startY,
    required this.lastPoint,
    required this.startLabel,
  });
  final List<Offset> points;
  final double startY;
  final Offset lastPoint;
  final String startLabel;
}

class _WalletLinePainter extends CustomPainter {
  _WalletLinePainter({
    required this.accent,
    required this.points,
    required this.startY,
  });

  final Color accent;
  final List<Offset> points;
  final double startY;

  @override
  void paint(Canvas canvas, Size size) {
    if (points.isEmpty) return;

    // Dashed horizontal line at start level
    final yStart = startY.clamp(0, size.height).toDouble();
    final dotted = Paint()
      ..color = AppColors.textSecondary.withValues(alpha: 0.55)
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    const dashWidth = 2.2;
    const gap = 5.0;
    var x = 0.0;
    while (x < size.width) {
      final x2 = math.min(x + dashWidth, size.width).toDouble();
      canvas.drawLine(Offset(x, yStart), Offset(x2, yStart), dotted);
      x += dashWidth + gap;
    }

    // Smooth Catmull-Rom line
    final paint = Paint()
      ..color = accent
      ..strokeWidth = 2.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    final clamped = <Offset>[
      for (final p in points)
        Offset(
          p.dx.clamp(0, size.width).toDouble(),
          p.dy.clamp(0, size.height).toDouble(),
        ),
    ];
    final path = Path()..moveTo(clamped[0].dx, clamped[0].dy);
    if (clamped.length == 2) {
      path.lineTo(clamped[1].dx, clamped[1].dy);
    } else {
      for (var i = 0; i < clamped.length - 1; i++) {
        final p0 = clamped[i > 0 ? i - 1 : i];
        final p1 = clamped[i];
        final p2 = clamped[i + 1];
        final p3 = clamped[i + 1 < clamped.length - 1 ? i + 2 : i + 1];
        final c1 = i == 0
            ? p1
            : Offset(p1.dx + (p2.dx - p0.dx) / 6, p1.dy + (p2.dy - p0.dy) / 6);
        final c2 = i == clamped.length - 2
            ? p2
            : Offset(p2.dx - (p3.dx - p1.dx) / 6, p2.dy - (p3.dy - p1.dy) / 6);
        path.cubicTo(c1.dx, c1.dy, c2.dx, c2.dy, p2.dx, p2.dy);
      }
    }
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _WalletLinePainter old) =>
      old.accent != accent ||
      old.startY != startY ||
      old.points.length != points.length ||
      (points.isNotEmpty && old.points.isNotEmpty && old.points.last != points.last);
}

class _WalletChartEntranceAnimation extends StatefulWidget {
  const _WalletChartEntranceAnimation({super.key, required this.child});
  final Widget child;

  @override
  State<_WalletChartEntranceAnimation> createState() =>
      _WalletChartEntranceAnimationState();
}

class _WalletChartEntranceAnimationState
    extends State<_WalletChartEntranceAnimation>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _reveal;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 320),
    );
    _reveal = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic),
    );
    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _reveal,
      builder: (context, child) {
        return ClipRect(
          child: Align(
            alignment: Alignment.centerLeft,
            widthFactor: _reveal.value,
            child: widget.child,
          ),
        );
      },
    );
  }
}
