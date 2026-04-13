import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../core/currency_preference.dart';
import '../../../../design_system/design_system.dart';
import '../../data/wallet_history_api.dart';

const List<String> _periods = ['1D', '1W', '1M', 'ALL'];

class HistoricalWalletValueChart extends StatefulWidget {
  const HistoricalWalletValueChart({super.key, this.onDataLoaded});

  final void Function(List<double> normalised)? onDataLoaded;

  @override
  State<HistoricalWalletValueChart> createState() =>
      _HistoricalWalletValueChartState();
}

class _HistoricalWalletValueChartState
    extends State<HistoricalWalletValueChart>
    with SingleTickerProviderStateMixin {
  final WalletHistoryApi _api = const WalletHistoryApi();
  String _period = 'ALL';
  WalletHistoryData? _data;
  bool _loading = true;
  bool _switching = false;
  String? _error;

  late final AnimationController _shimmerCtrl;
  late final Animation<double> _shimmerAnim;

  @override
  void initState() {
    super.initState();
    _shimmerCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat(reverse: true);
    _shimmerAnim = CurvedAnimation(parent: _shimmerCtrl, curve: Curves.easeInOut);
    _load();
  }

  @override
  void dispose() {
    _shimmerCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final isSwitch = _data != null;
    setState(() {
      if (isSwitch) {
        _switching = true;
      } else {
        _loading = true;
      }
      _error = null;
    });
    try {
      final data = await _api.fetchHistory(period: _period);
      if (!mounted) return;
      setState(() {
        _data = data;
        _loading = false;
        _switching = false;
      });
      _emitNormalised(data);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _switching = false;
        _error = 'Données indisponibles';
      });
    }
  }

  void _emitNormalised(WalletHistoryData data) {
    if (widget.onDataLoaded == null || data.points.isEmpty) return;
    final values = data.points.map((p) => p.walletValue).toList();
    final mn = values.reduce(math.min);
    final mx = values.reduce(math.max);
    final range = (mx - mn).clamp(0.001, double.infinity);
    final normalised = values.map((v) => (v - mn) / range).toList();
    widget.onDataLoaded!(normalised);
  }

  void _selectPeriod(String p) {
    if (p == _period) return;
    setState(() => _period = p);
    _load();
  }

  NumberFormat get _activeFormatter {
    final pref = CurrencyPreference.instance;
    return pref.currency == ReferenceCurrency.eur
        ? NumberFormat.currency(locale: 'fr_FR', symbol: '€', decimalDigits: 2)
        : NumberFormat.currency(locale: 'en_US', symbol: '\$', decimalDigits: 2);
  }

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
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _buildHeader(),
            const SizedBox(height: 4),
            _buildValueRow(),
            const SizedBox(height: 12),
            _buildPeriodSelector(),
            const SizedBox(height: 16),
            _buildChart(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Text(
      'Historique de valeur',
      style: AppTypography.sectionTitle.copyWith(
        color: AppColors.textPrimary,
        fontWeight: FontWeight.w700,
      ),
    );
  }

  Widget _buildValueRow() {
    if (_data == null || _data!.points.isEmpty) {
      return const SizedBox(height: 28);
    }
    final last = _data!.points.last.walletValue;
    final first = _data!.points.first.walletValue;
    final diff = last - first;
    final pct = first > 0 ? (diff / first) * 100 : 0.0;
    final isPositive = diff >= 0;
    final color = isPositive ? const Color(0xFF059669) : const Color(0xFFDC2626);
    final sign = isPositive ? '+' : '';
    final fmt = _activeFormatter;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.baseline,
      textBaseline: TextBaseline.alphabetic,
      children: [
        Text(
          fmt.format(last),
          style: AppTypography.heroAmount.copyWith(
            color: AppColors.textPrimary,
            fontSize: 22,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(width: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(6),
          ),
          child: Text(
            '$sign${pct.toStringAsFixed(1)}%',
            style: AppTypography.meta.copyWith(
              color: color,
              fontWeight: FontWeight.w700,
              fontSize: 13,
            ),
          ),
        ),
        const SizedBox(width: 6),
        Expanded(
          child: Text(
            '$sign${fmt.format(diff.abs())}',
            style: AppTypography.meta.copyWith(
              color: color.withValues(alpha: 0.7),
              fontSize: 12,
            ),
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }

  Widget _buildPeriodSelector() {
    return Row(
      children: _periods.map((p) {
        final selected = p == _period;
        return Padding(
          padding: const EdgeInsets.only(right: 8),
          child: GestureDetector(
            onTap: () => _selectPeriod(p),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
              decoration: BoxDecoration(
                color: selected
                    ? AppColors.textPrimary
                    : AppColors.textSecondary.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text(
                p,
                style: AppTypography.meta.copyWith(
                  color: selected ? Colors.white : AppColors.textSecondary,
                  fontWeight: FontWeight.w600,
                  fontSize: 13,
                ),
              ),
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildChart() {
    if (_loading && _data == null) {
      return _buildShimmerChart();
    }

    if (_error != null && _data == null) {
      return _buildErrorState();
    }

    if (_data != null && _data!.points.isEmpty) {
      return _buildEmptyState();
    }

    if (_data == null) return const SizedBox(height: 160);

    final values = _data!.points.map((p) => p.walletValue).toList();
    final isPositive = values.last >= values.first;
    final lineColor =
        isPositive ? const Color(0xFF059669) : const Color(0xFFDC2626);

    return SizedBox(
      height: 160,
      child: Stack(
        children: [
          LayoutBuilder(
            builder: (context, constraints) {
              return CustomPaint(
                size: Size(constraints.maxWidth, constraints.maxHeight),
                painter: _WalletChartPainter(
                  values: values,
                  lineColor: lineColor,
                ),
              );
            },
          ),
          if (_switching)
            Positioned.fill(
              child: Container(
                decoration: BoxDecoration(
                  color: AppColors.cardBackground.withValues(alpha: 0.5),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Center(
                  child: SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildShimmerChart() {
    return AnimatedBuilder(
      animation: _shimmerAnim,
      builder: (context, _) {
        final t = _shimmerAnim.value;
        final alpha = 0.04 + 0.08 * t;
        return SizedBox(
          height: 160,
          child: Column(
            children: [
              const SizedBox(height: 8),
              Expanded(
                child: CustomPaint(
                  size: const Size(double.infinity, double.infinity),
                  painter: _ShimmerChartPainter(
                    color: AppColors.textSecondary.withValues(alpha: alpha),
                  ),
                ),
              ),
              const SizedBox(height: 8),
            ],
          ),
        );
      },
    );
  }

  Widget _buildEmptyState() {
    return SizedBox(
      height: 160,
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.show_chart_rounded,
              size: 36,
              color: AppColors.textSecondary.withValues(alpha: 0.4),
            ),
            const SizedBox(height: 8),
            Text(
              'Aucun historique pour le moment',
              style: AppTypography.meta.copyWith(
                color: AppColors.textSecondary,
                fontSize: 14,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorState() {
    return SizedBox(
      height: 160,
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.cloud_off_rounded,
              size: 32,
              color: AppColors.textSecondary.withValues(alpha: 0.5),
            ),
            const SizedBox(height: 8),
            Text(
              _error ?? 'Données indisponibles',
              style: AppTypography.meta.copyWith(
                color: AppColors.textSecondary,
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 10),
            GestureDetector(
              onTap: _load,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: AppColors.textPrimary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  'Réessayer',
                  style: AppTypography.meta.copyWith(
                    color: AppColors.textPrimary,
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Chart painter
// ---------------------------------------------------------------------------

class _WalletChartPainter extends CustomPainter {
  _WalletChartPainter({required this.values, required this.lineColor});

  final List<double> values;
  final Color lineColor;

  @override
  void paint(Canvas canvas, Size size) {
    if (values.length < 2) return;

    final n = values.length;
    final minY = values.reduce(math.min);
    final maxY = values.reduce(math.max);
    final range = (maxY - minY).clamp(0.001, double.infinity);

    final xs = <double>[];
    final ys = <double>[];
    for (int i = 0; i < n; i++) {
      xs.add(size.width * (i / (n - 1)));
      ys.add(size.height -
          ((values[i] - minY) / range) * size.height * 0.88 -
          size.height * 0.06);
    }

    final path = Path()..moveTo(xs[0], ys[0]);
    const tension = 1 / 6.0;
    for (int i = 0; i < n - 1; i++) {
      final x0 = xs[i], y0 = ys[i];
      final x1 = xs[i + 1], y1 = ys[i + 1];
      final xPrev = i > 0 ? xs[i - 1] : x0;
      final yPrev = i > 0 ? ys[i - 1] : y0;
      final xNext = i + 2 < n ? xs[i + 2] : x1;
      final yNext = i + 2 < n ? ys[i + 2] : y1;
      path.cubicTo(
        x0 + (x1 - xPrev) * tension,
        y0 + (y1 - yPrev) * tension,
        x1 - (xNext - x0) * tension,
        y1 - (yNext - y0) * tension,
        x1,
        y1,
      );
    }

    canvas.drawPath(
      path,
      Paint()
        ..color = lineColor
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.5
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round
        ..isAntiAlias = true,
    );

    final fillPath = Path.from(path)
      ..lineTo(xs.last, size.height)
      ..lineTo(xs.first, size.height)
      ..close();
    canvas.drawPath(
      fillPath,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            lineColor.withValues(alpha: 0.18),
            lineColor.withValues(alpha: 0.0),
          ],
        ).createShader(Rect.fromLTWH(0, 0, size.width, size.height))
        ..style = PaintingStyle.fill,
    );

    final lastX = xs.last;
    final lastY = ys.last;
    canvas.drawCircle(
      Offset(lastX, lastY),
      4,
      Paint()..color = lineColor,
    );
    canvas.drawCircle(
      Offset(lastX, lastY),
      7,
      Paint()
        ..color = lineColor.withValues(alpha: 0.20)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2,
    );
  }

  @override
  bool shouldRepaint(covariant _WalletChartPainter old) =>
      old.values.length != values.length || old.lineColor != lineColor;
}

// ---------------------------------------------------------------------------
// Shimmer chart painter (wavy placeholder)
// ---------------------------------------------------------------------------

class _ShimmerChartPainter extends CustomPainter {
  _ShimmerChartPainter({required this.color});

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final path = Path();
    final n = 40;
    final w = size.width;
    final h = size.height;
    path.moveTo(0, h * 0.55);
    for (int i = 1; i <= n; i++) {
      final x = w * (i / n);
      final base = h * 0.55;
      final wave = math.sin(i * 0.5) * h * 0.18 +
          math.cos(i * 0.3) * h * 0.10;
      path.lineTo(x, base - wave);
    }

    canvas.drawPath(
      path,
      Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.5
        ..strokeCap = StrokeCap.round
        ..isAntiAlias = true,
    );

    final fillPath = Path.from(path)
      ..lineTo(w, h)
      ..lineTo(0, h)
      ..close();
    canvas.drawPath(
      fillPath,
      Paint()
        ..color = color.withValues(alpha: color.a * 0.3)
        ..style = PaintingStyle.fill,
    );
  }

  @override
  bool shouldRepaint(covariant _ShimmerChartPainter old) =>
      old.color != color;
}
