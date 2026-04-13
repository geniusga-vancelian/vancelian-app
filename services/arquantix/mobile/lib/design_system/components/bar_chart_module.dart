import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Data point for [BarChartModule].
class BarChartData {
  const BarChartData({required this.label, required this.value});

  final String label;
  final double value;
}

/// Vertical bar chart with Y-axis legend.
///
/// Figma spec:
/// - Bars: max-width 24px, borderRadius 8, gap 8px between bars
/// - Labels: 10px, Public Sans Regular
/// - Y legend: min/max values, 10px, right-aligned
/// - Height default: 144px
class BarChartModule extends StatelessWidget {
  const BarChartModule({
    super.key,
    required this.data,
    this.height = 144,
    this.barColor = Colors.white,
    this.labelColor = Colors.white,
    this.maxValue,
    this.minValue,
    this.showYLegend = true,
    this.valueFormatter,
  });

  final List<BarChartData> data;
  final double height;
  final Color barColor;
  final Color labelColor;
  final double? maxValue;
  final double? minValue;
  final bool showYLegend;

  /// Formats Y legend values. Defaults to `value.toStringAsFixed(2) + ' €'`.
  final String Function(double)? valueFormatter;

  @override
  Widget build(BuildContext context) {
    if (data.isEmpty) return SizedBox(height: height);

    final max = maxValue ?? data.map((d) => d.value).reduce(math.max);
    final min = minValue ?? data.map((d) => d.value).reduce(math.min);
    final range = (max - min).abs() < 1e-9 ? 1.0 : (max - min);

    final fmt = valueFormatter ?? (v) => '${v.toStringAsFixed(2)} €';

    return SizedBox(
      height: height,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(child: _buildBars(min, range)),
          if (showYLegend) ...[
            const SizedBox(width: 12),
            _buildYLegend(max, min, fmt),
          ],
        ],
      ),
    );
  }

  Widget _buildBars(double min, double range) {
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          for (int i = 0; i < data.length; i++) ...[
            if (i > 0) const SizedBox(width: 8),
            Expanded(child: _buildBar(data[i], min, range)),
          ],
        ],
      ),
    );
  }

  Widget _buildBar(BarChartData item, double min, double range) {
    final pct = ((item.value - min) / range).clamp(0.0, 1.0);
    final barFraction = math.max(pct, 0.08);

    return Column(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        Flexible(
          child: FractionallySizedBox(
            heightFactor: barFraction,
            child: Container(
              constraints: const BoxConstraints(maxWidth: 24),
              decoration: BoxDecoration(
                color: barColor,
                borderRadius: BorderRadius.circular(8),
              ),
            ),
          ),
        ),
        const SizedBox(height: 4),
        SizedBox(
          height: 16,
          child: Center(
            child: Text(
              item.label,
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w400,
                color: labelColor,
                height: 12 / 10,
              ),
              maxLines: 1,
              overflow: TextOverflow.clip,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildYLegend(double max, double min, String Function(double) fmt) {
    return SizedBox(
      width: 40,
      child: Padding(
        padding: const EdgeInsets.only(top: 27, bottom: 16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              fmt(max),
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w400,
                color: labelColor,
                height: 12 / 10,
              ),
              maxLines: 1,
            ),
            Text(
              fmt(min),
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w400,
                color: labelColor,
                height: 12 / 10,
              ),
              maxLines: 1,
            ),
          ],
        ),
      ),
    );
  }
}
