import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../core/currency_preference.dart';
import '../../../../design_system/design_system.dart';
import '../../../markets/presentation/widgets/chart_asset_module.dart';
import '../../data/bundle_api.dart';
import '../../data/wallet_history_api.dart';

class BundleStatisticsScreen extends StatefulWidget {
  const BundleStatisticsScreen({
    super.key,
    required this.portfolioId,
    required this.portfolioName,
  });

  final String portfolioId;
  final String portfolioName;

  @override
  State<BundleStatisticsScreen> createState() => _BundleStatisticsScreenState();
}

class _BundleStatisticsScreenState extends State<BundleStatisticsScreen> {
  final BundleApi _bundleApi = const BundleApi();
  final WalletHistoryApi _historyApi = const WalletHistoryApi();
  final ScrollController _scrollController = ScrollController();
  double _navTitleOpacity = 0;

  BundlePortfolioStatistics? _stats;
  bool _isLoading = true;
  String? _error;

  List<WalletHistoryPoint> _chartPoints = [];
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
        _bundleApi.getBundlePortfolioStatistics(portfolioId: widget.portfolioId),
        _historyApi.fetchHistory(
          period: _selectedPeriod,
          mode: 'performance_value',
          portfolioScope: 'bundle',
          portfolioId: widget.portfolioId,
        ),
      ]);
      if (!mounted) return;
      setState(() {
        _stats = results[0] as BundlePortfolioStatistics;
        _chartPoints = (results[1] as WalletHistoryData).points;
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
        mode: 'performance_value',
        portfolioScope: 'bundle',
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
                  _buildPerformance(s),
                  const SizedBox(height: 16),
                  _buildChartModule(),
                  const SizedBox(height: 16),
                  _buildAllocationVsTarget(s),
                  const SizedBox(height: 16),
                  _buildContributions(s),
                  const SizedBox(height: 16),
                  _buildCashDeployment(s),
                  const SizedBox(height: 16),
                  _buildActivity(s),
                  const SizedBox(height: 16),
                  _buildRisk(s),
                  const SizedBox(height: 32),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ─── Performance ─────────────────────────────────────────────────

  Widget _buildPerformance(BundlePortfolioStatistics s) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Performance'),
        const SizedBox(height: 10),
        _ModuleCard(
          child: Column(
            children: [
              _infoRow('Valeur actuelle', _fmt.format(s.currentValue)),
              _infoRow('Total investi', _fmt.format(s.totalInvested)),
              _infoRow(
                'P&L total',
                _fmtSigned(s.totalPnl),
                valueColor: _pnlColor(s.totalPnl),
              ),
              _infoRow(
                'Performance',
                '${s.performancePct >= 0 ? '+' : ''}${s.performancePct.toStringAsFixed(2)}%',
                valueColor: _pnlColor(s.performancePct),
                isLast: true,
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ─── Chart ───────────────────────────────────────────────────────

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
    const brandColor = AppColors.accent;

    final lastVal = values.isNotEmpty ? values.last : 0.0;
    final isPositive = lastVal >= 0;
    final perfColor = isPositive
        ? const Color(0xFF059669)
        : const Color(0xFFDC2626);

    final headerValue = _fmtSigned(lastVal);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Performance historique'),
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
              SizedBox(
                height: _chartTotalHeight,
                child: _chartLoading
                    ? const SizedBox.expand()
                    : values.length < 2
                        ? Center(
                            child: Text(
                              'Pas de données',
                              style: AppTypography.bodySmall.copyWith(
                                color: AppColors.textSecondary,
                              ),
                            ),
                          )
                        : _ChartEntranceAnimation(
                            key: ValueKey('bsc-$_selectedPeriod'),
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
                                        painter: _LinePainter(
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
              _buildPeriodChips(),
            ],
          ),
        ),
      ],
    );
  }

  _ChartGeo _computeChartGeometry(List<double> values, Size size) {
    if (values.isEmpty) {
      return const _ChartGeo(
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

    final sym = CurrencyPreference.instance.currency.symbol;
    final first = values.first;
    final startLabel = first.abs() < 1
        ? '${first.toStringAsFixed(4).replaceAll('.', ',')} $sym'
        : '${first.toStringAsFixed(2).replaceAll('.', ',')} $sym';
    return _ChartGeo(
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

  // ─── Allocation vs Target ────────────────────────────────────────

  Widget _buildAllocationVsTarget(BundlePortfolioStatistics s) {
    if (s.allocationVsTarget.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Allocation vs Cible'),
        const SizedBox(height: 10),
        _ModuleCard(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Row(
                  children: [
                    Expanded(
                      flex: 3,
                      child: Text('Actif', style: AppTypography.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                        fontWeight: FontWeight.w600,
                      )),
                    ),
                    Expanded(
                      flex: 2,
                      child: Text('Cible', textAlign: TextAlign.right,
                          style: AppTypography.bodySmall.copyWith(
                            color: AppColors.textSecondary,
                            fontWeight: FontWeight.w600,
                          )),
                    ),
                    Expanded(
                      flex: 2,
                      child: Text('Réelle', textAlign: TextAlign.right,
                          style: AppTypography.bodySmall.copyWith(
                            color: AppColors.textSecondary,
                            fontWeight: FontWeight.w600,
                          )),
                    ),
                    Expanded(
                      flex: 2,
                      child: Text('Drift', textAlign: TextAlign.right,
                          style: AppTypography.bodySmall.copyWith(
                            color: AppColors.textSecondary,
                            fontWeight: FontWeight.w600,
                          )),
                    ),
                  ],
                ),
              ),
              for (int i = 0; i < s.allocationVsTarget.length; i++)
                _allocationRow(s.allocationVsTarget[i], isLast: i == s.allocationVsTarget.length - 1),
            ],
          ),
        ),
      ],
    );
  }

  Widget _allocationRow(AllocationVsTarget a, {bool isLast = false}) {
    return Padding(
      padding: EdgeInsets.only(bottom: isLast ? 0 : 12),
      child: Row(
        children: [
          Expanded(
            flex: 3,
            child: Text(a.asset, style: AppTypography.bodyMedium.copyWith(
              fontWeight: FontWeight.w600,
            )),
          ),
          Expanded(
            flex: 2,
            child: Text(
              '${a.targetPct.toStringAsFixed(1)}%',
              textAlign: TextAlign.right,
              style: AppTypography.bodyMedium,
            ),
          ),
          Expanded(
            flex: 2,
            child: Text(
              '${a.currentPct.toStringAsFixed(1)}%',
              textAlign: TextAlign.right,
              style: AppTypography.bodyMedium,
            ),
          ),
          Expanded(
            flex: 2,
            child: Text(
              '${a.driftPct >= 0 ? '+' : ''}${a.driftPct.toStringAsFixed(1)}%',
              textAlign: TextAlign.right,
              style: AppTypography.bodyMedium.copyWith(
                color: _driftColor(a.driftPct),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ─── Contribution à la performance ───────────────────────────────

  Widget _buildContributions(BundlePortfolioStatistics s) {
    if (s.contributions.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Contribution à la performance'),
        const SizedBox(height: 10),
        _ModuleCard(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Row(
                  children: [
                    Expanded(
                      flex: 3,
                      child: Text('Actif', style: AppTypography.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                        fontWeight: FontWeight.w600,
                      )),
                    ),
                    Expanded(
                      flex: 3,
                      child: Text('P&L', textAlign: TextAlign.right,
                          style: AppTypography.bodySmall.copyWith(
                            color: AppColors.textSecondary,
                            fontWeight: FontWeight.w600,
                          )),
                    ),
                    Expanded(
                      flex: 2,
                      child: Text('Contrib.', textAlign: TextAlign.right,
                          style: AppTypography.bodySmall.copyWith(
                            color: AppColors.textSecondary,
                            fontWeight: FontWeight.w600,
                          )),
                    ),
                  ],
                ),
              ),
              for (int i = 0; i < s.contributions.length; i++)
                _contributionRow(s.contributions[i], isLast: i == s.contributions.length - 1),
            ],
          ),
        ),
      ],
    );
  }

  Widget _contributionRow(AssetContribution c, {bool isLast = false}) {
    return Padding(
      padding: EdgeInsets.only(bottom: isLast ? 0 : 12),
      child: Row(
        children: [
          Expanded(
            flex: 3,
            child: Text(c.asset, style: AppTypography.bodyMedium.copyWith(
              fontWeight: FontWeight.w600,
            )),
          ),
          Expanded(
            flex: 3,
            child: Text(
              _fmtSigned(c.pnl),
              textAlign: TextAlign.right,
              style: AppTypography.bodyMedium.copyWith(
                color: _pnlColor(c.pnl),
              ),
            ),
          ),
          Expanded(
            flex: 2,
            child: Text(
              '${c.contributionPct.toStringAsFixed(1)}%',
              textAlign: TextAlign.right,
              style: AppTypography.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }

  // ─── Cash & Deployment ───────────────────────────────────────────

  Widget _buildCashDeployment(BundlePortfolioStatistics s) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Déploiement du capital'),
        const SizedBox(height: 10),
        _ModuleCard(
          child: Column(
            children: [
              _infoRow(
                'Investi',
                '${s.investedPct.toStringAsFixed(1)}%',
              ),
              _infoRow(
                'Cash',
                '${s.cashPct.toStringAsFixed(1)}%',
              ),
              _infoRow(
                'Valeur cash',
                _fmt.format(s.cashValue),
                isLast: true,
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ─── Activity ────────────────────────────────────────────────────

  Widget _buildActivity(BundlePortfolioStatistics s) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Activité'),
        const SizedBox(height: 10),
        _ModuleCard(
          child: Column(
            children: [
              _infoRow('Rééquilibrages', '${s.rebalanceCount}'),
              _infoRow(
                'Événements d\'allocation',
                '${s.totalAllocationEvents}',
                isLast: true,
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ─── Risk ────────────────────────────────────────────────────────

  Widget _buildRisk(BundlePortfolioStatistics s) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Risque'),
        const SizedBox(height: 10),
        _ModuleCard(
          child: Column(
            children: [
              _infoRow('Nombre d\'actifs', '${s.assetsCount}'),
              _infoRow(
                'Concentration max',
                s.concentrationAsset != null
                    ? '${s.concentrationAsset} (${s.concentrationPct.toStringAsFixed(1)}%)'
                    : '—',
              ),
              _infoRow('Volatilité 30j', '—'),
              _infoRow('Max drawdown', '—', isLast: true),
            ],
          ),
        ),
      ],
    );
  }

  // ─── Helpers ─────────────────────────────────────────────────────

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

  String _fmtSigned(double v) {
    final formatted = _fmt.format(v.abs());
    if (v > 0) return '+$formatted';
    if (v < 0) return '-$formatted';
    return formatted;
  }

  Color? _pnlColor(double v) {
    if (v > 0) return const Color(0xFF059669);
    if (v < 0) return const Color(0xFFDC2626);
    return null;
  }

  Color _driftColor(double drift) {
    if (drift.abs() < 1.0) return AppColors.textPrimary;
    if (drift > 0) return const Color(0xFF059669);
    return const Color(0xFFDC2626);
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

// ─── Chart geometry & painters ──────────────────────────────────────

class _ChartGeo {
  const _ChartGeo({
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

class _LinePainter extends CustomPainter {
  _LinePainter({
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
  bool shouldRepaint(covariant _LinePainter old) =>
      old.accent != accent ||
      old.startY != startY ||
      old.points.length != points.length ||
      (points.isNotEmpty && old.points.isNotEmpty && old.points.last != points.last);
}

class _ChartEntranceAnimation extends StatefulWidget {
  const _ChartEntranceAnimation({super.key, required this.child});
  final Widget child;

  @override
  State<_ChartEntranceAnimation> createState() =>
      _ChartEntranceAnimationState();
}

class _ChartEntranceAnimationState extends State<_ChartEntranceAnimation>
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
