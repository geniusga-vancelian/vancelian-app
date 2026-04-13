import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../core/currency_preference.dart';
import '../../../../design_system/design_system.dart';
import '../../data/portfolio_statistics_api.dart';
import '../../data/wallet_history_api.dart';
import '../../domain/models/portfolio_statistics.dart';

class PortfolioStatisticsScreen extends StatefulWidget {
  const PortfolioStatisticsScreen({super.key});

  @override
  State<PortfolioStatisticsScreen> createState() =>
      _PortfolioStatisticsScreenState();
}

class _PortfolioStatisticsScreenState extends State<PortfolioStatisticsScreen> {
  final PortfolioStatisticsApi _statsApi = const PortfolioStatisticsApi();
  final WalletHistoryApi _historyApi = const WalletHistoryApi();
  final ScrollController _scrollController = ScrollController();
  double _navTitleOpacity = 0;

  PortfolioStatistics? _stats;
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
        _statsApi.fetchStatistics(),
        _historyApi.fetchHistory(
          period: _selectedPeriod,
          mode: 'performance_value',
          scope: 'crypto',
        ),
      ]);
      if (!mounted) return;
      setState(() {
        _stats = results[0] as PortfolioStatistics;
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
        scope: 'crypto',
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
        title: 'Mes crypto',
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
              child: AppPageTitle('Mes crypto'),
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
                  _buildAllocation(s),
                  const SizedBox(height: 16),
                  _buildSourceBreakdown(s),
                  const SizedBox(height: 16),
                  _buildContributions(s),
                  const SizedBox(height: 16),
                  _buildDeployment(s),
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

  Widget _buildPerformance(PortfolioStatistics s) {
    final pnlColor = _pnlColor(s.totalPnl);
    final pctLabel = '${s.performancePct >= 0 ? '+' : ''}${s.performancePct.toStringAsFixed(2)}%';

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
              const SizedBox(height: 6),
              Divider(height: 1, color: AppColors.textSecondary.withValues(alpha: 0.12)),
              const SizedBox(height: 12),
              _infoRow(
                'P&L total',
                '${_fmtSigned(s.totalPnl)}  $pctLabel',
                valueColor: pnlColor,
              ),
              _infoRow(
                'Réalisé',
                _fmtSigned(s.realizedPnl),
                valueColor: _pnlColor(s.realizedPnl),
                labelSecondary: true,
              ),
              _infoRow(
                'Non réalisé',
                _fmtSigned(s.unrealizedPnl),
                valueColor: _pnlColor(s.unrealizedPnl),
                labelSecondary: true,
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
    const brandColor = Color(0xFF0D1B2A);

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
                        : LayoutBuilder(
                            builder: (context, constraints) {
                              final size = Size(
                                constraints.maxWidth,
                                constraints.maxHeight,
                              );
                              return CustomPaint(
                                size: size,
                                painter: _PortfolioChartPainter(
                                  values: values,
                                  color: brandColor,
                                  chartRightMargin: _chartRightMargin,
                                  chartBottomMargin: _chartBottomMargin,
                                ),
                              );
                            },
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

  // ─── Allocation ──────────────────────────────────────────────────

  Widget _buildAllocation(PortfolioStatistics s) {
    if (s.allocation.isEmpty) return const SizedBox.shrink();
    final sorted = List<PortfolioAssetAllocation>.from(s.allocation)
      ..sort((a, b) => b.weight.compareTo(a.weight));
    final hasNonZero = sorted.any((a) => a.weight > 0);
    if (!hasNonZero) return const SizedBox.shrink();
    final top = sorted.first;
    final slices = sorted
        .where((a) => a.weight > 0)
        .map((a) => DonutsChartSlice(label: a.asset, percentage: a.weight))
        .toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Allocation globale'),
        const SizedBox(height: 4),
        Padding(
          padding: const EdgeInsets.only(left: 2),
          child: Text(
            'Top exposure : ${top.asset} (${top.weight.toStringAsFixed(1)}%)',
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ),
        const SizedBox(height: 10),
        DonutsChartBig(slices: slices),
      ],
    );
  }

  // ─── Source Breakdown ────────────────────────────────────────────

  Widget _buildSourceBreakdown(PortfolioStatistics s) {
    final sb = s.sourceBreakdown;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Répartition par source'),
        const SizedBox(height: 10),
        _ModuleCard(
          child: Column(
            children: [
              _infoRow(
                'Holdings directs',
                '${_fmt.format(sb.directValue)} (${sb.directPct.toStringAsFixed(1)}%)',
              ),
              _infoRow(
                'Holdings bundle',
                '${_fmt.format(sb.bundleValue)} (${sb.bundlePct.toStringAsFixed(1)}%)',
              ),
              _infoRow(
                'Cash bundle',
                '${_fmt.format(sb.bundleCashValue)} (${sb.bundleCashPct.toStringAsFixed(1)}%)',
                isLast: true,
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ─── Contribution ────────────────────────────────────────────────

  Widget _buildContributions(PortfolioStatistics s) {
    if (s.contributions.isEmpty) return const SizedBox.shrink();

    final sorted = List<PortfolioContribution>.from(s.contributions)
      ..sort((a, b) => b.pnl.compareTo(a.pnl));
    final positive = sorted.where((c) => c.pnl > 0).take(3).toList();
    final negative = sorted.where((c) => c.pnl < 0).toList();

    Widget header() {
      return Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Row(
          children: [
            Expanded(
              flex: 3,
              child: Text('Actif',
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.textSecondary,
                    fontWeight: FontWeight.w600,
                  )),
            ),
            Expanded(
              flex: 3,
              child: Text('P&L',
                  textAlign: TextAlign.right,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.textSecondary,
                    fontWeight: FontWeight.w600,
                  )),
            ),
            Expanded(
              flex: 2,
              child: Text('Contrib.',
                  textAlign: TextAlign.right,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.textSecondary,
                    fontWeight: FontWeight.w600,
                  )),
            ),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (positive.isNotEmpty) ...[
          AppSectionTitle('Top contributeurs'),
          const SizedBox(height: 10),
          _ModuleCard(
            child: Column(
              children: [
                header(),
                for (int i = 0; i < positive.length; i++)
                  _contributionRow(
                    positive[i],
                    icon: Icons.trending_up_rounded,
                    isLast: i == positive.length - 1,
                  ),
              ],
            ),
          ),
        ],
        if (negative.isNotEmpty) ...[
          const SizedBox(height: 16),
          AppSectionTitle('Contributeurs négatifs'),
          const SizedBox(height: 10),
          _ModuleCard(
            child: Column(
              children: [
                header(),
                for (int i = 0; i < negative.length; i++)
                  _contributionRow(
                    negative[i],
                    icon: Icons.trending_down_rounded,
                    isLast: i == negative.length - 1,
                  ),
              ],
            ),
          ),
        ],
      ],
    );
  }

  Widget _contributionRow(PortfolioContribution c, {IconData? icon, bool isLast = false}) {
    return Padding(
      padding: EdgeInsets.only(bottom: isLast ? 0 : 12),
      child: Row(
        children: [
          if (icon != null) ...[
            Icon(icon, size: 16, color: _pnlColor(c.pnl)),
            const SizedBox(width: 6),
          ],
          Expanded(
            flex: 3,
            child: Text(c.asset,
                style: AppTypography.bodyMedium
                    .copyWith(fontWeight: FontWeight.w600)),
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

  // ─── Deployment ──────────────────────────────────────────────────

  Widget _buildDeployment(PortfolioStatistics s) {
    final d = s.deployment;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Déploiement du capital'),
        const SizedBox(height: 10),
        _ModuleCard(
          child: Column(
            children: [
              _infoRow('Capital déployé', '${d.investedPct.toStringAsFixed(1)}%'),
              _infoRow('Cash inactif', '${d.cashPct.toStringAsFixed(1)}% (${_fmt.format(d.cashValue)})'),
              const SizedBox(height: 6),
              Divider(height: 1, color: AppColors.textSecondary.withValues(alpha: 0.12)),
              const SizedBox(height: 12),
              _infoRow('Wallets directs', '${d.directWallets}'),
              _infoRow('Bundles actifs', '${d.activeBundles}', isLast: true),
            ],
          ),
        ),
      ],
    );
  }

  // ─── Activity ────────────────────────────────────────────────────

  Widget _buildActivity(PortfolioStatistics s) {
    final a = s.activity;
    final dateFormat = DateFormat('dd MMM yyyy', 'fr_FR');
    String lastAct = 'Aucune activité';
    if (a.lastActivity != null) {
      final diff = DateTime.now().difference(a.lastActivity!);
      if (diff.inDays == 0) {
        lastAct = "Aujourd'hui";
      } else if (diff.inDays == 1) {
        lastAct = 'Hier';
      } else {
        lastAct = dateFormat.format(a.lastActivity!);
      }
    }

    final totalOps = a.directTrades + a.bundleInvestEvents + a.rebalanceEvents;
    final lines = <String>[
      '$totalOps opérations au total',
      '${a.directTrades} trade${a.directTrades > 1 ? 's' : ''} direct${a.directTrades > 1 ? 's' : ''}',
    ];
    if (a.bundleInvestEvents > 0) {
      lines.add('${a.bundleInvestEvents} investissement${a.bundleInvestEvents > 1 ? 's' : ''} bundle');
    }
    if (a.rebalanceEvents > 0) {
      lines.add('${a.rebalanceEvents} rééquilibrage${a.rebalanceEvents > 1 ? 's' : ''}');
    }
    lines.add('Dernière activité : $lastAct');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Activité'),
        const SizedBox(height: 10),
        _ModuleCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (int i = 0; i < lines.length; i++)
                Padding(
                  padding: EdgeInsets.only(bottom: i == lines.length - 1 ? 0 : 10),
                  child: Text(
                    lines[i],
                    style: (i == 0)
                        ? AppTypography.bodyMedium.copyWith(fontWeight: FontWeight.w600)
                        : AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }

  // ─── Risk ────────────────────────────────────────────────────────

  Widget _buildRisk(PortfolioStatistics s) {
    final r = s.risk;
    final rows = <Widget>[
      _infoRow('Nombre d\'actifs', '${r.assetsCount}'),
      _infoRow(
        'Concentration max',
        r.concentrationAsset != null
            ? '${r.concentrationAsset} (${r.concentrationPct.toStringAsFixed(1)}%)'
            : '—',
      ),
    ];
    if (r.volatility30d != null) {
      rows.add(_infoRow(
        'Volatilité 30j',
        '${(r.volatility30d! * 100).toStringAsFixed(1)}%',
      ));
    }
    if (r.maxDrawdown != null) {
      rows.add(_infoRow(
        'Max drawdown',
        '${(r.maxDrawdown! * 100).toStringAsFixed(1)}%',
      ));
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Risque'),
        const SizedBox(height: 10),
        _ModuleCard(
          child: _ColumnWithLastMarker(children: rows),
        ),
      ],
    );
  }

  // ─── Helpers ─────────────────────────────────────────────────────

  Widget _infoRow(String label, String value,
      {Color? valueColor, bool isLast = false, bool labelSecondary = false}) {
    return Padding(
      padding: EdgeInsets.only(bottom: isLast ? 0 : 14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(
              label,
              style: AppTypography.bodyMedium.copyWith(
                color: labelSecondary ? AppColors.textSecondary : AppColors.textPrimary,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              value,
              style: AppTypography.bodyMedium.copyWith(
                color: valueColor ?? AppColors.textPrimary,
              ),
              textAlign: TextAlign.right,
            ),
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
}

// ─── Reusable sub-widgets ──────────────────────────────────────────

class _ColumnWithLastMarker extends StatelessWidget {
  const _ColumnWithLastMarker({required this.children});
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    if (children.isEmpty) return const SizedBox.shrink();
    return Column(
      children: [
        for (int i = 0; i < children.length; i++) children[i],
      ],
    );
  }
}

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

class _PortfolioChartPainter extends CustomPainter {
  _PortfolioChartPainter({
    required this.values,
    required this.color,
    required this.chartRightMargin,
    required this.chartBottomMargin,
  });

  final List<double> values;
  final Color color;
  final double chartRightMargin;
  final double chartBottomMargin;

  @override
  void paint(Canvas canvas, Size size) {
    if (values.isEmpty) return;

    final mn = values.reduce(math.min);
    final mx = values.reduce(math.max);
    final range = (mx - mn).abs() < 1e-9 ? 1.0 : (mx - mn);
    const paddingTop = 16.0;
    final paddingBottom = 16.0 + chartBottomMargin;
    final usableHeight = math.max(1.0, size.height - paddingTop - paddingBottom);
    final usableWidth = math.max(1.0, size.width - chartRightMargin);

    final points = <Offset>[];
    for (var i = 0; i < values.length; i++) {
      final x =
          values.length == 1 ? 0.0 : usableWidth * (i / (values.length - 1));
      final normalized = (values[i] - mn) / range;
      final y = paddingTop + (1 - normalized) * usableHeight;
      points.add(Offset(x, y));
    }

    final paint = Paint()
      ..color = color
      ..strokeWidth = 2.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    final path = Path()..moveTo(points[0].dx, points[0].dy);
    if (points.length == 2) {
      path.lineTo(points[1].dx, points[1].dy);
    } else {
      for (var i = 0; i < points.length - 1; i++) {
        final p0 = points[i > 0 ? i - 1 : i];
        final p1 = points[i];
        final p2 = points[i + 1];
        final p3 = points[i + 1 < points.length - 1 ? i + 2 : i + 1];
        final c1 = i == 0
            ? p1
            : Offset(
                p1.dx + (p2.dx - p0.dx) / 6, p1.dy + (p2.dy - p0.dy) / 6);
        final c2 = i == points.length - 2
            ? p2
            : Offset(
                p2.dx - (p3.dx - p1.dx) / 6, p2.dy - (p3.dy - p1.dy) / 6);
        path.cubicTo(c1.dx, c1.dy, c2.dx, c2.dy, p2.dx, p2.dy);
      }
    }
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _PortfolioChartPainter old) =>
      old.values.length != values.length || old.color != color;
}
