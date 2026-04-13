import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;

import '../../../../core/config.dart';
import '../../../../core/session_bearer_http.dart';
import '../../../../design_system/design_system.dart';
import 'chart_asset_module.dart';

class _ChartPoint {
  final DateTime time;
  final double value;
  const _ChartPoint(this.time, this.value);
}

/// Métriques pour le header [LayoutPageInstrumentDetail] (détail bundle), hors carte liste.
class BundleChartHeroMetrics {
  const BundleChartHeroMetrics({
    required this.performancePct,
    required this.periodCaption,
    required this.hasPoints,
  });

  final double performancePct;
  final String periodCaption;
  final bool hasPoints;
}

/// Performance chart for bundle products — mirrors [ChartAssetModule] layout.
///
/// Mode liste : carte avec perf % + courbe + onglets.
/// Mode [embedInstrumentHero] : uniquement courbe + onglets + disclaimer (perf % dans le header).
class BundlePerformanceChartModule extends StatefulWidget {
  const BundlePerformanceChartModule({
    super.key,
    required this.productCode,
    this.title = 'Performance',
    this.embedInstrumentHero = false,
    this.onHeroMetricsChanged,
  });

  final String productCode;
  final String title;
  final bool embedInstrumentHero;
  final void Function(BundleChartHeroMetrics metrics)? onHeroMetricsChanged;

  @override
  State<BundlePerformanceChartModule> createState() =>
      _BundlePerformanceChartModuleState();
}

