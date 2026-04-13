import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_typography.dart';

/// Ligne temps de lecture (Figma `ReadingTime.tsx`) : horloge 12px indigo + texte 13px gris.
class DsNewsReadingTime extends StatelessWidget {
  const DsNewsReadingTime({
    super.key,
    required this.label,
    this.iconColor = AppColors.indigo,
  });

  /// Texte affiché (ex. « 3 minutes » ou « Reading time »).
  final String label;

  /// Couleur du trait d’horloge (Figma `#6155F5`).
  final Color iconColor;

  static const double _iconSize = 12;
  static const double _gap = 4;

  @override
  Widget build(BuildContext context) {
    final textStyle = AppTypography.itemSupporting.copyWith(
      fontWeight: FontWeight.w400,
      letterSpacing: -0.08,
      height: 18 / 13,
      color: AppColors.gray,
    );

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: _iconSize,
          height: _iconSize,
          child: CustomPaint(
            painter: _NewsClockPainter(color: iconColor),
          ),
        ),
        const SizedBox(width: _gap),
        Flexible(
          child: Text(
            label,
            style: textStyle,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}

/// Horloge minimaliste (cercle + aiguilles) alignée Figma ReadingTime.
class _NewsClockPainter extends CustomPainter {
  _NewsClockPainter({required this.color});

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final stroke = 1.2;
    final cx = size.width / 2;
    final cy = size.height / 2;
    final r = (size.shortestSide / 2) - stroke;

    final circlePaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round;

    canvas.drawCircle(Offset(cx, cy), r, circlePaint);

    final handPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round;

    // Aiguilles type Figma (petite + grande).
    canvas.drawLine(
      Offset(cx, cy),
      Offset(cx, cy - r * 0.45),
      handPaint,
    );
    canvas.drawLine(
      Offset(cx, cy),
      Offset(cx + r * 0.35, cy + r * 0.25),
      handPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _NewsClockPainter oldDelegate) =>
      oldDelegate.color != color;
}
