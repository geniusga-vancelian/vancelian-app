import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'ds_timeline_step_dot.dart';
import 'step_item.dart';

/// Module "Steps" (itinéraire) : carte arrondie, timeline pointillée + texte direct.
///
/// Design aligné Figma « Funding Timeline » :
/// - Carte blanche `AppRadius.xxl`, padding intérieur **16 px**
/// - Pastille gauche **20×20 px**, alignée sur la **1re ligne** du titre (haut de ligne)
/// - **28 px** entre la description d’une étape et le titre de la suivante ([AppSpacing.s7])
/// - Ligne verticale **pointillée** entre les pastilles ; **aucun** segment sous la dernière pastille
/// - Tag « EN COURS » : **4 px** après le titre (même ligne si place), `labelEmphasized` + fond clair
/// - Titre = `itemPrimary`, description = `itemSupporting`, gap titre → texte **4 px**
class StepsModuleWidget extends StatelessWidget {
  const StepsModuleWidget({
    required this.title,
    required this.steps,
    super.key,
    this.subtitle,
    this.rightLabel,
    this.onStepTap,
    this.horizontalMargin,
  });

  final String title;
  final String? subtitle;
  final String? rightLabel;
  final List<StepItem> steps;
  final void Function(int index)? onStepTap;
  final double? horizontalMargin;

  static const double _defaultHorizontalMargin = 16;

  static StepsModuleWidget? fromJson(dynamic json,
      {void Function(int index)? onStepTap}) {
    if (json is! Map<String, dynamic>) return null;
    if (json['type'] != 'steps') return null;
    final title = json['title'] as String?;
    if (title == null || title.isEmpty) return null;
    final items = StepItem.listFromJson(json['items']);
    return StepsModuleWidget(
      title: title,
      steps: items,
      rightLabel: json['rightLabel'] as String?,
      subtitle: json['subtitle'] as String?,
      onStepTap: onStepTap,
    );
  }

  @override
  Widget build(BuildContext context) {
    final margin = horizontalMargin ?? _defaultHorizontalMargin;
    if (steps.isEmpty) {
      return Padding(
        padding: EdgeInsets.symmetric(horizontal: margin),
        child: Text(
          'No steps yet',
          style:
              AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary),
        ),
      );
    }

    final statuses = _resolveStatuses(steps);

    return Padding(
      padding: EdgeInsets.symmetric(horizontal: margin),
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.white,
          borderRadius: BorderRadius.circular(AppRadius.xxl),
          boxShadow: const [
            BoxShadow(
              blurRadius: 20,
              spreadRadius: -10,
              color: Color(0x1F000000),
            ),
          ],
        ),
        padding: const EdgeInsets.all(AppSpacing.s4), // 16 px
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: List.generate(steps.length, (i) {
            return _StepRow(
              step: steps[i],
              status: statuses[i],
              isFirst: i == 0,
              isLast: i == steps.length - 1,
              onTap: onStepTap != null ? () => onStepTap!(i) : null,
            );
          }),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Résolution des statuts
// ---------------------------------------------------------------------------

List<DsTimelineStepStatus> _resolveStatuses(List<StepItem> steps) {
  final firstPending = steps.indexWhere((s) => !s.isCompleted);
  return List<DsTimelineStepStatus>.generate(steps.length, (i) {
    if (steps[i].isCompleted) return DsTimelineStepStatus.completed;
    if (firstPending == -1) return DsTimelineStepStatus.completed;
    if (i == firstPending) return DsTimelineStepStatus.active;
    return DsTimelineStepStatus.upcoming;
  });
}

// ---------------------------------------------------------------------------
// Step row
// ---------------------------------------------------------------------------

/// Diamètre exact de la pastille d’étape (avatar gauche).
const double _kDotSize = 20;

/// Espace horizontal entre la colonne timeline et le texte.
const double _kDotTextGap = 16;

class _StepRow extends StatelessWidget {
  const _StepRow({
    required this.step,
    required this.status,
    required this.isFirst,
    required this.isLast,
    this.onTap,
  });

