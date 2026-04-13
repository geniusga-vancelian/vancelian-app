import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../core/currency_preference.dart';
import '../../../../design_system/design_system.dart';
import '../../data/global_statistics_api.dart';
import '../../domain/models/global_statistics.dart';

class GlobalStatisticsScreen extends StatefulWidget {
  const GlobalStatisticsScreen({super.key});

  @override
  State<GlobalStatisticsScreen> createState() => _GlobalStatisticsScreenState();
}

class _GlobalStatisticsScreenState extends State<GlobalStatisticsScreen> {
  final GlobalStatisticsApi _statsApi = const GlobalStatisticsApi();
  final ScrollController _scrollController = ScrollController();
  double _navTitleOpacity = 0;

  GlobalStatistics? _stats;
  List<GlobalHistoryPoint> _chartPoints = [];
  double? _maxDrawdown;
  bool _isLoading = true;
  String? _error;

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
        _statsApi.fetchHistory(period: _selectedPeriod),
      ]);
      if (!mounted) return;
      final histResult = results[1] as GlobalHistoryResult;
      setState(() {
        _stats = results[0] as GlobalStatistics;
        _chartPoints = histResult.points;
        _maxDrawdown = histResult.maxDrawdown;
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
      final histResult = await _statsApi.fetchHistory(period: period);
      if (!mounted) return;
      setState(() {
        _chartPoints = histResult.points;
        _maxDrawdown = histResult.maxDrawdown;
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
        title: 'Mon patrimoine',
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
              child: AppPageTitle('Mon patrimoine'),
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
                  _buildBreakdown(s),
                  const SizedBox(height: 16),
                  _buildAccountContributions(s),
                  const SizedBox(height: 16),
                  _buildAssetAllocation(s),
                  const SizedBox(height: 16),
                  _buildAccountAllocation(s),
                  const SizedBox(height: 16),
                  _buildContributions(s),
                  const SizedBox(height: 16),
                  _buildCashflow(s),
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

  Widget _buildPerformance(GlobalStatistics s) {
    final pnlColor = _pnlColor(s.totalPnl);
    final pctLabel = '(${s.performancePct >= 0 ? '+' : ''}${s.performancePct.toStringAsFixed(2)}%)';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Performance'),
        const SizedBox(height: 10),
        _ModuleCard(
          child: Column(
            children: [
              _infoRow('Valeur totale', _fmt.format(s.currentValue)),
              _infoRow('Net investi', _fmt.format(s.totalInvested)),
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
  static const List<String> _periodLabels = ['1D', '1W', '1M', '1Y', 'ALL'];
  static const List<String> _periodCaptions = [
    '1 jour',
    '1 semaine',
    '1 mois',
    '1 an',
    'Tout',
  ];

  int get _periodIndex => _periodLabels.indexOf(_selectedPeriod).clamp(0, 4);

  List<double> get _chartValues {
    if (_chartPoints.isEmpty) return [];
    return _chartPoints.map((p) => p.performanceValue).toList();
  }

  Widget _buildChartModule() {
    final values = _chartValues;
    const brandColor = Color(0xFF0D1B2A);

    final lastPerfVal = _chartPoints.isNotEmpty ? _chartPoints.last.performanceValue : 0.0;
    final isPositive = lastPerfVal >= 0;
    final perfColor =
        isPositive ? const Color(0xFF059669) : const Color(0xFFDC2626);

    final headerValue = _fmtSigned(lastPerfVal);

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
                      isPositive
                          ? Icons.arrow_drop_up
                          : Icons.arrow_drop_down,
                      color: perfColor,
                      size: 20,
                    ),
                    Text(
                      _periodCaptions[_periodIndex],
                      style: AppTypography.bodySmall
                          .copyWith(color: AppColors.textSecondary),
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
                              style: AppTypography.bodySmall
                                  .copyWith(color: AppColors.textSecondary),
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
                                painter: _ChartPainter(
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

  // ─── Breakdown ───────────────────────────────────────────────────

  Widget _buildBreakdown(GlobalStatistics s) {
    final b = s.breakdown;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Répartition par compte'),
        const SizedBox(height: 10),
        _ModuleCard(
          child: Column(
            children: [
              _infoRow(
                'Compte Euro',
                '${_fmt.format(b.fiat)} (${b.fiatPct.toStringAsFixed(1)}%)',
              ),
              _infoRow(
                'Crypto direct',
                '${_fmt.format(b.cryptoDirect)} (${b.cryptoDirectPct.toStringAsFixed(1)}%)',
              ),
              _infoRow(
                'Bundles',
                '${_fmt.format(b.bundles)} (${b.bundlesPct.toStringAsFixed(1)}%)',
                isLast: true,
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ─── Account Contributions ──────────────────────────────────────

  Widget _buildAccountContributions(GlobalStatistics s) {
    if (s.accountContributions.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Contribution par compte'),
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
                      child: Text('Compte',
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
              ),
              for (int i = 0; i < s.accountContributions.length; i++)
                _accountContribRow(
                  s.accountContributions[i],
                  isLast: i == s.accountContributions.length - 1,
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _accountContribRow(GlobalAccountContribution c, {bool isLast = false}) {
    return Padding(
      padding: EdgeInsets.only(bottom: isLast ? 0 : 12),
      child: Row(
        children: [
          Expanded(
            flex: 3,
            child: Text(c.account,
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

  // ─── Asset Allocation ──────────────────────────────────────────

  Widget _buildAssetAllocation(GlobalStatistics s) {
    if (s.allocation.isEmpty) return const SizedBox.shrink();
    final items = s.allocation.where((a) => a.weight > 0).toList();
    if (items.isEmpty) return const SizedBox.shrink();
    final top = items.first;
    final slices = items
        .map((a) => DonutsChartSlice(label: a.asset, percentage: a.weight))
        .toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Allocation par actif'),
        const SizedBox(height: 4),
        Padding(
          padding: const EdgeInsets.only(left: 2, bottom: 6),
          child: Text(
            'Top exposition : ${top.asset} (${top.weight.toStringAsFixed(1)}%)',
            style: AppTypography.bodySmall.copyWith(color: AppColors.textSecondary),
          ),
        ),
        DonutsChartBig(slices: slices),
      ],
    );
  }

  // ─── Account Allocation ─────────────────────────────────────────

  Widget _buildAccountAllocation(GlobalStatistics s) {
    final b = s.breakdown;
    final slices = <DonutsChartSlice>[];
    if (b.fiatPct > 0) slices.add(DonutsChartSlice(label: 'Euro', percentage: b.fiatPct));
    if (b.cryptoDirectPct > 0) slices.add(DonutsChartSlice(label: 'Crypto', percentage: b.cryptoDirectPct));
    if (b.bundlesPct > 0) slices.add(DonutsChartSlice(label: 'Bundles', percentage: b.bundlesPct));
    if (slices.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Allocation par compte'),
        const SizedBox(height: 10),
        DonutsChartBig(slices: slices),
      ],
    );
  }

  // ─── Asset Contributions ───────────────────────────────────────

  Widget _buildContributions(GlobalStatistics s) {
    if (s.contributions.isEmpty) return const SizedBox.shrink();
    final sorted = [...s.contributions]..sort((a, b) => b.pnl.compareTo(a.pnl));
    final positive = sorted.where((c) => c.pnl > 0).take(3).toList();
    final negative = sorted.where((c) => c.pnl < 0).toList();

    if (positive.isEmpty && negative.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Contribution par actif'),
        const SizedBox(height: 10),
        if (positive.isNotEmpty)
          _ModuleCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Top contributeurs',
                    style: AppTypography.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                        fontWeight: FontWeight.w600)),
                const SizedBox(height: 10),
                for (int i = 0; i < positive.length; i++)
                  _contributionRow(
                    positive[i],
                    icon: Icons.trending_up_rounded,
                    isLast: i == positive.length - 1,
                  ),
              ],
            ),
          ),
        if (positive.isNotEmpty && negative.isNotEmpty)
          const SizedBox(height: 10),
        if (negative.isNotEmpty)
          _ModuleCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Contributeurs négatifs',
                    style: AppTypography.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                        fontWeight: FontWeight.w600)),
                const SizedBox(height: 10),
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
    );
  }

  Widget _contributionRow(GlobalContribution c, {IconData? icon, bool isLast = false}) {
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

  // ─── Cashflow ────────────────────────────────────────────────────

  Widget _buildCashflow(GlobalStatistics s) {
    final cf = s.cashflow;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionTitle('Flux de trésorerie'),
        const SizedBox(height: 10),
        _ModuleCard(
          child: Column(
            children: [
              _infoRow('Dépôts', _fmt.format(cf.deposits)),
              _infoRow('Retraits', _fmt.format(cf.withdrawals)),
              _infoRow(
                'Flux net',
                _fmtSigned(cf.netFlow),
                valueColor: _pnlColor(cf.netFlow),
                isLast: true,
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ─── Activity ────────────────────────────────────────────────────

  Widget _buildActivity(GlobalStatistics s) {
    final a = s.activity;
    final dateFormat = DateFormat('dd MMM yyyy', 'fr_FR');
    String lastAct = '—';
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
      '$totalOps opération${totalOps > 1 ? 's' : ''} au total',
      '${a.directTrades} trade${a.directTrades > 1 ? 's' : ''} direct${a.directTrades > 1 ? 's' : ''}',
    ];
    if (a.bundleInvestEvents > 0) {
      lines.add('${a.bundleInvestEvents} investissement${a.bundleInvestEvents > 1 ? 's' : ''} bundle');
    }
    if (a.rebalanceEvents > 0) {
      lines.add('${a.rebalanceEvents} rééquilibrage${a.rebalanceEvents > 1 ? 's' : ''}');
    }
    if (a.depositCount > 0) {
      lines.add('${a.depositCount} dépôt${a.depositCount > 1 ? 's' : ''}');
    }
    if (a.withdrawalCount > 0) {
      lines.add('${a.withdrawalCount} retrait${a.withdrawalCount > 1 ? 's' : ''}');
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
                  padding: EdgeInsets.only(bottom: i < lines.length - 1 ? 8 : 0),
                  child: Text(
                    lines[i],
                    style: (i == 0)
                        ? AppTypography.bodyMedium.copyWith(fontWeight: FontWeight.w700)
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

  Widget _buildRisk(GlobalStatistics s) {
    final r = s.risk;
    final rows = <Widget>[];

    rows.add(_infoRow('Nombre d\'actifs', '${r.assetsCount}'));
    rows.add(_infoRow(
      'Concentration max',
      r.concentrationAsset != null
          ? '${r.concentrationAsset} (${r.concentrationPct.toStringAsFixed(1)}%)'
          : '—',
    ));
    if (r.hhi != null) {
      rows.add(_infoRow('Indice HHI', r.hhi!.toStringAsFixed(4)));
    }
    if (_maxDrawdown != null) {
      rows.add(_infoRow(
        'Max drawdown',
        '${(_maxDrawdown! * 100).toStringAsFixed(1)}%',
        valueColor: _maxDrawdown! > 0 ? const Color(0xFFDC2626) : null,
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

class _ColumnWithLastMarker extends StatelessWidget {
  const _ColumnWithLastMarker({required this.children});
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    if (children.isEmpty) return const SizedBox.shrink();
    final updated = <Widget>[];
    for (int i = 0; i < children.length; i++) {
      final w = children[i];
      if (w is Padding && i == children.length - 1) {
        updated.add(Padding(
          padding: EdgeInsets.zero,
          child: w.child,
        ));
      } else {
        updated.add(w);
      }
    }
    return Column(children: updated);
  }
}

class _ChartPainter extends CustomPainter {
  _ChartPainter({
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
    final usableHeight =
        math.max(1.0, size.height - paddingTop - paddingBottom);
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
  bool shouldRepaint(covariant _ChartPainter old) =>
      old.values.length != values.length || old.color != color;
}
