import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';

/// Curseur de sélection de valeur continue.
///
/// Style aligné sur le DS : track arrondi, thumb indigo,
/// zone active en indigo, zone inactive en gris clair.
class AppSlider extends StatelessWidget {
  const AppSlider({
    super.key,
    required this.value,
    required this.onChanged,
    this.min = 0.0,
    this.max = 1.0,
    this.divisions,
    this.label,
    this.enabled = true,
  });

  final double value;
  final ValueChanged<double>? onChanged;
  final double min;
  final double max;
  final int? divisions;
  final String? label;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return SliderTheme(
      data: SliderThemeData(
        activeTrackColor: AppColors.indigo,
        inactiveTrackColor: AppColors.placeholderBg,
        thumbColor: AppColors.white,
        overlayColor: AppColors.indigo.withValues(alpha: 0.12),
        trackHeight: 4,
        thumbShape: const _ThumbShape(),
        overlayShape: const RoundSliderOverlayShape(overlayRadius: 20),
        valueIndicatorColor: AppColors.indigo,
        valueIndicatorTextStyle: const TextStyle(
          color: AppColors.white,
          fontSize: 13,
          fontWeight: FontWeight.w600,
        ),
        showValueIndicator: ShowValueIndicator.onlyForDiscrete,
      ),
      child: Slider(
        value: value,
        min: min,
        max: max,
        divisions: divisions,
        label: label,
        onChanged: enabled ? onChanged : null,
      ),
    );
  }
}

class _ThumbShape extends SliderComponentShape {
  const _ThumbShape();

  @override
  Size getPreferredSize(bool isEnabled, bool isDiscrete) =>
      const Size.fromRadius(10);

  @override
  void paint(
    PaintingContext context,
    Offset center, {
    required Animation<double> activationAnimation,
    required Animation<double> enableAnimation,
    required bool isDiscrete,
    required TextPainter labelPainter,
    required RenderBox parentBox,
    required SliderThemeData sliderTheme,
    required TextDirection textDirection,
    required double value,
    required double textScaleFactor,
    required Size sizeWithOverflow,
  }) {
    final canvas = context.canvas;

    final shadowPaint = Paint()
      ..color = Colors.black.withValues(alpha: 0.15)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3);
    canvas.drawCircle(center + const Offset(0, 1), 10, shadowPaint);

    final fillPaint = Paint()
      ..color = sliderTheme.thumbColor ?? AppColors.white
      ..style = PaintingStyle.fill;
    canvas.drawCircle(center, 10, fillPaint);

    final borderPaint = Paint()
      ..color = AppColors.indigo
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;
    canvas.drawCircle(center, 9, borderPaint);
  }
}
