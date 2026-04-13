import 'dart:math' as math;
import 'package:flutter/material.dart';

/// Données mock pour le line chart (100 points, courbe type évolution). Calculées une seule fois.
List<double> get mockLineChartData100 {
  return _mockLineChartData100;
}

final List<double> _mockLineChartData100 = () {
  final rnd = math.Random(42);
  final points = <double>[];
  double y = 0.2;
  for (int i = 0; i < 100; i++) {
    final trend = 0.006;
    final noise = (rnd.nextDouble() - 0.5) * 0.18;
    y = y + trend + noise;
    y = y.clamp(0.0, 1.0);
    points.add(y);
  }
  return points;
}();

/// Module line chart bord à bord, épaisseur par défaut 3px, 100 points, courbe lissée (angles arrondis).
class LineChartModule extends StatelessWidget {
  const LineChartModule({
    super.key,
    this.data,
    this.height = 56,
    this.lineColor = Colors.white,
    this.strokeWidth = 2.0,
    this.paddingTop,
    this.paddingBottom,
  });

  /// Valeurs normalisées 0.0–1.0 (indice = abscisse). Si null, utilise [mockLineChartData100].
  final List<double>? data;
  final double height;
  final Color lineColor;
  final double strokeWidth;
  /// Padding au-dessus du chart. Par défaut 8.
  final double? paddingTop;
  /// Padding sous le chart. Par défaut 8.
  final double? paddingBottom;

  static const double _paddingVerticalDefault = 8;

  @override
  Widget build(BuildContext context) {
    final values = data ?? mockLineChartData100;
    final top = paddingTop ?? _paddingVerticalDefault;
    final bottom = paddingBottom ?? _paddingVerticalDefault;
    Widget chart = SizedBox(
      height: height,
      width: double.infinity,
      child: Padding(
        padding: EdgeInsets.only(top: top, bottom: bottom),
        child: LayoutBuilder(
          builder: (context, constraints) {
            return CustomPaint(
              size: Size(constraints.maxWidth, constraints.maxHeight),
              painter: _LineChartPainter(
                values: values,
                lineColor: lineColor,
                strokeWidth: strokeWidth,
              ),
            );
          },
        ),
      ),
    );
    return chart;
  }
}

class _LineChartPainter extends CustomPainter {
  _LineChartPainter({
    required this.values,
    required this.lineColor,
    required this.strokeWidth,
  });

  final List<double> values;
  final Color lineColor;
  final double strokeWidth;

  @override
  void paint(Canvas canvas, Size size) {
    if (values.isEmpty) return;
    final path = Path();
    final n = values.length;
    final minY = values.reduce(math.min);
    final maxY = values.reduce(math.max);
    final range = (maxY - minY).clamp(0.001, double.infinity);
    final xs = <double>[];
    final ys = <double>[];
    for (int i = 0; i < n; i++) {
      xs.add(size.width * (i / (n - 1)));
      ys.add(size.height - (values[i] - minY) / range * size.height);
    }
    path.moveTo(xs[0], ys[0]);
    const tension = 1 / 6.0; // Catmull-Rom pour courbe lisse et angles arrondis
    for (int i = 0; i < n - 1; i++) {
      final x0 = xs[i], y0 = ys[i];
      final x1 = xs[i + 1], y1 = ys[i + 1];
      final xPrev = i > 0 ? xs[i - 1] : x0;
      final yPrev = i > 0 ? ys[i - 1] : y0;
      final xNext = i + 2 < n ? xs[i + 2] : x1;
      final yNext = i + 2 < n ? ys[i + 2] : y1;
      final c1x = x0 + (x1 - xPrev) * tension;
      final c1y = y0 + (y1 - yPrev) * tension;
      final c2x = x1 - (xNext - x0) * tension;
      final c2y = y1 - (yNext - y0) * tension;
      path.cubicTo(c1x, c1y, c2x, c2y, x1, y1);
    }

    final paint = Paint()
      ..color = lineColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..isAntiAlias = true;

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _LineChartPainter oldDelegate) {
    return oldDelegate.values.length != values.length ||
        oldDelegate.lineColor != lineColor ||
        oldDelegate.strokeWidth != strokeWidth;
  }
}
