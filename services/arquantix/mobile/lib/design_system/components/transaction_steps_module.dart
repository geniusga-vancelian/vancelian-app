import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';
import '../atoms/app_shadow.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'dot_spinner.dart';
import 'transaction_step_item.dart';

/// Module "Transaction Steps" : carte blanche avec timeline verticale reliant
/// des étapes numérotées.
///
/// Figma spec :
///   - Card : white, radius 16, shadow 0 0 20 -10 rgba(0,0,0,0.12), padding 16
///   - Timeline circle : 20×20, bg #EFEEFE, number Inter Bold 8px #6155F5
///   - Connector : 1px wide, #EFEEFE
///   - Gap circle↔content : 8px
///   - Gap between steps : 24px
///   - Step title : Inter SemiBold 15px / lh 20 / tracking -0.23
///   - Step subtitle : Inter Regular 15px / lh 20 / tracking -0.23
///   - Step description : Inter Regular 10px / lh 13 / tracking 0.06 / #8E8E93
///   - Gap title+subtitle↔description : 4px
class TransactionStepsModule extends StatelessWidget {
  const TransactionStepsModule({
    required this.title,
    required this.steps,
    super.key,
  });

  final String title;
  final List<TransactionStepItem> steps;

  static const double _circleSize = 20;
  static const double _interStepSpacing = AppSpacing.xxl;

  static TransactionStepsModule? fromJson(dynamic json) {
    if (json is! Map<String, dynamic>) return null;
    if (json['type'] != 'transactionSteps') return null;
    final title = json['title'] as String?;
    if (title == null || title.isEmpty) return null;
    final items = TransactionStepItem.listFromJson(json['steps']);
    if (items.isEmpty) return null;
    return TransactionStepsModule(title: title, steps: items);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (title.isNotEmpty) ...[
          Text(title, style: AppTypography.title2),
          const SizedBox(height: AppSpacing.md),
        ],
        Container(
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(AppRadius.lg),
            boxShadow: AppShadow.defaultShadowList,
          ),
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (var i = 0; i < steps.length; i++)
                _buildStepRow(steps[i], isLast: i == steps.length - 1),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildStepRow(TransactionStepItem step, {required bool isLast}) {
    final row = Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _TimelineColumn(
          circleSize: _circleSize,
          step: step,
          showLine: !isLast,
        ),
        const SizedBox(width: AppSpacing.sm),
        Expanded(
          child: Padding(
            padding: EdgeInsets.only(bottom: isLast ? 0 : _interStepSpacing),
            child: _StepContent(step: step),
          ),
        ),
      ],
    );

    if (isLast) return row;
    return IntrinsicHeight(child: row);
  }
}

// ---------------------------------------------------------------------------
// _TimelineColumn — circle + optional vertical connector line
// ---------------------------------------------------------------------------

class _TimelineColumn extends StatelessWidget {
  const _TimelineColumn({
    required this.circleSize,
    required this.step,
    required this.showLine,
  });

  final double circleSize;
  final TransactionStepItem step;
  final bool showLine;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: circleSize,
      child: Column(
        children: [
          _buildCircle(),
          if (showLine)
            Expanded(
              child: Center(
                child: Container(width: 1, color: AppColors.accentLight),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildCircle() {
    if (step.state == TransactionStepState.completed) {
      return Container(
        width: circleSize,
        height: circleSize,
        decoration: const BoxDecoration(
          color: AppColors.indigo,
          shape: BoxShape.circle,
        ),
        alignment: Alignment.center,
        child: const Icon(Icons.check_rounded, size: 10, color: Colors.white),
      );
    }
    if (step.state == TransactionStepState.processing) {
      return Container(
        width: circleSize,
        height: circleSize,
        decoration: const BoxDecoration(
          color: AppColors.accentLight,
          shape: BoxShape.circle,
        ),
        alignment: Alignment.center,
        child: const DotSpinner(size: 10, color: AppColors.indigo),
      );
    }
    return Container(
      width: circleSize,
      height: circleSize,
      decoration: const BoxDecoration(
        color: AppColors.accentLight,
        shape: BoxShape.circle,
      ),
      alignment: Alignment.center,
      child: Text(
        '${step.number}',
        style: GoogleFonts.inter(
          fontSize: 8,
          fontWeight: FontWeight.w700,
          height: 10 / 8,
          letterSpacing: 0.06,
          color: AppColors.indigo,
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// _StepContent — title + subtitle/primaryWidget + description
// ---------------------------------------------------------------------------

/// Figma text tokens exposed for step content widgets built externally.
class TransactionStepStyles {
  TransactionStepStyles._();

  /// Step title — Inter SemiBold 15px / lh 20 / -0.23.
  static final TextStyle title = GoogleFonts.inter(
    fontSize: 15,
    fontWeight: FontWeight.w600,
    height: 20 / 15,
    letterSpacing: -0.23,
    color: AppColors.textPrimary,
  );

  /// Step data line — Inter Regular 15px / lh 20 / -0.23.
  static final TextStyle body = GoogleFonts.inter(
    fontSize: 15,
    fontWeight: FontWeight.w400,
    height: 20 / 15,
    letterSpacing: -0.23,
    color: AppColors.textPrimary,
  );

  /// Step description — Inter Regular 10px / lh 13 / 0.06 / gray.
  static final TextStyle description = GoogleFonts.inter(
    fontSize: 10,
    fontWeight: FontWeight.w400,
    height: 13 / 10,
    letterSpacing: 0.06,
    color: AppColors.gray,
  );
}

class _StepContent extends StatelessWidget {
  const _StepContent({required this.step});

  final TransactionStepItem step;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          step.title,
          maxLines: 3,
          overflow: TextOverflow.ellipsis,
          style: TransactionStepStyles.title,
        ),
        if (step.primaryWidget != null && step.primaryWidget is Widget)
          step.primaryWidget as Widget
        else if (step.primaryText != null)
          Text(step.primaryText!, style: TransactionStepStyles.body),
        if (step.secondaryText != null) ...[
          const SizedBox(height: AppSpacing.xs),
          Text(step.secondaryText!, style: TransactionStepStyles.description),
        ],
      ],
    );
  }
}
