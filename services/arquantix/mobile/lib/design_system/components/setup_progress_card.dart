import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/kalai_icons.dart';
import 'app_primary_button.dart';
import 'app_tag.dart';
import 'kalai_icon.dart';

// ---------------------------------------------------------------------------
// Data model
// ---------------------------------------------------------------------------

enum SetupStepStatus { completed, inProgress, pending }

class SetupStep {
  const SetupStep({
    required this.title,
    required this.status,
    this.subtitle,
    this.tag,
    this.icon,
    this.onTap,
  });

  final String title;
  final String? subtitle;
  final String? tag;
  final SetupStepStatus status;
  final IconData? icon;
  final VoidCallback? onTap;
}

// ---------------------------------------------------------------------------
// SetupProgressCard
// ---------------------------------------------------------------------------

/// Card combining a circular progress ring, title, CTA and a vertical list
/// of setup steps (completed / in-progress / pending).
///
/// Matches the Figma "Finish setting up" component.
class SetupProgressCard extends StatelessWidget {
  const SetupProgressCard({
    super.key,
    required this.currentStep,
    required this.totalSteps,
    required this.title,
    required this.steps,
    this.subtitle,
    this.ctaLabel,
    this.onCtaPressed,
  });

  final int currentStep;
  final int totalSteps;
  final String title;
  final String? subtitle;
  final String? ctaLabel;
  final VoidCallback? onCtaPressed;
  final List<SetupStep> steps;