  final StepItem step;
  final DsTimelineStepStatus status;
  final bool isFirst;
  final bool isLast;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return IntrinsicHeight(
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _TimelineSpine(status: status, isFirst: isFirst, isLast: isLast),
            const SizedBox(width: _kDotTextGap),
            Expanded(child: _buildContent()),
          ],
        ),
      ),
    );
  }

  Widget _buildContent() {
    final desc = step.description?.trim();
    final statusLabel = step.date?.trim();
    final titleStyle = AppTypography.itemPrimary.copyWith(
      color: AppColors.textPrimary,
    );

    return Padding(
      padding: EdgeInsets.only(bottom: isLast ? 0 : AppSpacing.s7),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Titre + tag « EN COURS » : 4 px après le titre (Wrap), pas poussé à droite.
          Wrap(
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: AppSpacing.s1,
            runSpacing: AppSpacing.s1,
            children: [
              Text(
                step.title,
                style: titleStyle,
                strutStyle: StrutStyle.fromTextStyle(
                  titleStyle,
                  forceStrutHeight: true,
                ),
              ),
              if (status == DsTimelineStepStatus.active) const _EnCoursTag(),
            ],
          ),

          if (statusLabel != null && statusLabel.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.s1),
            Text(
              statusLabel,
              style: AppTypography.itemSupporting.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
          if (desc != null && desc.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.s1),
            Text(
              desc,
              style: AppTypography.itemSupporting.copyWith(
                color: AppColors.textSecondary,
                height: 1.4,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Tag « EN COURS » : label/Emphasized SM + fond gris clair (Figma Gray5 fill).
class _EnCoursTag extends StatelessWidget {
  const _EnCoursTag();

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: AppColors.progressTrackLight,
        borderRadius: BorderRadius.circular(AppRadius.sm),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
        child: Text(
          'EN COURS',
          style: AppTypography.labelEmphasized.copyWith(
            color: AppColors.textPrimary,
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Timeline : pastille 20×20 en haut + pointillés (jamais sous la dernière pastille)
// ---------------------------------------------------------------------------

class _TimelineSpine extends StatelessWidget {
  const _TimelineSpine({
    required this.status,
    required this.isFirst,
    required this.isLast,
  });

  final DsTimelineStepStatus status;
  final bool isFirst;
  final bool isLast;

  static double get _lineLeft => (_kDotSize - 2) / 2;

  static double get _dotCenterY => _kDotSize / 2;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: _kDotSize,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final h = constraints.maxHeight;
          return SizedBox(
            width: _kDotSize,
            height: h.isFinite ? h : _kDotSize,
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                // Segment au-dessus de la pastille (depuis l’étape précédente jusqu’au centre du point).
                if (!isFirst)
                  Positioned(
                    left: _lineLeft,
                    top: 0,
                    width: 2,
                    height: _dotCenterY,
                    child: CustomPaint(painter: _DottedLinePainter()),
                  ),
                // Segment sous la pastille (du centre du point vers l’étape suivante) — absent sur la dernière ligne.
                if (!isLast)
                  Positioned(
                    left: _lineLeft,
                    top: _dotCenterY,
                    width: 2,
                    bottom: 0,
                    child: CustomPaint(painter: _DottedLinePainter()),
                  ),
                Positioned(
                  top: 0,
                  left: 0,
                  width: _kDotSize,
                  height: _kDotSize,
                  child: DsTimelineStepDot(
                    status: status,
                    size: _kDotSize,
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

/// Ligne verticale en points rapprochés (pas un trait plein).
class _DottedLinePainter extends CustomPainter {
  _DottedLinePainter();

  static const double _dotRadius = 1.1;
  static const double _gap = 2.5;
  static final Paint _paint = Paint()..color = AppColors.border;

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    var y = _dotRadius;
    while (y < size.height - _dotRadius) {
      canvas.drawCircle(Offset(cx, y), _dotRadius, _paint);
      y += _dotRadius * 2 + _gap;
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
