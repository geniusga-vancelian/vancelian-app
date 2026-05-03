import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/kalai_icons.dart';
import 'kalai_icon.dart';

/// Statut d'une pastille d'étape (itinéraire / steps) — aligné Figma StepStatus.
enum DsTimelineStepStatus {
  completed,
  active,
  upcoming,
}

/// Pastille timeline : check vert, arc actif (spinner), anneau vide à venir.
///
/// Taille par défaut **20 px** (Figma « Funding Timeline / itinéraire »).
class DsTimelineStepDot extends StatefulWidget {
  const DsTimelineStepDot({
    super.key,
    required this.status,
    this.size = 20,
  });

  final DsTimelineStepStatus status;
  final double size;

  @override
  State<DsTimelineStepDot> createState() => _DsTimelineStepDotState();
}

class _DsTimelineStepDotState extends State<DsTimelineStepDot>
    with SingleTickerProviderStateMixin {
  AnimationController? _ctrl;

  @override
  void initState() {
    super.initState();
    _syncAnimation();
  }

  @override
  void didUpdateWidget(covariant DsTimelineStepDot oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.status != widget.status) _syncAnimation();
  }

  void _syncAnimation() {
    if (widget.status == DsTimelineStepStatus.active) {
      _ctrl ??= AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 1200),
      );
      _ctrl!.repeat();
    } else {
      _ctrl?.stop();
    }
  }

  @override
  void dispose() {
    _ctrl?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.size;
    switch (widget.status) {
      case DsTimelineStepStatus.completed:
        return Container(
          width: s,
          height: s,
          decoration: const BoxDecoration(
            shape: BoxShape.circle,
            color: AppColors.semanticPositive,
          ),
          alignment: Alignment.center,
          child: KalaiIcon(KalaiIcons.check, size: s * 0.6, color: AppColors.white),
        );

      case DsTimelineStepStatus.active:
        return SizedBox(
          width: s,
          height: s,
          child: AnimatedBuilder(
            animation: _ctrl!,
            builder: (_, __) => CustomPaint(
              painter: _ArcSpinnerPainter(
                progress: _ctrl!.value,
                color: AppColors.textPrimary,
                strokeWidth: 2,
              ),
            ),
          ),
        );

      case DsTimelineStepStatus.upcoming:
        return Container(
          width: s,
          height: s,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: AppColors.white,
            border: Border.all(color: AppColors.border, width: 1),
          ),
        );
    }
  }
}

/// Arc animé ¾ tour qui tourne.
class _ArcSpinnerPainter extends CustomPainter {
  _ArcSpinnerPainter({
    required this.progress,
    required this.color,
    required this.strokeWidth,
  });

  final double progress;
  final Color color;
  final double strokeWidth;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    const sweepAngle = math.pi * 1.5;
    final startAngle = progress * math.pi * 2 - math.pi / 2;
    canvas.drawArc(rect.deflate(strokeWidth / 2), startAngle, sweepAngle, false, paint);
  }

  @override
  bool shouldRepaint(_ArcSpinnerPainter old) => old.progress != progress;
}
