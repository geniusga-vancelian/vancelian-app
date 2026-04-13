import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Uniform spinning arc indicator.
///
/// Draws a smooth arc that rotates at constant speed with a gradient tail,
/// similar to the Cursor IDE step loader.
class DotSpinner extends StatefulWidget {
  const DotSpinner({
    super.key,
    this.size = 20,
    this.color = Colors.white,
    this.strokeWidth,
  });

  final double size;
  final Color color;
  final double? strokeWidth;

  @override
  State<DotSpinner> createState() => _DotSpinnerState();
}

class _DotSpinnerState extends State<DotSpinner>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 750),
    )..repeat();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _ctrl,
      builder: (_, __) {
        return CustomPaint(
          size: Size.square(widget.size),
          painter: _ArcSpinnerPainter(
            progress: _ctrl.value,
            color: widget.color,
            strokeWidth: widget.strokeWidth ?? (widget.size * 0.12),
          ),
        );
      },
    );
  }
}

class _ArcSpinnerPainter extends CustomPainter {
  _ArcSpinnerPainter({
    required this.progress,
    required this.color,
    required this.strokeWidth,
  });

  final double progress;
  final Color color;
  final double strokeWidth;

  static const int _segments = 32;
  static const double _arcLength = 0.75 * 2 * math.pi;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width - strokeWidth) / 2;
    final startAngle = progress * 2 * math.pi - math.pi / 2;
    const segmentSweep = _arcLength / _segments;

    for (int i = 0; i < _segments; i++) {
      final t = i / _segments;
      final opacity = t * t;
      final paint = Paint()
        ..color = color.withValues(alpha: opacity)
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeWidth
        ..strokeCap = StrokeCap.round;

      final angle = startAngle + i * segmentSweep;
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        angle,
        segmentSweep + 0.02,
        false,
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(_ArcSpinnerPainter old) => old.progress != progress;
}