  @override
  Widget build(BuildContext context) {
    // Un seul bloc (anneau + titre + CTA + liste), sans second cartouche blanc ni traits entre les lignes.
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Padding(
            padding: EdgeInsets.fromLTRB(
              24,
              28,
              24,
              steps.isEmpty ? 28 : 20,
            ),
            child: Column(
              children: [
                _ProgressRing(
                  current: currentStep,
                  total: totalSteps,
                ),
                const SizedBox(height: 20),
                Text(
                  title,
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.26,
                    height: 28 / 22,
                    color: AppColors.textPrimary,
                  ),
                ),
                if (subtitle != null && subtitle!.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    subtitle!,
                    textAlign: TextAlign.center,
                    style: GoogleFonts.inter(
                      fontSize: 15,
                      fontWeight: FontWeight.w400,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
                if (ctaLabel != null) ...[
                  const SizedBox(height: 16),
                  AppPrimaryButton(
                    label: ctaLabel!,
                    onPressed: onCtaPressed,
                    shrinkWrap: true,
                  ),
                ],
              ],
            ),
          ),
          if (steps.isNotEmpty)
            Padding(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.s4,
                0,
                AppSpacing.s4,
                16,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  for (var i = 0; i < steps.length; i++) ...[
                    if (i > 0) const SizedBox(height: AppSpacing.xxl),
                    _SetupStepRow(step: steps[i]),
                  ],
                ],
              ),
            ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Progress ring
// ---------------------------------------------------------------------------

class _ProgressRing extends StatelessWidget {
  const _ProgressRing({required this.current, required this.total});

  final int current;
  final int total;

  @override
  Widget build(BuildContext context) {
    final progress = total > 0 ? current / total : 0.0;

    return SizedBox(
      width: 72,
      height: 72,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CustomPaint(
            size: const Size(72, 72),
            painter: _RingPainter(
              progress: progress,
              trackColor: const Color(0xFFE5E5EA),
              progressColor: AppColors.indigo,
              strokeWidth: 4.5,
            ),
          ),
          Text(
            '$current/$total',
            style: GoogleFonts.inter(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.43,
              color: AppColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }
}

/// Anneau de progression 0–100 % (activation journey, métriques pondérées).
class ProgressRingPercent extends StatelessWidget {
  const ProgressRingPercent({super.key, required this.percent});

  final int percent;

  @override
  Widget build(BuildContext context) {
    final p = (percent.clamp(0, 100)) / 100.0;
    final label = '${percent.clamp(0, 100)}%';
    return SizedBox(
      width: 72,
      height: 72,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CustomPaint(
            size: const Size(72, 72),
            painter: _RingPainter(
              progress: p,
              trackColor: const Color(0xFFE5E5EA),
              progressColor: AppColors.indigo,
              strokeWidth: 4.5,
            ),
          ),
          Text(
            label,
            style: GoogleFonts.inter(
              fontSize: label.length > 4 ? 14 : 18,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.43,
              color: AppColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  _RingPainter({
    required this.progress,
    required this.trackColor,
    required this.progressColor,
    required this.strokeWidth,
  });

  final double progress;
  final Color trackColor;
  final Color progressColor;
  final double strokeWidth;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width - strokeWidth) / 2;
    const startAngle = -math.pi / 2;

    // Track
    final trackPaint = Paint()
      ..color = trackColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;
    canvas.drawCircle(center, radius, trackPaint);

    // Progress arc
    if (progress > 0) {
      final progressPaint = Paint()
        ..color = progressColor
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeWidth
        ..strokeCap = StrokeCap.round;
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        startAngle,
        2 * math.pi * progress,
        false,
        progressPaint,
      );
    }
  }

  @override
  bool shouldRepaint(_RingPainter oldDelegate) =>
      oldDelegate.progress != progress;
}

// ---------------------------------------------------------------------------
// Step row
// ---------------------------------------------------------------------------

class _SetupStepRow extends StatelessWidget {
  const _SetupStepRow({required this.step});

  final SetupStep step;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: step.onTap,
      borderRadius: BorderRadius.circular(20),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        child: Row(
          children: [
            _buildLeadingIcon(),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          step.title,
                          style: GoogleFonts.inter(
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                            letterSpacing: -0.31,
                            color: AppColors.textPrimary,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (step.tag != null) ...[
                        const SizedBox(width: 8),
                        AppTag(
                          label: step.tag!,
                          variant: AppTagVariant.article,
                        ),
                      ],
                    ],
                  ),
                  if (step.subtitle != null) ...[
                    const SizedBox(height: 2),
                    Text(
                      step.subtitle!,
                      style: GoogleFonts.inter(
                        fontSize: 13,
                        fontWeight: FontWeight.w400,
                        color: AppColors.textSecondary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ],
              ),
            ),
            if (step.onTap != null)
              const Padding(
                padding: EdgeInsets.only(left: 8),
                child: KalaiIcon(
                  KalaiIcons.chevronRight,
                  size: 20,
                  color: Color(0xFFC7C7CC),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildLeadingIcon() {
    switch (step.status) {
      case SetupStepStatus.completed:
        return Container(
          width: 32,
          height: 32,
          decoration: const BoxDecoration(
            color: Color(0xFF34C759),
            shape: BoxShape.circle,
          ),
          child: const KalaiIcon(KalaiIcons.check, size: 18, color: Colors.white),
        );

      case SetupStepStatus.inProgress:
        return SizedBox(
          width: 32,
          height: 32,
          child: Stack(
            alignment: Alignment.center,
            children: [
              SizedBox(
                width: 28,
                height: 28,
                child: CircularProgressIndicator(
                  value: 0.5,
                  strokeWidth: 2.5,
                  backgroundColor: const Color(0xFFE5E5EA),
                  valueColor: const AlwaysStoppedAnimation<Color>(
                      AppColors.indigo),
                ),
              ),
              if (step.icon != null)
                Icon(step.icon, size: 14, color: AppColors.textSecondary),
            ],
          ),
        );

      case SetupStepStatus.pending:
        return Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            color: const Color(0xFFF5F5F5),
            borderRadius: BorderRadius.circular(8),
          ),
          child: step.icon != null
              ? Icon(step.icon, size: 18, color: AppColors.textSecondary)
              : const KalaiIcon(
                  KalaiIcons.photo,
                  size: 18,
                  color: AppColors.textSecondary,
                ),
        );
    }
  }
}
