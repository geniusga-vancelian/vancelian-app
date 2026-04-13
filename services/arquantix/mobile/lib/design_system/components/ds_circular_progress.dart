import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';

/// Indicateur circulaire Figma `CircularProgress` (piste #E5E5EA, progression #34C759).
class DsCircularProgress extends StatelessWidget {
  const DsCircularProgress({
    super.key,
    this.progress = 100,
    this.icon,
    this.size = 56,
    this.strokeWidth = 4,
    this.backgroundColor = AppColors.progressTrackLight,
    this.progressColor = AppColors.semanticPositive,
  });

  /// 0–100, comme le composant React du module Figma.
  final double progress;
  final Widget? icon;
  final double size;
  final double strokeWidth;
  final Color backgroundColor;
  final Color progressColor;

  @override
  Widget build(BuildContext context) {
    final p = (progress / 100).clamp(0.0, 1.0);
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CustomPaint(
            size: Size(size, size),
            painter: _RingPainter(
              progress: p,
              strokeWidth: strokeWidth,
              backgroundColor: backgroundColor,
              progressColor: progressColor,
            ),
          ),
          if (icon != null) icon!,
        ],
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  _RingPainter({
    required this.progress,
    required this.strokeWidth,
    required this.backgroundColor,
    required this.progressColor,
  });

  final double progress;
  final double strokeWidth;
  final Color backgroundColor;
  final Color progressColor;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.shortestSide - strokeWidth) / 2;

    final bgPaint = Paint()
      ..color = backgroundColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final fgPaint = Paint()
      ..color = progressColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    canvas.drawCircle(center, radius, bgPaint);

    final sweep = 2 * math.pi * progress;
    if (sweep <= 0) return;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -math.pi / 2,
      sweep,
      false,
      fgPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _RingPainter oldDelegate) {
    return oldDelegate.progress != progress ||
        oldDelegate.strokeWidth != strokeWidth ||
        oldDelegate.backgroundColor != backgroundColor ||
        oldDelegate.progressColor != progressColor;
  }
}
