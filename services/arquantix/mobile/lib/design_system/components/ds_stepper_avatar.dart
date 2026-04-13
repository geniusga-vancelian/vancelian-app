import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import 'ds_circular_progress.dart';

/// Statut du stepper Figma (`StepperAvatar.tsx`).
enum DsStepperAvatarStatus {
  success,
  error,
  warning,
  info,
}

/// Anneau de progression + icône centrale — export Figma module validation.
///
/// Erreur : piste #E5E5EA, arc [couleur statut], **croix** au centre en #FF2D55
/// (pas de disque plein).
class DsStepperAvatar extends StatelessWidget {
  const DsStepperAvatar({
    super.key,
    this.status = DsStepperAvatarStatus.error,
    this.progress = 100,
    this.size = 56,
    this.strokeWidth = 4,
    this.icon,
  });

  final DsStepperAvatarStatus status;
  final double progress;
  final double size;
  final double strokeWidth;
  final Widget? icon;

  static const Color _warningFigma = Color(0xFFFF9500);

  Color get _statusColor => switch (status) {
        DsStepperAvatarStatus.success => AppColors.semanticPositive,
        DsStepperAvatarStatus.error => AppColors.semanticNegative,
        DsStepperAvatarStatus.warning => _warningFigma,
        DsStepperAvatarStatus.info => AppColors.actionPrimaryBlue,
      };

  @override
  Widget build(BuildContext context) {
    final inner = size * 0.42;
    return DsCircularProgress(
      progress: progress,
      size: size,
      strokeWidth: strokeWidth,
      backgroundColor: AppColors.progressTrackLight,
      progressColor: _statusColor,
      icon: icon ??
          SizedBox(
            width: inner,
            height: inner,
            child: CustomPaint(
              painter: _StepperCenterIconPainter(
                status: status,
                color: _statusColor,
              ),
            ),
          ),
    );
  }
}

class _StepperCenterIconPainter extends CustomPainter {
  _StepperCenterIconPainter({
    required this.status,
    required this.color,
  });

  final DsStepperAvatarStatus status;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    switch (status) {
      case DsStepperAvatarStatus.error:
        paint.strokeWidth = w * 0.2;
        final pad = w * 0.18;
        canvas.drawLine(Offset(pad, pad), Offset(w - pad, h - pad), paint);
        canvas.drawLine(Offset(w - pad, pad), Offset(pad, h - pad), paint);
        break;
      case DsStepperAvatarStatus.success:
        paint.strokeWidth = w * 0.14;
        final path = Path()
          ..moveTo(w * 0.2, h * 0.52)
          ..lineTo(w * 0.42, h * 0.72)
          ..lineTo(w * 0.82, h * 0.28);
        canvas.drawPath(path, paint);
        break;
      case DsStepperAvatarStatus.warning:
        paint.strokeWidth = w * 0.12;
        final cx = w / 2;
        canvas.drawLine(Offset(cx, h * 0.22), Offset(cx, h * 0.62), paint);
        final fill = Paint()
          ..color = color
          ..style = PaintingStyle.fill;
        canvas.drawCircle(Offset(cx, h * 0.78), w * 0.06, fill);
        break;
      case DsStepperAvatarStatus.info:
        final cx = w / 2;
        final fill = Paint()
          ..color = color
          ..style = PaintingStyle.fill;
        canvas.drawCircle(Offset(cx, h * 0.28), w * 0.07, fill);
        paint.strokeWidth = w * 0.12;
        canvas.drawLine(Offset(cx, h * 0.45), Offset(cx, h * 0.82), paint);
        break;
    }
  }

  @override
  bool shouldRepaint(covariant _StepperCenterIconPainter oldDelegate) {
    return oldDelegate.status != status || oldDelegate.color != color;
  }
}
