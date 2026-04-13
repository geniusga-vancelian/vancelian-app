import 'package:flutter/material.dart';

/// Caret marché type Figma **Tags** (Vector 28) : **9×6 px** ; écart avec le libellé **4 px** ([AppSpacing.s1]).
///
/// [up] : triangle pointe vers le haut (gain) ; false : pointe vers le bas (perte).
class MarketTrendCaret extends StatelessWidget {
  const MarketTrendCaret({
    super.key,
    required this.up,
    required this.color,
  });

  final bool up;
  final Color color;

  static const double width = 9;
  static const double height = 6;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      height: height,
      child: CustomPaint(
        painter: _MarketTrendCaretPainter(up: up, color: color),
      ),
    );
  }
}

class _MarketTrendCaretPainter extends CustomPainter {
  const _MarketTrendCaretPainter({required this.up, required this.color});

  final bool up;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = color;
    final path = Path();
    if (up) {
      path
        ..moveTo(0, size.height)
        ..lineTo(size.width * 0.5, 0)
        ..lineTo(size.width, size.height)
        ..close();
    } else {
      path
        ..moveTo(0, 0)
        ..lineTo(size.width * 0.5, size.height)
        ..lineTo(size.width, 0)
        ..close();
    }
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _MarketTrendCaretPainter oldDelegate) =>
      oldDelegate.up != up || oldDelegate.color != color;
}