class _BundlePerformanceChartModuleState
    extends State<BundlePerformanceChartModule>
    with SingleTickerProviderStateMixin {
  static const _periods = ['1j', '1s', '1m', '1a', '5a'];
  static const _periodCaptions = [
    '1 jour',
    '1 semaine',
    '1 mois',
    '1 an',
    '5 ans',
  ];

  // Same constants as ChartAssetModule
  static const double _chartRightMargin = 24.0;
  static const double _chartBottomMargin = 24.0;
  static const double _chartHeightBase = 212.0;
  static const double _chartTotalHeight = _chartHeightBase + _chartBottomMargin;
  static const double _periodChipHeight = 36.0;
  /// Aligné sur [ChartAssetModule] : piste grise, capsule blanche ([AppColors.pageBackground]).
  static const double _periodPillInset = 2.0;

  int _selectedIndex = 3;
  List<_ChartPoint> _points = [];
  double _performancePct = 0.0;
  bool _loading = true;
  String? _error;

  late AnimationController _shimmerCtrl;
  late Animation<double> _shimmerAnim;

  @override
  void initState() {
    super.initState();
    _shimmerCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
    _shimmerAnim = Tween<double>(begin: 0.08, end: 0.22).animate(
      CurvedAnimation(parent: _shimmerCtrl, curve: Curves.easeInOut),
    );
    _load();
  }

  @override
  void dispose() {
    _shimmerCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final period = _periods[_selectedIndex];
      final uri = Uri.parse(Config.portfolioProductChartUrl(widget.productCode, period));
      final response = await http.get(
        uri,
        headers: await SessionBearerHttp.jsonHeadersAppScoped(
          uri: uri,
          debugTag: 'BundlePerformanceChartModule._load',
        ),
      );

      if (!mounted) return;

      if (response.statusCode != 200) {
        setState(() {
          _loading = false;
          _error = 'Données indisponibles';
          _points = [];
          _performancePct = 0;
        });
        _emitHeroMetrics();
        return;
      }

      final json = jsonDecode(response.body) as Map<String, dynamic>;
      final rawPoints = (json['points'] as List?) ?? [];
      final perfPct = (json['performance_pct'] as num?)?.toDouble() ?? 0.0;

      final parsed = <_ChartPoint>[];
      for (final raw in rawPoints) {
        if (raw is! Map) continue;
        final ts = raw['open_time'];
        final val = raw['value'];
        if (ts == null || val == null) continue;
        final dt = DateTime.tryParse(ts.toString());
        final v = (val is num) ? val.toDouble() : double.tryParse(val.toString());
        if (dt != null && v != null) {
          parsed.add(_ChartPoint(dt, v));
        }
      }

      setState(() {
        _points = parsed;
        _performancePct = perfPct;
        _loading = false;
      });
      _emitHeroMetrics();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Erreur de chargement';
        _points = [];
        _performancePct = 0;
      });
      _emitHeroMetrics();
    }
  }

  void _emitHeroMetrics() {
    if (!widget.embedInstrumentHero || widget.onHeroMetricsChanged == null) {
      return;
    }
    widget.onHeroMetricsChanged!(
      BundleChartHeroMetrics(
        performancePct: _performancePct,
        periodCaption: _periodCaptions[_selectedIndex],
        hasPoints: _points.length >= 2,
      ),
    );
  }

  void _onPeriodChanged(int index) {
    if (index == _selectedIndex) return;
    HapticFeedback.lightImpact();
    setState(() => _selectedIndex = index);
    _load();
  }

  // ---------------------------------------------------------------------------
  // Skeleton helpers
  // ---------------------------------------------------------------------------

  Widget _skeletonBlock({
    required double width,
    required double height,
    double borderRadius = 4,
  }) {
    return AnimatedBuilder(
      animation: _shimmerAnim,
      builder: (context, child) {
        return Container(
          width: width,
          height: height,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(borderRadius),
            color: AppColors.textSecondary.withValues(alpha: _shimmerAnim.value),
          ),
        );
      },
    );
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.sizeOf(context).width;
    final isPositive = _performancePct >= 0;
    final perfColor = isPositive
        ? AppColors.semanticPositive
        : AppColors.semanticNegative;
    final perfStr =
        '${isPositive ? '+' : ''}${_performancePct.toStringAsFixed(2)} %';

    final chartWidthCard = screenWidth - AppSpacing.lg - _chartRightMargin;
    final chartWidthHero = screenWidth - _chartRightMargin;
    final chartLeftInset = widget.embedInstrumentHero ? 0.0 : -AppSpacing.lg;
    final chartW = widget.embedInstrumentHero ? chartWidthHero : chartWidthCard;

    final cardPerfHeader = _loading
        ? Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              _skeletonBlock(width: 72, height: 28, borderRadius: 999),
              const SizedBox(width: AppSpacing.sm),
              _skeletonBlock(width: 72, height: 14, borderRadius: 4),
            ],
          )
        : InstrumentDetailHeroPerformanceRow(
            percentChipText: perfStr,
            periodLabel: _periodCaptions[_selectedIndex],
            percentColor: perfColor,
            percentIsPositive: isPositive,
          );

    final chartStack = SizedBox(
      height: _chartTotalHeight,
      child: _loading
          ? _buildLoadingChart()
          : Stack(
              clipBehavior: Clip.hardEdge,
              children: [
                Positioned(
                  left: chartLeftInset,
                  top: 0,
                  child: SizedBox(
                    width: chartW,
                    height: _chartTotalHeight,
                    child: _buildChartContent(chartW),
                  ),
                ),
              ],
            ),
    );

    final disclaimer = Text(
      'Performance simulée basée sur l\'allocation pondérée des actifs du bundle '
      'sur la période sélectionnée.',
      textAlign: TextAlign.center,
      style: AppTypography.meta.copyWith(
        color: AppColors.textSecondary,
        fontSize: 12,
      ),
    );

    if (widget.embedInstrumentHero) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          chartStack,
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: AppSpacing.md),
                _buildPeriodChips(),
                const SizedBox(height: AppSpacing.md),
                disclaimer,
              ],
            ),
          ),
        ],
      );
    }

    return Container(
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(AppRadius.card + 4),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.lg,
          AppSpacing.lg,
          AppSpacing.lg,
          AppSpacing.lg,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            cardPerfHeader,
            const SizedBox(height: AppSpacing.md),
            chartStack,
            const SizedBox(height: AppSpacing.md),
            _buildPeriodChips(),
            const SizedBox(height: AppSpacing.md),
            disclaimer,
          ],
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Loading chart skeleton
  // ---------------------------------------------------------------------------

  Widget _buildLoadingChart() {
    return const SizedBox(height: _chartTotalHeight);
  }

  // ---------------------------------------------------------------------------
  // Chart content (line + sonar + start label) — identical to ChartAssetModule
  // ---------------------------------------------------------------------------

  Widget _buildChartContent(double chartWidth) {
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline_rounded,
              size: 36,
              color: AppColors.textSecondary.withValues(alpha: 0.7),
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              _error!,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            TextButton.icon(
              onPressed: _load,
              icon: const Icon(Icons.refresh_rounded, size: 16),
              label: const Text('Réessayer'),
              style: TextButton.styleFrom(foregroundColor: AppColors.accent),
            ),
          ],
        ),
      );
    }
    if (_points.isEmpty) {
      return Center(
        child: Text(
          'Aucune donnée pour cette période',
          style: AppTypography.bodySmall.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
      );
    }

    final lineColor = _points.length >= 2
        ? instrumentDetailLineTrendColorFromEndpoints(
            _points.first.value,
            _points.last.value,
          )
        : AppColors.chartLine;

    return _ChartEntranceAnimation(
      key: ValueKey('bundle-chart-$_selectedIndex'),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final size = Size(constraints.maxWidth, constraints.maxHeight);
          final geometry = _computeLineGeometry(_points, size);
          return Stack(
            clipBehavior: Clip.none,
            children: [
              Positioned.fill(
                child: CustomPaint(
                  painter: _BundleLinePainter(
                    accent: lineColor,
                    strokeWidth: ChartAssetModule.instrumentDetailLineStrokeWidth,
                    points: geometry.points,
                    startY: geometry.startY,
                  ),
                ),
              ),
              // Sonar point at the end of the curve
              Positioned(
                left: geometry.lastPoint.dx - ChartSonarPoint.size / 2,
                top: geometry.lastPoint.dy - ChartSonarPoint.size / 2,
                child: ChartSonarPoint(color: lineColor),
              ),
            ],
          );
        },
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Line geometry computation — same approach as ChartAssetModule
  // ---------------------------------------------------------------------------

  _LineGeometry _computeLineGeometry(List<_ChartPoint> chartPoints, Size size) {
    if (chartPoints.isEmpty) {
      return const _LineGeometry(
        points: [],
        startY: 0,
        lastPoint: Offset(0, 0),
      );
    }
    final values = chartPoints.map((p) => p.value).toList();
    final minVal = values.reduce(math.min);
    final maxVal = values.reduce(math.max);
    const paddingTop = 16.0;
    const paddingBottom = 16.0 + _chartBottomMargin;
    final range = (maxVal - minVal).abs() < 1e-9 ? 1.0 : (maxVal - minVal);
    final usableHeight = math.max(1.0, size.height - paddingTop - paddingBottom);
    final usableWidth = math.max(1.0, size.width - _chartRightMargin);
    final offsets = <Offset>[];
    for (var i = 0; i < values.length; i++) {
      final x = values.length == 1 ? 0.0 : usableWidth * (i / (values.length - 1));
      final normalized = (values[i] - minVal) / range;
      final y = paddingTop + (1 - normalized) * usableHeight;
      offsets.add(Offset(x, y));
    }
    return _LineGeometry(
      points: offsets,
      startY: offsets.isEmpty ? 0 : offsets.first.dy,
      lastPoint: offsets.isEmpty ? Offset.zero : offsets.last,
    );
  }

  // ---------------------------------------------------------------------------
  // Period chips — same as ChartAssetModule
  // ---------------------------------------------------------------------------

  Widget _buildPeriodChips() {
    return Container(
      padding: const EdgeInsets.all(_periodPillInset),
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(999),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final segmentWidth = constraints.maxWidth / _periods.length;
          final pillW = segmentWidth - 2 * _periodPillInset;
          const pillH = _periodChipHeight - 2 * _periodPillInset;
          return SizedBox(
            height: _periodChipHeight,
            child: Stack(
              children: [
                AnimatedPositioned(
                  duration: const Duration(milliseconds: 220),
                  curve: Curves.easeOutCubic,
                  left: _selectedIndex * segmentWidth + _periodPillInset,
                  top: _periodPillInset,
                  width: pillW,
                  height: pillH,
                  child: Container(
                    decoration: BoxDecoration(
                      color: AppColors.pageBackground,
                      borderRadius: BorderRadius.circular(999),
                    ),
                  ),
                ),
                Row(
                  children: [
                    for (int i = 0; i < _periods.length; i++)
                      Expanded(
                        child: GestureDetector(
                          onTap: () => _onPeriodChanged(i),
                          behavior: HitTestBehavior.opaque,
                          child: Center(
                            child: Text(
                              _periods[i],
                              style: AppTypography.bodyMedium.copyWith(
                                color: i == _selectedIndex
                                    ? AppColors.textPrimary
                                    : AppColors.textSecondary,
                                fontWeight: i == _selectedIndex
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
}

// =============================================================================
// Data classes
// =============================================================================

class _LineGeometry {
  const _LineGeometry({
    required this.points,
    required this.startY,
    required this.lastPoint,
  });

  final List<Offset> points;
  final double startY;
  final Offset lastPoint;
}

// =============================================================================
// Line painter — same as ChartAssetModule._LinePainter (dashed baseline + Catmull-Rom)
// =============================================================================

class _BundleLinePainter extends CustomPainter {
  _BundleLinePainter({
    required this.accent,
    required this.points,
    required this.startY,
    required this.strokeWidth,
  });

  final Color accent;
  final List<Offset> points;
  final double startY;
  final double strokeWidth;

  @override
  void paint(Canvas canvas, Size size) {
    final dotted = Paint()
      ..color = AppColors.textSecondary.withValues(alpha: 0.55)
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    // Dashed horizontal baseline at start price
    final yStart = startY.clamp(0, size.height).toDouble();
    const dashWidth = 2.2;
    const gap = 5.0;
    var x = 0.0;
    while (x < size.width) {
      final x2 = math.min(x + dashWidth, size.width).toDouble();
      canvas.drawLine(Offset(x, yStart), Offset(x2, yStart), dotted);
      x += dashWidth + gap;
    }

    if (points.isEmpty) return;

    // Catmull-Rom spline (épaisseur alignée [ChartAssetModule] détail instrument)
    final paint = Paint()
      ..color = accent
      ..strokeWidth = strokeWidth
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

    final path = Path();
    path.moveTo(clamped[0].dx, clamped[0].dy);
    if (clamped.length == 1) {
      canvas.drawPath(path, paint);
      return;
    }
    if (clamped.length == 2) {
      path.lineTo(clamped[1].dx, clamped[1].dy);
      canvas.drawPath(path, paint);
      return;
    }
    for (var i = 0; i < clamped.length - 1; i++) {
      final p0 = clamped[i > 0 ? i - 1 : i];
      final p1 = clamped[i];
      final p2 = clamped[i + 1];
      final p3 = clamped[i + 1 < clamped.length - 1 ? i + 2 : i + 1];
      final c1 = i == 0
          ? p1
          : Offset(
              p1.dx + (p2.dx - p0.dx) / 6,
              p1.dy + (p2.dy - p0.dy) / 6,
            );
      final c2 = i == clamped.length - 2
          ? p2
          : Offset(
              p2.dx - (p3.dx - p1.dx) / 6,
              p2.dy - (p3.dy - p1.dy) / 6,
            );
      path.cubicTo(c1.dx, c1.dy, c2.dx, c2.dy, p2.dx, p2.dy);
    }
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _BundleLinePainter oldDelegate) =>
      oldDelegate.accent != accent ||
      oldDelegate.strokeWidth != strokeWidth ||
      oldDelegate.startY != startY ||
      oldDelegate.points.length != points.length ||
      (points.isNotEmpty &&
          oldDelegate.points.isNotEmpty &&
          oldDelegate.points.last != points.last);
}

// =============================================================================
// Chart entrance animation (left-to-right reveal) — same as ChartAssetModule
// =============================================================================

class _ChartEntranceAnimation extends StatefulWidget {
  const _ChartEntranceAnimation({super.key, required this.child});
  final Widget child;

  @override
  State<_ChartEntranceAnimation> createState() =>
      _ChartEntranceAnimationState();
}

class _ChartEntranceAnimationState extends State<_ChartEntranceAnimation>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _reveal;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 320),
    );
    _reveal = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _ctrl, curve: Curves.easeOutCubic),
    );
    _ctrl.forward();
  }

  @override
  void dispose() {
    _ctrl.dispose();
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
